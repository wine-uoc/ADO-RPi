"""
TODO
"""
import json
import os
from json import JSONDecodeError
from rpiapp.logging_filter import logger
import time
from config import ConfigRPI
from rpiapp.arduino_commands import CmdType, SensorType
from rpiapp.db_management import get_table_database, update_req_cal_1_table_database, update_req_cal_2_table_database,\
 update_calibration_1_table_database, update_calibration_2_table_database, update_calibration_1_temp_table_database, update_calibration_2_temp_table_database


logging = logger
temperature = 25 #global var, holds the last known temperature value, for where temp compensation is needed  
isCalibrated = [0,0,0,0,0,0,0,0,0,0] #flag for each sensor
_kvalue = 1

DO_Table = [
    14460, 14220, 13820, 13440, 13090, 12740, 12420, 12110, 11810, 11530,
    11260, 11010, 10770, 10530, 10300, 10080, 9860, 9660, 9460, 9270,
    9080, 8900, 8730, 8570, 8410, 8250, 8110, 7960, 7820, 7690,
    7560, 7430, 7300, 7180, 7070, 6950, 6840, 6730, 6630, 6530, 6410]

def reset_iscalibrated_flags(idx_sensor):
    global isCalibrated
    isCalibrated[idx_sensor] = 0


def valid_data(response, sensorType, parameter1):
    if len(response) > 2:
        #print(response)
        try:
            data = json.loads(response)  # a SenML list
            for item in data:  # normally only one item
                try:
                    if int(item["sensorType"]) == int(sensorType) and int(item["parameter1"]) == int(parameter1):
                        logging.debug('OK')
                        return True
                    else:
                        logging.warning('Received data does not correspond to the last sent command')
                        logging.info("param1: %s", str((item["parameter1"])))
                        logging.info("sensortype: %s ", str(item["sensorType"]))
                except ValueError:
                    # it was a string, not int
                    #logging.debug('parameter is a string')
                    if int(item["sensorType"]) == int(sensorType) and str(item["parameter1"]) == str(parameter1):
                        logging.debug('sensorType and parameter checks')
                        return True
                    else:
                        logging.warning('Received data does not correspond to the last sent command: %s', item)
                except JSONDecodeError as e:
                    logging.warning("Json decode error: %s", str(e))
                except Exception as e:
                    logging.warning("Something else went wrong: %s", str(e))
        except:
            logging.error("loading will block our program")
            #logging.info("*********************** E X I T ********************************************")
            #os._exit(1)
        
    else:
        logging.error('Data length is too small')
        return False



def publish_data(magnitude,response, client, topic, engine):
    global temperature

    data = json.loads(response)  # a SenML list
    for item in data: #normally there is only one item
        #logging.debug("#### publishing ####")
        timestamp = time.time()
        # extract read value and hardware name from arduino answer 
        value = item['pinValue']
        bn = item['bn']
        name = magnitude
        unit = [i for (i, v) in zip(ConfigRPI.SENSOR_UNITS, ConfigRPI.SENSOR_MAGNITUDES) if v == name][0]

        #handle calibration db
        sensor_index = get_sensor_index(name) + 1 #index 1 to 10, to extract from calibration table
        if sensor_index < 10:
            idx_sensor_str = 's0' + str(sensor_index)
        else:
            idx_sensor_str = 's' + str(sensor_index)

        db1_row,_ = get_table_database(engine,"calibration_1")
        db2_row,_ = get_table_database(engine,"calibration_2")

        #constructing the payload for mainflux
        #for some sensors, special payload construction is needed, to use the calibration values
        #********************************************
        if name == "Temperature-S": #update global temp value, take into account the surface temp
            temperature = value
            #logging.debug ("temperature is %s", value)
            print(temperature)
        #********************************************
        if name == "pH":
            neutralVoltage = getattr(db1_row, idx_sensor_str) 
            acidVoltage = getattr(db2_row, idx_sensor_str)
            voltage = value * 3300/1024 #mkr1000  max 3.3V input

            logging.info("neutral, %s", neutralVoltage)
            logging.info("acid, %s", acidVoltage)
            logging.info("current, %s", voltage)  
            try:
                ph =  readPH_library(voltage, temperature, neutralVoltage, acidVoltage)
                value = ph
            except:#division by zero
                logging.error("division by zero") #raw value will be sent
    
        #***********************************************
        elif name == "Turbidity": #current formula can only be used with 5V readings
            try:
                #attention! voltage reading is artificially shifted to 5V from 3.3V
                value = readTurbidity(value) 
            except:
                logging.error("error in turbidity computation")
                
        #************************************************
        elif name == "Conductivity1": #add if calibrated flag
            #print("pinvalue: ", value)
            voltage = value/1024*3300 #max analog input mkr1000
            #print("voltage:", voltage)
            _kvalueLow = getattr(db1_row, idx_sensor_str)
            _kvalueHigh = getattr(db2_row, idx_sensor_str)
            try:
                value = readEC(voltage, temperature, _kvalueLow, _kvalueHigh)
            except:
                logging.error("error in Conductivity1 computation")
                
        #***********************************************
        elif name == "Conductivity2":
            voltage = value/1024*3300 #mkr1000
            _kvalue2 = getattr(db1_row, idx_sensor_str)
            try:
                value = readEC2(voltage, temperature, _kvalue2)
            except:
                logging.error("error in Conductivity2 computation")
                
        #***********************************************
        elif name == "Oxygen":
            voltage = value/1024*3300 #mV
            calib_mode=1
            if calib_mode == 0: #1 point calib, or two point
                
                CAL1_V=getattr(db1_row, idx_sensor_str)
                CAL2_V=0

                db1T_row,_ = get_table_database(engine,"calibration_1_temp")
                CAL1_T=getattr(db1T_row, idx_sensor_str)
                CAL2_T=0
                try:
                    value = readDO(voltage, temperature, calib_mode, CAL1_T, CAL1_V, CAL2_T, CAL2_V)
                except:
                    logging.error("DO math issue")
                   
            elif calib_mode == 1: #2 point calib
                
                CAL1_V=getattr(db1_row, idx_sensor_str)
                CAL2_V=getattr(db2_row, idx_sensor_str)
                db1T_row,_ = get_table_database(engine,"calibration_1_temp")
                db2T_row,_ = get_table_database(engine,"calibration_2_temp")

                CAL1_T=getattr(db1T_row, idx_sensor_str)
                CAL2_T=getattr(db2T_row, idx_sensor_str)
                try:
                    value = readDO(voltage, temperature, calib_mode, CAL1_T, CAL1_V, CAL2_T, CAL2_V)
                except:
                    logging.error(" DO math issue")
                    

        #***********************************************
        elif name == 'AirCO2':
            voltage = value/1024*3300 #mV
            #print("voltage:", voltage)
            try:
                value = readCO2(voltage)
            except:
                logging.error("some CO2 error")
        
        payload = [{"bn": "", "n": name, "u": unit, "v": value, "t": timestamp}]
        #payload = {"bn": "", "n": name, "u": unit, "v": 10, "t": timestamp}
        #print(payload)
        client.publish(topic, json.dumps(payload))




def readPH_library(voltage, temperature, neutralVoltage, acidVoltage):
    slope = (7.0-4.0)/((neutralVoltage-1500.0)/3.0 - (acidVoltage-1500.0)/3.0)  
    #two point: (_neutralVoltage,7.0),(_acidVoltage,4.0)
    intercept =  7.0 - slope*(neutralVoltage-1500.0)/3.0
    phValue = slope*(voltage-1500.0)/3.0+intercept;  
    #y = k*x + b
    return phValue

def readTurbidity(reading):
    #from dfrobot wiki page
    #transform reading 0-1023 to voltage 0-5V
    #reading is 0-3.3V but extrapolate to 5V for using this formula
    voltage = reading * 5/1024 # converts reading to 5V value
    #voltage3.3 = reading * 3.3/1024 #maximum pin input is 3.3V
    #voltage5 = voltage3.3 * 5/3.3
    NTU = -1120.4*(voltage**2) + 5742.3*voltage -4352.9
    return NTU 

def readEC(voltage,temperature, _kvalueLow, _kvalueHigh):
    global _kvalue
    rawEC = 1000*voltage/820.0/200.0
    valueTemp = rawEC * _kvalue
    if(valueTemp > 2.5):
        _kvalue = _kvalueHigh
    elif(valueTemp < 2.0):
        _kvalue = _kvalueLow
    value = rawEC * _kvalue
    value = value / (1.0+0.0185*(temperature-25.0))
    return value

def readEC2(voltage,temperature, _kvalue2):
    RES2 = (7500.0/0.66)
    ECREF = 20.0
    _ecvalueRaw = 1000*voltage/RES2/ECREF*_kvalue2*10.0
    value = _ecvalueRaw / (1.0+0.0185*(temperature-25.0)) #temperature compensation
    return value

def readDO(voltage, temperature_real, calib_mode, CAL1_T, CAL1_V, CAL2_T, CAL2_V):
    global DO_Table

    temperature = int(round(temperature_real)) #to search the DO table
    if calib_mode == 0: #one point
        V_saturation = CAL1_V + 35 * temperature - CAL1_T * 35
        return voltage * DO_Table[temperature] / V_saturation
    else:
        V_saturation = (temperature - CAL2_T) * (CAL1_V - CAL2_V) / (CAL1_T - CAL2_T) + CAL2_V
    return voltage * DO_Table[temperature] / V_saturation

def readCO2(voltage):
    if voltage<400: #preheating
        return 0
    else:
        concentration = (voltage-400)*50/16
        return concentration

def get_sensor_index(name):
    sensor_list = ConfigRPI.SENSOR_MAGNITUDES
    for i in range(len(sensor_list)):
        if sensor_list[i] == name:
            break
    return i

def HandleCalibration(engine, db, value, sensor_index, topic_cal, client):
    global temperature
    flag1 = 0
    flag2 = 0


    name = ConfigRPI.SENSOR_MAGNITUDES[sensor_index-1]
    logging.info("Handling %s sensor calibration", name)
    if sensor_index < 10:
        idx_sensor_str = 's0' + str(sensor_index)
    else:
        idx_sensor_str = 's' + str(sensor_index)
    
    #print ("Last known temperature value: ", temperature)
    #************************************************************************************  
    if name == "pH":
        #todo: somehow store the temperature value too, or fix it for the user
        voltage = value *3300/1024 
        if db == '1': #high temp
            update_req_cal_1_table_database(engine, sensor_index, 0) #cal not needed anymore
            update_calibration_1_table_database(engine, sensor_index, voltage) #1 to 10
            flag1 = 1
        elif db == '2':
            update_req_cal_2_table_database(engine, sensor_index, 0) #cal not needed anymore
            update_calibration_2_table_database(engine, sensor_index, voltage) #1 to 10
            flag2 = 1

    #************************************************************************************  

    elif name == "Conductivity1":
        #read cal db\
        voltage = value*3300/1024
        if db == '1':
            dbname= "calibration_1"
            db_index = 1
        else:
            dbname= "calibration_2"
            db_index = 2

        logging.debug ("db value: %s", voltage)
        rawEC = 1000*voltage/820.0/200.0 
        logging.debug("rawEC: %s", rawEC)
        if (rawEC>0.9 and rawEC<1.9): #original 1.9 Buffer Solution:1.413us/cm
            compECsolution = 1.413*(1.0+0.0185*(temperature-25.0))
            KValueTemp = 820.0*200.0*compECsolution/1000.0/voltage
            round(KValueTemp,2)
            _kvalueLow = KValueTemp 
            logging.debug ("kLOW: %s",_kvalueLow)
            update_req_cal_1_table_database(engine, sensor_index, 0) #cal not needed anymore
            update_calibration_1_table_database(engine, sensor_index, _kvalueLow) #1 to 10
            flag1 = 1
        elif (rawEC>9 and rawEC<16.8): #Buffer Solution:12.88ms/cm
            compECsolution = 12.88*(1.0+0.0185*(temperature-25.0))
            KValueTemp = 820.0*200.0*compECsolution/1000.0/voltage
            _kvalueHigh = KValueTemp
            logging.debug("kHIGH: %s",_kvalueHigh)
            update_req_cal_2_table_database(engine, sensor_index, 0)
            update_calibration_2_table_database(engine, sensor_index, _kvalueHigh) #1 to 10
            flag2 = 1
        else:
            if db_index == 1:
                update_req_cal_1_table_database(engine, sensor_index, 1)
            elif db_index == 2:
                update_req_cal_2_table_database(engine, sensor_index, 1)
            logging.error("error with Conductivity1 calibration values, setting db: %s", db_index ,"flag to retake measurement")
                #to do: flag a database for check_cal fc in flaskapp

        if flag1 == 1 or flag2 == 1: #this function will be called once for a db, and once again for the other
            logging.debug("value is updated")
        else:
            logging.error("_kvalueLow and _kvalueHigh were not updated correctly")
            #here we should set a flag for flaskapp


    #************************************************************************************
    elif name == "Conductivity2":
        RES2 = (7500.0/0.66)
        ECREF = 20.0
        _kvalue2 = 1
        voltage = value *3300/1024
        if db == '1':
            dbname= "calibration_1"
            db_index = 1
            _ecvalueRaw = 1000*voltage/RES2/ECREF*_kvalue2*10.0
            logging.debug ("ecvalueRaw %s",_ecvalueRaw)
            if (_ecvalueRaw>6) and (_ecvalueRaw<18): #original 18
                logging.debug("identified 12.88ms/cm buffer solution")
                rawECsolution = 12.9*(1.0+0.0185*(temperature-25.0))  #temperature compensation
                KValueTemp = RES2*ECREF*rawECsolution/1000.0/voltage/10.0  #calibrate the k value
                if((KValueTemp>0.5) and (KValueTemp<1.5)):
                    logging.debug("successful calibration")
                    _kvalue2 =  KValueTemp
                    update_req_cal_1_table_database(engine, sensor_index, 0) #cal not needed anymore
                    update_calibration_1_table_database(engine, sensor_index, _kvalue2) #1 to 10
                    flag1 = 1
                else:
                    logging.error("Conductivity2 calibration failed")
                    update_req_cal_1_table_database(engine, sensor_index, 1) #cal needed 
            else:
                logging.error("Conductivity2 buffer solution error")
                update_req_cal_1_table_database(engine, sensor_index, 1) #cal needed 
        else:
            logging.error("this DB is not an option for the Conductivity2 sensor")



    #************************************************************************************   
    elif name == "Oxygen":
        voltage = value *3300/1024 #mkr1000
        logging.debug("pin value %s", str(value))
        logging.debug("voltage %s", str(voltage))
        logging.debug("temp %s", str(temperature))
        if db == '1': #high temp
            update_req_cal_1_table_database(engine, sensor_index, 0) #cal not needed anymore
            update_calibration_1_table_database(engine, sensor_index, voltage) #1 to 10
            update_calibration_1_temp_table_database(engine, sensor_index, temperature) #1 to 10
            flag1 = 1

            logging.info("****DB1 DONE****")
        elif db == '2':
            update_req_cal_2_table_database(engine, sensor_index, 0) #cal not needed anymore
            update_calibration_2_table_database(engine, sensor_index, voltage) #1 to 10
            update_calibration_2_temp_table_database(engine, sensor_index, temperature) #1 to 10
            flag2 = 1

            logging.info("****DB2 DONE****")



    #************************************************************************************
    else: #other sensor 
        if db == '1':
            update_calibration_1_table_database(engine, sensor_index, value) #1 to 10
            flag1 = 1
        else:
            update_calibration_2_table_database(engine, sensor_index, value)
            flag2 = 1

    
    name1 = name+"-db1"
    name2 = name+"-db2"
    # Send control message confirming CAL to grafana
    if db == '1': #we were suposed to update db1
        data = [{"bn": "", "n": name1, "u": "", "v": flag1, "t": time.time()}]
        client.publish(topic_cal, json.dumps(data))
    elif db == '2':
        data = [{"bn": "", "n": name2, "u": "", "v": flag2, "t": time.time()}]
        client.publish(topic_cal, json.dumps(data))
