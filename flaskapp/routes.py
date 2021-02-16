"""Logged-in page routes."""
from flask import Blueprint, render_template, redirect, url_for, request, flash
from flask import current_app as app
from flask_login import login_required, logout_user

from .assets import compile_main_assets
from .control import get_node_id, get_thing_id, get_account_token, get_config_obj, delete_tables_entries, update_config_values, get_wifi_obj, \
    update_wifi_data, get_user_org, get_tokens_obj, get_calib_1_obj, get_calib_2_obj, get_req_calib_1_obj, get_req_calib_2_obj
from .forms import WifiForm
from flaskapp.backend.grafana_bootstrap import load_json
from flaskapp.backend.mainflux_provisioning import delete_thing
from config import ConfigFlaskApp
import requests
if app.config['HTTPS_ENABLED']:
    host = ConfigFlaskApp.SSL_SERVER_URL
    ssl_flag = ConfigFlaskApp.SSL_CA_LOCATION 
else:
    host = ConfigFlaskApp.SERVER_URL
    ssl_flag = False


# Blueprint Configuration
main_bp = Blueprint('main_bp', __name__,
                    template_folder='templates',
                    static_folder='static')
compile_main_assets(app)

@main_bp.route('/', methods=['GET', 'POST'])
@login_required
def dashboard():
    """
    Node configuration page.
    GET:
    Show active sensors from database, allow enable/disable sensors, show menu options.
    """
    global tokens, client, mqtt_topic, MQTT_CONNECTED, MQTT_SUBSCRIBED

    str_current_config = ['checked' if sensor_sr != 0 else '' for sensor_sr in get_config_obj().get_values()]
    # str list of 'checked' if sensor sampling rate is not 0 else '' (checked is passed to html checkbox)

    return render_template('dashboard.jinja2',
                           title='Configuration - ADO',
                           template='dashboard-template',
                           node_id=get_node_id(),
                           s01_state=str_current_config[0],
                           s02_state=str_current_config[1],
                           s03_state=str_current_config[2],
                           s04_state=str_current_config[3],
                           s05_state=str_current_config[4],
                           s06_state=str_current_config[5],
                           s07_state=str_current_config[6],
                           s08_state=str_current_config[7],
                           s09_state=str_current_config[8],
                           s10_state=str_current_config[9],
                           s11_state=str_current_config[10])


@main_bp.route('/wifi', methods=['GET', 'POST'])
@login_required
def set_wifi():
    """
    Wifi configuration page.

    GET: Serve Set-wifi page and show current SSID stored.
    POST: If form is valid, add new wifi data (delete previous), show success message.
    """
    wifi_form = WifiForm()

    if get_wifi_obj().active:
        current_wifi_state = 'checked'  # Get current wifi status to be displayed in page
    else:
        current_wifi_state = ''

    if request.method == 'POST' and wifi_form.validate_on_submit():
        # Store Wifi details
        update_wifi_data(wifi_form.ssid.data,
                         wifi_form.password.data)
        flash('New SSID and password stored.')
        return redirect(url_for('main_bp.set_wifi'))

    return render_template('wifi.jinja2',
                           form=wifi_form,
                           title='Configure WiFi - ADO',
                           template='wifi-page',
                           current_ssid=get_wifi_obj().ssid,
                           current_wifi_state=current_wifi_state)


@main_bp.route("/logout")
@login_required
def logout():
    """User log-out."""
    logout_user()
    return redirect(url_for('auth_bp.login'))


@main_bp.route("/delete")
@login_required
def delete():
    """Factory reset. Delete thing from mainflux. Leave account alive. Delete entries one by one from each table"""
    token = get_account_token()
    thingid= get_thing_id() #not name!!! mainflux thing id. get_node_id returns name
    response = delete_thing(token, thingid)
    if response.ok:
      delete_tables_entries()
      logout_user()
    else:
      flash("Error when trying to factory reset. Please try again after loging in.")
    return redirect(url_for('main_bp.dashboard'))



@main_bp.route('/activatewifi', methods=['POST'])
@login_required
def get_post_js_data_activatewifi():
    """Receives post message from js on-off button to activate wifi."""
    jsdata = request.form['javascript_data']
    if jsdata == 'true':
        activate = 1
    elif jsdata == 'false':
        activate = 0
    else:
        activate = None
    update_wifi_data(activate=activate)
    return jsdata


@main_bp.route('/setsensor', methods=['POST'])
@login_required
def get_post_js_data_setsensor():
    """Receives post message from js on-off button, activates SPECIFIC sensor to default sampling rate."""
    str_sensor_num = request.form['sensor_num']  # Data from js
    state = request.form['box_state']

    sensor_idx = int(str_sensor_num[-2:]) - 1
    new_value = app.config['DEFAULT_SR'] if state == 'true' else 0

    # update rpi db
    update_config_values(sensor_idx, new_value)
    return state

@main_bp.route('/upgrade', methods=['GET','POST'])
@login_required
def dashboard_upgrade():

  try:
    organization = get_user_org() 
    url = host + '/control/grafana/dash_update'
    data = {
      "organization": str(organization)
    }
    headers = {"Content-Type": 'application/json'}
    status= requests.post(url, json=data, headers=headers, verify=ssl_flag)
    print("*****received answer is:", status.json())
    if status.json()['status'] == 'success':
      flash('Dashboard has been upgraded to the last version')
    else:
      flash(str(status.json()['status']))
  except:
      flash('Something went wrong, Try again later')
  return redirect(url_for('auth_bp.login'))
    