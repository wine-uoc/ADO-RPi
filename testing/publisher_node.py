import json
import paho.mqtt.client as mqttClient
import time
import random as r

#dictionary = eval(open("tokens.txt").read())
#print(dictionary)


class Fake_node():
    def __init__(self,  name, mqtt_id, mqtt_key, channel_id, client):
        self.name = name
        self.mqtt_id = mqtt_id
        self.mqtt_key = mqtt_key
        print(self.name)
        print(self.mqtt_id)
        print(self.mqtt_key)
        self.client = client
        #mqttClient.Client._call_socket_register_write = lambda _self: None
        #mqttClient.Client._call_socket_unregister_write = lambda _self, _sock=None: None
        #self.client = mqttClient.Client(self.name)               #create new instance
        #self.client.username_pw_set(str(self.mqtt_id), str(self.mqtt_key))    #set username and password
        self.mqtt_topic = "channels/" + str(channel_id) + "/messages" 
        #self.conn_flag = False


    def node_connect(self):
            # avoid deadlock by nop-ing socket control callback stubs
 
        self.client.on_connect = self.on_connect
        self.client.connect_async(host='localhost', port=1883, keepalive=60)
        self.client.loop_start()
        self.client.reconnect_delay_set(min_delay=1, max_delay=10)
                    

    def on_connect(self, client, userdata, flags, rc):
        if rc == 0:
            print("Connected to broker")
            self.conn_flag = True 
        else:
            print("Connection failed")

    def disconnect(self):
        print("disconnecting: ", self.name)
        self.client.disconnect()

    def send_data(self, min, max):
 
        #try:
        #while 1:
        print("Sending...:", self.name)
        temperature = r.uniform(min, max)
        ph = r.uniform(1, 14)
        do = r.uniform(100, 200)
        conductivity = r.uniform(10, 20)
        lux = r.uniform(100, 400)
        flow = r.uniform(1, 40)
        timestamp = time.time()
        payload1 = [{"bn":"","n":"pH", "u":"","v":ph, "t":timestamp}]
        payload2 = [{"bn":"","n":"Oxygen", "u":"mg/L","v":do, "t":timestamp}]
        payload3 = [{"bn":"","n":"Temperature-S", "u":"Cel","v":temperature, "t":timestamp}]
        self.client.publish(self.mqtt_topic,json.dumps(payload1)) 
        self.client.publish(self.mqtt_topic,json.dumps(payload2)) 
        self.client.publish(self.mqtt_topic,json.dumps(payload3)) 
        time.sleep(5)
 
        #except KeyboardInterrupt:
         #   print("bye bye")
          #  self.client.disconnect()
           # self.client.loop_stop()
