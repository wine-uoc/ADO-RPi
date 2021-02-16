import json
import certifi
import urllib3
import requests
import paho.mqtt.client as mqtt
import time
import random as r
import copy
#import grafana_users as grafana
from publisher_node import Fake_node


host='http://localhost'
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

#create user account
def create_account(email, password):
	url=host+'/users'
	data={
		"email":str(email),
		"password": str(password)
	}
	headers={"Content-Type": 'application/json'}
	return requests.post(url, json=data,headers=headers, verify=False)

def get_account_token(email, password):
	url=host+'/tokens'
	data={
		"email":str(email),
		"password": str(password)
	}
	headers={"Content-Type": 'application/json'}
	return requests.post(url, json=data,headers=headers, verify=False)

def create_thing(account_token, thing_name, thing_type):
	url=host+'/things'
	data={
		"name":str(thing_name),
		"type": str(thing_type)
	}
	headers={"Content-Type": 'application/json', "Authorization": str(account_token)}
	return requests.post(url, json=data,headers=headers, verify=False)

def return_thing_id(account_token, thing_name):
	url=host+'/things?offset=0&limit=100' #default things limit is 10
	headers={"Authorization": str(account_token)}
	response = requests.get(url,headers=headers, verify=False)
	#print (response.text)
	response= response.json()
	things_list = response["things"]
	#print(things_list)
	for i in range(len(things_list)):
		if things_list[i]['name'] == str(thing_name):
			#print("found it")
			thing_id = things_list[i]['id']
			return thing_id
	
	print('thing not here')
	return 0

def delete_thing(account_token, thing_id):
	url=host+'/things/'+ str(thing_id)
	headers={"Authorization": str(account_token)}
	return requests.delete(url,headers=headers, verify=False)

def return_things_list(account_token):
	url=host+'/things?offset=0&limit=100' #default things limit is 10
	headers={"Authorization": str(account_token)}
	response = requests.get(url,headers=headers, verify=False)
	#print (response.text)
	response= response.json()
	things_list = response["things"]
	print (things_list)
	return things_list


def delete_things_list(account_token):
	url=host+'/things?offset=0&limit=100' #default things limit is 10
	headers={"Authorization": str(account_token)}
	response = requests.get(url,headers=headers, verify=False)
	#print (response.text)
	response= response.json()
	things_list = response["things"]
	print(things_list)
	for i in range(len(things_list)):
		if things_list[i]['name']!= 'piscina4': #real thing
			delete_thing(account_token, things_list[i]['id'])
			time.sleep(0.1)
	


def return_thing_key(account_token, thing_name):
	url=host+'/things?offset=0&limit=100' #default things limit is 10
	headers={"Authorization": str(account_token)}
	response = requests.get(url,headers=headers, verify=False)
	#print (response.text)
	response= response.json()
	things_list = response["things"]
	for i in range(len(things_list)):
		if things_list[i]['name'] == str(thing_name):
			#print("found it")
			thing_key = things_list[i]['key']
			return thing_key
		
	print('thing not here')
	return 0

def create_channel(account_token, channel_name):
	url=host+'/channels'
	data={
		"name":str(channel_name)
	}
	headers={"Content-Type": 'application/json', "Authorization": str(account_token)}
	return requests.post(url, json=data,headers=headers, verify=False)

def return_channel_id(account_token, channel_name):
	url=host+'/channels'
	headers={"Authorization": str(account_token)}
	response = requests.get(url,headers=headers, verify=False)
	#print (response.text)
	response= response.json()
	channels_list = response["channels"]
	for i in range(len(channels_list)):
		if channels_list[i]['name'] == str(channel_name):
			#print("found it")
			channel_id = channels_list[i]['id']
			return channel_id
		
	print('channel not here')
	return 0


def connect_to_channel(account_token, channel_id, thing_id):
	url=host+'/channels/'+ str(channel_id)+ '/things/'+ str(thing_id)
	headers={"Authorization": str(account_token)}
	return requests.put(url,headers=headers, verify=False)

def attempt_sending_message(channel_id, thing_key):
	url=host+'/http/channels/'+ str(channel_id) + '/messages'
	headers={"Content-Type": 'application/senml+json', "Authorization": str(thing_key)}
	data = [
			{
				"bn":"some-base-name:",
				"bt":1.276020076001e+09,
				"bu":"A",
				"bver":5,
				"n":"voltage",
				"u":"V",
				"v":120.1
			}, 
			{
				"n":"current",
				"t":-5,
				"v":1.2
			},
			{
				"n":"current",
				"t":-4,
				"v":1.3
			}
			]
	response = requests.post(url, json = data,headers=headers, verify=False)
	print (response.text)

def get_messages_on_channel(channel_id, thing_key):
	url=host+':8905/channels/'+ str(channel_id) + '/messages'
	headers={"Authorization": str(thing_key)}
	response = requests.get(url, headers=headers, verify=False)
	print (response.text)

def on_connect(client, userdata, flags, rc):
    global subtopic_sr, subtopic_cal
    """The callback for when the client receives a CONNACK response from the server."""
    # The value of rc indicates success or not:
    # 0: Connection successful 1: Connection refused - incorrect protocol version 2: Connection refused - invalid
    # client identifier 3: Connection refused - server unavailable 4: Connection refused - bad username or password
    # 5: Connection refused - not authorised 6-255: Currently unused.
    print("Trying to connect to broker. Result code: %s" , str(rc))
    if rc == 0:
        print("Connected.")
    else:
    	print("This node couldn't connect")

def main():
	name = "christmas"
	organization = "tree"
	email="christmas@tree.com"
	password="password"
	response_c1 = create_account(email, password)
	response_c2 = get_account_token(email, password)
	channel_name = "comm_channel"
	
	if not response_c1.ok and response_c2.ok:
		print('Backend account exists, registering node.')
	elif response_c1.ok and response_c2.ok:
		print ('Backend account DOES NOT exist, creating account, channel, registering node.')
		_ = create_account(email, password)
		token = get_account_token(email, password).json()['token']
		_ = create_channel(token, channel_name)
	elif not response_c1.ok and not response_c2.ok:
		print('Incorrect password for that account. Try again.')

	token = get_account_token(email, password).json()['token']
	channel_id = return_channel_id(token, channel_name)
	dictionary = {}
	dictionary['account_token'] = token
	dictionary['channel_id'] = channel_id

	###delete user things (e.g when too many junk things were created)
	#print("*************************** listing things")
	#return_things_list(token)
	#print("*************************** removing things")
	#delete_things_list(token)
	#print("*************************** listing things after delete")
	#return_things_list(token)
	#print("*************************** done")

	nb_nodes = 9#99 #i have already manually created other things for this user
	fake_node_list=[]
	clients = [] #holds the mqtt connections

	for count in range(nb_nodes):
		node_name = "test_" + str(count)
		name_id = node_name + "_id"
		name_key = node_name + "_key"
		# register node to account (create thing), if node name is unique
		if (return_thing_id(token, node_name)==0):
			_ = create_thing(token, node_name, "device")
			thing_id = return_thing_id(token, node_name)
			thing_key = return_thing_key(token, node_name)
			# connect to the existing channel
			_ = connect_to_channel(token, channel_id, thing_id)
				# store credentials
			dictionary[name_id] = thing_id
			dictionary[name_key] = thing_key

			client = mqtt.Client(node_name)
			client.username_pw_set(str(thing_id), str(thing_key))
			client.on_connect = on_connect
			clients.append(client) 
			fake_node_list.append(Fake_node(node_name, thing_id, thing_key, channel_id, client))
		else:
			print('Device name already exists for this account.')
			thing_id = return_thing_id(token, node_name)
			thing_key = return_thing_key(token, node_name)
			_ = connect_to_channel(token, channel_id, thing_id)
			dictionary[name_id] = thing_id
			dictionary[name_key] = thing_key
			client = mqtt.Client(node_name)
			client.username_pw_set(str(thing_id), str(thing_key))
			client.on_connect = on_connect
			clients.append(client) 
			fake_node_list.append(Fake_node(node_name, thing_id, thing_key, channel_id, client))

	
	f = open('tokens.txt', 'w' )
	f.write(json.dumps(dictionary))
	f.close()

	for client in clients:
		client.connect_async(host='localhost', port=1883, keepalive=60)
		client.loop_start()
		time.sleep(0.5)
	while 1:
		for obj in fake_node_list:
			obj.send_data(0,9)


if __name__ == '__main__':
    print('Trying to create user account')
    main()
