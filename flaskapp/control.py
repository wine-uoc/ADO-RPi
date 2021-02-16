"""Database control functions."""
import json
from flask import current_app as app
from flask import render_template
from flask_login import current_user
import requests
import certifi
import urllib3
from config import ConfigFlaskApp

from .models import db, User, NodeConfig, Wifi, Tokens, Calibration_1, Calibration_2, Calibration_1_Temp, Calibration_2_Temp, Requires_Cal_1, Requires_Cal_2
from .utils import create_node_name, delete_entries
import jwt
from time import time

if app.config['HTTPS_ENABLED']:
    host = ConfigFlaskApp.SSL_SERVER_URL
    ssl_flag = ConfigFlaskApp.SSL_CA_LOCATION 
else:
    host = ConfigFlaskApp.SERVER_URL
    ssl_flag = False # may not work if mainflux is HTTPS only 



def delete_tables_entries():
    """Delete entries of each table in db."""
    delete_entries(Wifi.query.all())
    delete_entries(NodeConfig.query.all())
    delete_entries(Tokens.query.all())
    delete_entries(User.query.all())
    delete_entries(Calibration_1.query.all())
    delete_entries(Calibration_2.query.all())
    delete_entries(Calibration_1_Temp.query.all())
    delete_entries(Calibration_2_Temp.query.all())
    delete_entries(Requires_Cal_1.query.all())
    delete_entries(Requires_Cal_2.query.all())
    db.session.commit()


def update_config_values(sensor_idx, value):
    """Replace value of sensor ('sensor_idx+'1) with 'value'"""
    node_config = get_config_obj()
    new_config = node_config.get_values()
    new_config[sensor_idx] = value
    node_config.set_values(new_config)
    db.session.commit()


def update_wifi_data(ssid=None, password=None, activate=None):
    """Set new SSID and password for wifi."""
    wifi = Wifi.query.filter_by(id=current_user.email).first()
    if ssid and password:
        wifi.ssid = ssid
        wifi.set_password(password, hash_it=False)
    if activate == 1:
        wifi.activate()
    elif activate == 0:
        wifi.deactivate()
    db.session.commit()


def update_tokens_values(account_token, thing_id, thing_key, channel_id):
    """Add values to table.'"""
    tokens = get_tokens_obj()
    tokens.account_token = account_token
    tokens.thing_id = thing_id
    tokens.thing_key = thing_key
    tokens.channel_id = channel_id
    db.session.commit()


def get_config_obj():
    """Query to db to get current node config. object."""
    return NodeConfig.query.filter_by(id=current_user.email).first()

def get_user_obj():
    """Query to db to get current node config. object."""
    return User.query.filter_by(id=current_user.email).first()

def get_wifi_obj():
    """Query to db to get current wifi status."""
    return Wifi.query.filter_by(id=current_user.email).first()


def get_tokens_obj():
    """Query to db to get current tokens table obj."""
    return Tokens.query.filter_by(id=current_user.email).first()


def get_node_id():
    """Query to db to get the unique node id."""
    return Tokens.query.filter_by(id=current_user.email).first().node_id

def get_account_token():
    """Query to db to get the unique node id."""
    return Tokens.query.filter_by(id=current_user.email).first().account_token

def get_thing_id():
    """Query to db to get the unique node id."""
    return Tokens.query.filter_by(id=current_user.email).first().thing_id

def get_calib_1_obj():
    """Query to db to get current node config. object."""
    return Calibration_1.query.filter_by(id=current_user.email).first()

def get_calib_2_obj():
    """Query to db to get current node config. object."""
    return Calibration_2.query.filter_by(id=current_user.email).first()

def get_req_calib_1_obj():
    """Query to db to get current node config. object."""
    return Requires_Cal_1.query.filter_by(id=current_user.email).first()

def get_req_calib_2_obj():
    """Query to db to get current node config. object."""
    return Requires_Cal_2.query.filter_by(id=current_user.email).first()

def get_user_org():
    """Query to db to get the user organization name."""
    existing_user = User.query.first()
    if existing_user is None:
        return 0
    else:
        return existing_user.org


def validate_user(email, password):
    """Validate user pass against db and use login to renew user account token which expires every 24h."""
    user = User.query.filter_by(email=email).first()
    if user and user.check_password(password=password, hash_it=app.config['HASH_USER_PASSWORD']):
        print("checking credentials")
        #new implementation of mainflux_provisioning get_accout_token to avoid circular includes 

        urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)
        url = host + '/tokens'
        data = {
            "email": str(email),
            "password": str(password)
        }
        headers = {"Content-Type": 'application/json'}
        try:
            response = requests.post(url, json=data, headers=headers, verify=ssl_flag)
        except requests.exceptions.SSLError as err: 
            print ("SSL certificate error.")
            return None
        try:
            new_account_token = response.json()['token']
        except:
            return None
        print("updating account token to:", new_account_token)
        #renew account token in database
        tokens = Tokens.query.filter_by(id=email).first()
        tokens.account_token = new_account_token
        db.session.commit()
        return user
    else:
        return None

def validate_email(email):
    """Validate user email against db"""
    user = User.query.filter_by(email=email).first()
    if user:
        return user
    else:
        return None

def send_email(user):
    token = str(user.get_reset_token())
    url = host + '/control/resetpassword/sendmail'
    data = {
            "email": str(user.email),
            "token": str(token),
            "name": str(user.name)
    }
    headers = {"Content-Type": 'application/json'}
    try:
        response = requests.post(url, json=data, headers=headers, verify=ssl_flag)
    except requests.exceptions.SSLError as err: 
        print ("SSL certificate error.")
        return None
    except:
        print("Some error occurred when attempting to send reset email")
    try:
        status = response.json()['status']
        return status
    except:
        return None

def get_mainflux_token(user):
    #verified user, encode new token with channel id
    tokens=Tokens.query.filter_by(id=user.email).first()
    channel_id= tokens.channel_id
    identifier= str(channel_id[0:4]) #for mainflux to find the corresponding key faster
    token=jwt.encode({'reset_password': user.email,
                        'exp':    time() + 120}, #2 minutes
                        key=channel_id).decode('utf-8')
    return token, identifier


def sign_up_database(name, email, password, device_name):
    """
    Given user input in sign up form, initializes all tables of the database
    NOTE: WiFi password is currently stored in plain text (needed for Raspbian)

    :param name: user input in sign form
    :param org:
    :param email:
    :param password:
    :param device_name: has to be unique for this mainflux user
    :return: error msg, object of class User if new user else None
    """
    # Check if user does not exists and the node has not been registered yet to another account
    # existing_user = User.query.filter_by(email=email).first()
    org= str(email) #this way organization is unique and user cannot temper it
    existing_user = User.query.first()
    if existing_user is None:
        user = User(name=name, org=org, email=email)    # userdata table
        user.set_password(password, hash_it=app.config['HASH_USER_PASSWORD'])

        node_config = NodeConfig(id=email)              # nodeconfig table associated to email
        node_config.set_values([0] * app.config['MAX_NUM_SENSORS_IN_NODE'])   # All sampling rates to 0 (disabled)

        wifi = Wifi(id=email, ssid='')                  # wifidata table associated to email
        wifi.set_password(password, hash_it=False)      # Store-hashed option off
        wifi.deactivate()  # Use ethernet by default

        tokens = Tokens(id=email, node_id=device_name) #tokens = Tokens(id=email, node_id=create_node_name())   # tokens table associated to email

        calibration1 = Calibration_1(id=email)              # calibration table associated to email
        calibration1.set_values([1] * app.config['MAX_NUM_SENSORS_IN_NODE'])   # All 1-pt calibration values set to 1 (default)
        
        calibration2 = Calibration_2(id=email)              # calibration table associated to email
        calibration2.set_values([1] * app.config['MAX_NUM_SENSORS_IN_NODE'])   # All 2-pt calibration values set to 1 (default)

        calibration1_temp = Calibration_1_Temp(id=email)              # calibration table associated to email
        calibration1_temp.set_values([25] * app.config['MAX_NUM_SENSORS_IN_NODE'])   # All 1-pt calibration values set to 25deg (default)
        
        calibration2_temp = Calibration_2_Temp(id=email)              # calibration table associated to email
        calibration2_temp.set_values([25] * app.config['MAX_NUM_SENSORS_IN_NODE'])   # All 2-pt calibration values set to 25deg (default)
        
        #loads flags from config file
        #flag = 1 for the sensors that require calibration before using
        req_cal_1 = Requires_Cal_1(id=email)              # flag table associated to email
        req_cal_1.set_values(app.config['REQ_CAL_1'])   # All flag values set to 0 (disabled calibration)
        
        req_cal_2 = Requires_Cal_2(id=email)              # flag table associated to email
        req_cal_2.set_values(app.config['REQ_CAL_2'])   # All flag values set to 0 (disabled calibration)
        
        db.session.add(user)                            # Commit changes
        db.session.add(node_config)
        db.session.add(wifi)
        db.session.add(tokens)
        db.session.add(calibration1)
        db.session.add(calibration2)
        db.session.add(calibration1_temp)
        db.session.add(calibration2_temp)
        db.session.add(req_cal_1)
        db.session.add(req_cal_2)
        db.session.commit()
        return False, user, tokens.node_id
    else:
        # already exists an account associated to this node
        if existing_user.email == email:
            # email taken
            error_msg = 'This node is already registered with that email address. Log in to configure it.'
            return error_msg, None, None
        else:
            # node registered to other account
            error_msg = 'This node is linked to: {}! To link it to another account, log in and reset the ' \
                        'node to factory settings.'.format(existing_user.email)
            return error_msg, None, None
