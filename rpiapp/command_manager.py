# this is sending data over ubuntu serial to arduino main serial (not gpio to gpio)
import sys
import os
import threading
import time
import json
import paho.mqtt.client as mqtt
import serial
from rpiapp import arduino_publish_data, arduino_commands, ini_client
from rpiapp.db_management import check_table_database, get_table_database, update_calibration_1_table_database, update_calibration_2_table_database
from rpiapp.periodic_control_sensors import set_sr
from rpiapp.logging_filter import logger
from config import ConfigRPI, ConfigFlaskApp

logging = logger
CmdType = arduino_commands.CmdType
SensorType = arduino_commands.SensorType


MQTT_CONNECTED = False  # global variable for the state
MQTT_SUBSCRIBED = False
latest_thread = ['1','2','3','4', '5', '6', '7', '8', '9', '10', '11'] #the name of the latest created thread. position corresponds to sensor index
old_name_available=[1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1]
READ_timeout = 15
WRITE_timeout = 10 #non blocking mode

ssl_CA= ConfigRPI.SSL_CA_LOCATION
def create_threads(ser):
    global latest_thread, client, subtopic_sr
    serialcmd, periodicity, magnitudes = arduino_commands.get_config()
    size = len(serialcmd)  # number of configs we have

    logging.info('The set of commands is %s', serialcmd)
    logging.info('NB of threads is %s', str(size))
    logging.info('periodicity of each thread is %s', periodicity)
    logging.info('name of each sensor is %s', magnitudes)
    for i in range(1, size + 1):
        #send control message with SR at startup
        data = [{"bn": "", "n": magnitudes[i], "u": "s", "v": int(periodicity[i]), "t": time.time()}]
        client.publish(subtopic_sr, json.dumps(data))

    for i in range(1, size + 1):
        # timer is given by expressing a delay
        t = threading.Timer(1, TransmitThread, (ser, serialcmd[i], periodicity[i], magnitudes[i]))  # all sensors send data at startup
        position = arduino_publish_data.get_sensor_index(magnitudes[i])
        name = str(position+1)
        latest_thread[position]=name
        old_name_available[position] = 0 #block this name
        t.setName(name)
        t.start()
        t.join()



def TransmitThread(ser, serialcmd, periodicity, magnitude):
    global no_answer_pending
    global tx_lock
    global old_name_available

    # debug messages; get thread name and get the lock
    #print("TX trying to acquire lock")
    tx_lock.acquire()

    logging.info('executing thread %s', threading.currentThread().getName())
    # expect an answer from A0 after sending the serial message
    no_answer_pending = False

    # schedule this thread corresponding to its periodicity, with the same name it has now
    now = time.time()
    threadname = threading.currentThread().getName()
    index = arduino_publish_data.get_sensor_index(magnitude)


    if keepalive_thread(magnitude, threadname, periodicity):
        try:
            logging.debug("attempting to write")
            logging.debug(serialcmd)
            ser.write(serialcmd.encode('utf-8'))
            ser.flush() 
            logging.debug("rescheduling thread")
            tx = threading.Timer(periodicity, TransmitThread, (ser, serialcmd, periodicity, magnitude))
            threadname =reset_thread_name(threadname, index)
            tx.setName(threadname)
            tx.start()
            logging.debug("creating rx thread")
            # create the RX thread; use join() to start right now
            r = threading.Timer(1, ReceiveThread, (ser, serialcmd, magnitude))
            r.setName('RX Thread')
            r.start()
            r.join()
    
        except OSError as e:
            logging.warning("error: %s", str(e))
            #logging.info("*********************** E X I T ********************************************")
            #ser.reset_output_buffer()
            #ser.close()
            #os._exit(1)
            #we should reset A0 here

            try:
                new_ser = reestablish_serial(ser)
                #attempt writing again
                logging.debug(" except attempting to write")
                new_ser.write(serialcmd.encode('utf-8'))
                new_ser.flush()
                logging.debug("rescheduling thread")
                tx = threading.Timer(periodicity, TransmitThread, (new_ser, serialcmd, periodicity, magnitude))
                threadname =reset_thread_name(threadname, index)
                tx.setName(threadname)
                tx.start()

                # create the RX thread; use join() to start right now
                logging.debug("creating rx thread")
                r = threading.Timer(1, ReceiveThread, (new_ser, serialcmd, magnitude))
                r.setName('RX Thread')
                r.start()
                r.join()

            except Exception as e: #or should we just restart instead of reestablishing serial?
                logging.error("exception after trying to reestablish_serial: %s", str(e))
                logging.debug("rescheduling thread")
                tx = threading.Timer(periodicity, TransmitThread, (ser, serialcmd, periodicity, magnitude))
                threadname =reset_thread_name(threadname, index)
                tx.setName(threadname)
                tx.start()
                tx_lock.release()
        except Exception as e:
            logging.error ("Something else went wrong %s", str(e))
            logging.info("*********************** E X I T ********************************************")
            ser.reset_output_buffer()
            ser.close()
            os._exit(1)
    else:
        logging.info("++++ killing thread: %s", threadname) #kill thread and release lock
        if threadname == str(index+1): #first name will be available again
            old_name_available[index] = 1   
        tx_lock.release()


def ReceiveThread(ser, serialcmd, magnitude):
    global no_answer_pending, client, topic, engine

    try:
        logging.info('executing thread %s', threading.currentThread().getName())
        cmdtype, sensorType, parameter1 = arduino_commands.parse_cmd(serialcmd)
        #logging.info("param1: %s", str(parameter1))
        #logging.info("sensorType: %s", str(sensorType))

        # set a timeout for waiting for serial
        # wait until receiving valid answer
        timeout = time.time() + 15#15
        while no_answer_pending == False and time.time() < timeout:
            if ser.inWaiting() > 0:
                response = ser.readline()
                try:
                    response = response.decode('utf-8')
                    logging.debug("%s", str(response))
                except:
                    logging.error("cannot decode message")
                #logging.debug("%s", response)
                if arduino_publish_data.valid_data(response, sensorType, parameter1):
                    no_answer_pending = True
                    arduino_publish_data.publish_data(magnitude,response, client, topic, engine)
                else:
                    logging.debug("RX data does not correspond to the last command sent")#, lost sync, exit")
                    os._exit(1) #tbd: restart arduino too (soft/hard)

        logging.info("End RX processing %s", time.time())
        tx_lock.release()
    except serial.SerialTimeoutException as e:
        logging.error("serial timeout: %s", str(e))
        ser.close()
        os._exit(1)
    except Exception as e:
        logging.error("##### BAD PROCESSING in ReceiveThread: %s", str(e))
        tx_lock.release()


def CalibrationThread(ser, serialcmd, index, engine, db): #not periodic, index 0 to 9
    global no_answer_pending
    global tx_lock
    if db =='1':
        arduino_publish_data.update_req_cal_1_table_database(engine, index+1, 1) #reset to requires cal
    else:
        arduino_publish_data.update_req_cal_2_table_database(engine, index+1, 1) #reset to requires cal

    logging.info("CAL trying to acquire lock")
    tx_lock.acquire()

    threadname = threading.currentThread().getName()
    logging.info('executing thread %s', threadname)

    # expect an answer from A0 after sending the serial message
    no_answer_pending = False
    try:
        ser.write(serialcmd.encode('utf-8'))
        ser.flush()
        # create the RX thread; use join() to start right now
        r = threading.Timer(1, SetCalibrationDBThread, (ser, serialcmd, index, engine, db))
        r.setName('RX CAL Thread')
        r.start()
        r.join()
    except OSError as e: 
        try:
            ser = reestablish_serial(ser)
            #attempt writing again
            ser.write(serialcmd.encode('utf-8'))
            ser.flush()

            r = threading.Timer(1, SetCalibrationDBThread, (ser, serialcmd, index, engine, db))
            r.setName('RX CAL Thread')
            r.start()
            r.join()
        except:
            tx_lock.release() #in case serial fails
     


def SetCalibrationDBThread(ser, serialcmd, index, engine, db):
    global no_answer_pending, client, subtopic_cal

    try:
        logging.info('executing thread %s', threading.currentThread().getName())
        cmdtype, sensorType, parameter1 = arduino_commands.parse_cmd(serialcmd)
        logging.info('SENT CMD %s', serialcmd)
        # set a timeout for waiting for serial
        # wait until receiving valid answer
        timeout = time.time() + 15
        while no_answer_pending == False and time.time() < timeout:
            if ser.inWaiting() > 0:
                response = ser.readline()
                response = response.decode('utf-8')
                logging.info("%s", str(response))
                if arduino_publish_data.valid_data(response, sensorType, parameter1):
                    no_answer_pending = True
                    idx_sensor = index + 1
                    data = json.loads(response)
                    value = data[0]['pinValue'] #there should be only one item in data

                    arduino_publish_data.HandleCalibration(engine, db, value, idx_sensor, subtopic_cal, client)
                else:
                    logging.debug("RX data does not correspond to the last command sent, checking again the serial")

        logging.info("End CAL RX processing %s", time.time())
        tx_lock.release()        

    except:
        logging.warning("##### BAD PROCESSING in SetCalibrationDBThread")
        tx_lock.release()        


def reestablish_serial(serial_port):
    global READ_timeout, WRITE_timeout
    logging.debug("new serial")
    flag = 0
    #try: 
     #   if serial_port.isOpen():
      #      serial_port.flush()
       #     serial_port.close()
    #except Exception as e:
     #   logging.error("cannot close port: %s", str(e))

    try:    
        ser = serial.Serial(port='/dev/ttyACM0', baudrate=9600, timeout = READ_timeout, write_timeout = WRITE_timeout, rtscts =False, dsrdtr= False)
        flag = 1
        logging.warning("connected to ACM0")
    except:
        try:
            ser = serial.Serial(port='/dev/ttyACM1', baudrate=9600, timeout = READ_timeout, write_timeout = WRITE_timeout, rtscts =False, dsrdtr= False)
            flag = 1
            logging.warning("connected to ACM1")
        except:
            ser = None
            logging.warning("connected to nothing")
    return ser

def keepalive_thread(magnitude, threadname, periodicity):
    global latest_thread
    
    index = arduino_publish_data.get_sensor_index(magnitude)
    if threadname == latest_thread[index] and periodicity != 0: #this is the latest created thread for this sensor and SR!=0
        return True
    else:
        return False #this is an old thread for this sensor

def reset_thread_name(threadname, index):
    global old_name_available, latest_thread
    
    if old_name_available[index] == 1: 
        threadname = str(index+1)
        latest_thread[index] = threadname
        old_name_available[index] = 0
    return threadname

############################# MQTT FUNCTIONS ##################################################
def mqtt_connection_0(tokens, engine, serial):
    global subtopic_sr, subtopic_cal
    """Connect to broker and subscribe to topic."""
    mqtt_topic = 'channels/' + str(tokens.channel_id)
    client_userdata = {'topic': mqtt_topic + '/control',
                       'engine': engine, 'serial':serial}

    # avoid deadlock by nop-ing socket control callback stubs
    mqtt.Client._call_socket_register_write = lambda _self: None
    mqtt.Client._call_socket_unregister_write = lambda _self, _sock=None: None
   
    client = mqtt.Client(client_id=tokens.node_id, userdata=client_userdata) #here we may put device name

    client.username_pw_set(tokens.thing_id, tokens.thing_key)
    client.on_connect = on_connect
    client.on_message = on_message_0
    client.on_subscribe = on_subscribe
    client.on_diconnect = on_disconnect
    client.on_log = on_log
    subtopic_cal = mqtt_topic + '/control/CAL/' + str(tokens.thing_id) #cal is specific for this node
    subtopic_sr = mqtt_topic + '/control/SR/' + str(tokens.thing_id) #SR command is now specific to this device
    if ConfigRPI.HTTPS_ENABLED:
        print ("Connecting via TLS")
        client.tls_set(ssl_CA)
        client.connect_async(host=ConfigRPI.SHORT_SERVER_URL, port=ConfigRPI.SSL_SERVER_PORT_MQTT, keepalive=60)
    else:
        print ("unencrypted connection")
        client.connect_async(host=ConfigRPI.SHORT_SERVER_URL, port=ConfigRPI.SERVER_PORT_MQTT, keepalive=60)
    client.loop_start()
    client.reconnect_delay_set(min_delay=1, max_delay=10)

    # Wait for connection
    global MQTT_CONNECTED
    while not MQTT_CONNECTED:
        time.sleep(1)

    return MQTT_CONNECTED, client, mqtt_topic


def on_connect(client, userdata, flags, rc):
    global subtopic_sr, subtopic_cal
    """The callback for when the client receives a CONNACK response from the server."""
    # The value of rc indicates success or not:
    # 0: Connection successful 1: Connection refused - incorrect protocol version 2: Connection refused - invalid
    # client identifier 3: Connection refused - server unavailable 4: Connection refused - bad username or password
    # 5: Connection refused - not authorised 6-255: Currently unused.
    logging.info("Trying to connect to broker. Result code: %s" , str(rc))
    if rc == 0:
        logging.info("Connected.")
        global MQTT_CONNECTED
        MQTT_CONNECTED = True
        # Subscribing in on_connect() means that if we lose the connection and
        # reconnect then subscriptions will be renewed.
        #client.subscribe(userdata['topic']) #this is the control topic, arriving SR commands valid for all nodes
        logging.info(subtopic_cal)
        logging.info(subtopic_sr)
        client.subscribe(subtopic_sr)
        client.subscribe(subtopic_cal)


def on_disconnect(client, userdata, rc):
    if rc != 0:
        logging.warning("Unexpected disconnection.")

def on_log(client, userdata, level, buf):
    if level == MQTT_LOG_WARNING or level == MQTT_LOG_ERR:
        logging.warning(buf)


def on_subscribe(client, userdata, mid, granted_qos):
    """Callback for subscribed message."""
    #print('Subscribed to %s.' % userdata['topic'])
    global MQTT_SUBSCRIBED
    MQTT_SUBSCRIBED = True


def on_message_0(client, userdata, msg):
    global latest_thread, subtopic_cal, subtopic_sr
    """Callback for received message."""
    #print(msg.topic)
    # print("RX1")
    logging.info(msg.topic + " " + str(msg.qos) +" " + str(msg.payload))
    rx_data = str(msg.payload.decode('UTF-8'))  # message is string now, not json
    message = json.loads(rx_data) #message to json
    logging.info ("***************************************")
    logging.info ("******** %s", str(message['type']))
    if str(message['type']) == 'SET_SR':
        logging.info("Set Sr message")
        # message = eval(message)  # transform to dictionary
        magnitude = message['sensor']
        SR = int(message['v'])
        new_thread_needed, index = set_sr(client, userdata['engine'], subtopic_sr, magnitude, SR, message['u'])
        if new_thread_needed == 1:
            logging.info("creating new thread")
            
            #create read command
            cmd_type = 'read'  
            sensor_type = ConfigRPI.SENSOR_TYPES[index]
            sensor_params = ConfigRPI.SENSOR_PARAMS[index]
            serialcmd = arduino_commands.create_cmd(cmd_type, sensor_type, sensor_params)
            logging.info(serialcmd)
            logging.info(SR)
            logging.info(magnitude)

            #create thread
            t = threading.Timer(1, TransmitThread, (userdata['serial'], serialcmd, SR, magnitude))
            old_thread = int(latest_thread[index]) #catch the latest thread name for this sensor
            if old_name_available[index] == 1: #this thread was not created at startup in flaskapp config page
                new_thread = str(old_thread)
            else:
                new_thread = str(old_thread+ConfigFlaskApp.MAX_NUM_SENSORS_IN_NODE) #linear translation to make sure we don't duplicate names
            logging.info("****** new thread name: %s", new_thread)
            #update latest threadname for this sensor    
            latest_thread[index] = new_thread
            t.setName(new_thread)
            t.start()
            t.join()
        else:
            logging.warning("threads stay the same")

    elif str(message['type']) == 'CAL':
        logging.info("**** CAL the %s sensor", str(message['sensor']))
        sensor = str(message['sensor'])
        db_to_use = str(message['v']) #indicates in which calibration db to save the data
        magnitudes = ConfigRPI.SENSOR_MAGNITUDES
        for i in range(len(magnitudes)):
            if magnitudes[i] == sensor:
                break
        # Create command for A0
        cmd_type = 'calibrate'#'read'  
        sensor_type = ConfigRPI.SENSOR_TYPES[i]
        sensor_params = ConfigRPI.SENSOR_PARAMS[i]
        serialcmd = arduino_commands.create_cmd(cmd_type, sensor_type, sensor_params)

        #create calibration thread; use join() to wait for this thread to finish
        r = threading.Timer(1, CalibrationThread, (userdata['serial'], serialcmd, i, userdata['engine'], db_to_use))
        r.setName('CAL Thread')
        r.start()
        r.join()
            
    else:
        logging.warning("Received message is not of known type  ")

def main():
    global tx_lock, client, topic, engine, READ_timeout, WRITE_timeout

    #demonstrate the logging levels
    logging.debug('DEBUG')
    logging.info('INFO')
    logging.warning('WARNING')
    logging.error('ERROR')
    logging.critical('CRITICAL')
    
    # Check for a db
    engine, exists = None, False
    while not exists:
        logging.info('Waiting for a database.')
        engine, exists = check_table_database(engine)
        time.sleep(2)

    # Get backend credentials
    tokens_key = None
    while tokens_key is None:
        tokens, _ = get_table_database(engine, 'tokens')
        if tokens:
            tokens_key = tokens.thing_key
            logging.info('Waiting for MQTT credentials.')
        else:
            logging.info('Waiting for node signup.')
        time.sleep(2)

    #initialize serial
    ser = serial.Serial(port='/dev/ttyACM0', baudrate=9600, timeout =READ_timeout, write_timeout = WRITE_timeout, rtscts =False, dsrdtr= False)

    # Connect to backend and subscribe to rx control topic
    global MQTT_CONNECTED 
    MQTT_CONNECTED= False
    while not MQTT_CONNECTED:
        MQTT_CONNECTED, client, mqtt_topic = mqtt_connection_0(tokens, engine, ser)
    
    # save the messages topic too
    topic = mqtt_topic + "/messages" 

    #logging.debug("####################### Initializing mqtt broker for client #######################")
    #client, topic = ini_client.initialize_client()

    logging.info("####################### Creating TX_lock #######################")
    tx_lock = threading.Lock()

    # Wait until table exists in db
    # ASSUMPTION: the script can be called before user registers in flaskapp
    # engine, exists = None, False
    # while not exists:
    #     engine, exists = check_table_database(engine)
    #    time.sleep(1)  # seconds

    logging.info('####################### Creating Command Threads #######################')
    create_threads(ser)

    logging.info("####################### Running periodic threads #######################")

    # TODO:
    #  	que pasa si el usuario anade otro sensor mas adelante, se cancelan todos los threads (this)
    #   que pasa si usuario modifica config en grafana
    #   check db periodically (now is checked only when thread happens)
    #   error handling to grafana reading error if x3 reset or error message
    #   reset A0 from rpi
    #   firm udpdate rpi and A0
    #   status message to grafana (https://grafana.com/grafana/plugins/flant-statusmap-panel, auto install in docker
    #   handle rpi reboot

    # print('Press Ctrl+{0} to exit'.format('Break' if os.name == 'nt' else 'C'))

    try:  # This is here to simulate application activity (which keeps the main thread alive).
        while True:
            time.sleep(2)
            logging.info('loop')
    except (KeyboardInterrupt, SystemExit):
        # Not strictly necessary if daemonic mode is enabled but should be done if possible
        # scheduler.shutdown()
        os.exit()
