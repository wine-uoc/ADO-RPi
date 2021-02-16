#not used by rpi_A0.py, only bu rpi.py
import time
from rpiapp.logging_filter import logger
import paho.mqtt.client as mqttClient

from config import ConfigRPI
from rpiapp.db_management import get_table_database

logging = logger

def initialize_client():
    global Connected
    global topic
    global client

    tokens, _ = get_table_database(None, 'tokens')
    thing_id = tokens.thing_id
    thing_key = tokens.thing_key
    channel_id = tokens.channel_id
    node_id = tokens.node_id

    broker_address = ConfigRPI.SHORT_SERVER_URL
    port = ConfigRPI.SERVER_PORT_MQTT
    clientID = 'thing' + str(node_id) + ': data publisher'

    client = mqttClient.Client(clientID)            # create new instance
    client.username_pw_set(thing_id, thing_key)     # set username and password

    Connected = False  # global variable for the state of the connection
    client.on_connect = on_connect  # attach function to callback
    client.connect(broker_address, port=port)       # connect to broker

    topic = "channels/" + str(channel_id) + "/messages"
    data = {}  # json dictionary

    client.loop_start()  # start the loop
    while not Connected:  # Wait for connection
        time.sleep(0.1)
    return client, topic


def on_connect(client, userdata, flags, rc):
    if rc == 0:
        logging.info("Connected to broker")
        global Connected  # Use global variable
        Connected = True  # Signal connection
    else:
        logging.warning("Connection failed")
