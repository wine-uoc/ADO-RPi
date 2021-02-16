from enum import Enum

from config import ConfigRPI
from rpiapp.db_management import get_table_database


class CmdType(Enum):
	read = 0
	config = 1
	actuate = 2
	calibrate = 3


class SensorType(Enum):
	analog = 0
	digital = 1
	spi = 2
	onewire = 3
	i2c = 4
	serial = 5


def create_cmd(cmdtype, sensortype, param_list):
	num_param = len(param_list)
	# Format parameter list to match A0 (values separated by comma, no spaces, between brackets[] + initial space)
	str_param_list = ' ['
	for i in range(num_param):
		str_param_list = str_param_list + str(param_list[i])
		if i < num_param - 1:
			str_param_list = str_param_list + ','
	str_param_list = str_param_list + ']'

	serialcmd = str(CmdType[cmdtype].value) + str(SensorType[sensortype].value) + str(num_param) + str_param_list +'\n'
	return serialcmd


def parse_cmd(command):
	cmdtype = int(command[0])
	sensorType = int(command[1])
	# extract the parameters of the command : 032 [0,4] -->  0,4
	remaining_command = command[5:len(command)-1-1] #eliminate \n too
	parameter1 = remaining_command.split(',')[0] #string
	return cmdtype, sensorType, parameter1


def get_config():
	"""
	Get information of sensors enabled and default sampling rate from db set by user via web
	:return:
	serialcmd: dict
	periodicity: dict
	magnitudes: dict
	"""
	node_config, _ = get_table_database(None, 'nodeconfig')
	sampling_rates = list(node_config[1:])				# Get only sampling rates ([0] is id, rest are sensors sr)

	# Create commands only if user has enabled one sensor at least
	if sum(sampling_rates) > 0:
		enabled_sensors = [x != 0 for x in sampling_rates]		# List of booleans (True: enabled, False: disabled)

		# Filtering based on list of booleans, get a list of sr's, types and params only of sensors enabled
		sampling_rates_enabled_sensors = [i for (i, v) in zip(sampling_rates, enabled_sensors) if v]
		sensor_types_enabled_sensors = [i for (i, v) in zip(ConfigRPI.SENSOR_TYPES, enabled_sensors) if v]
		sensor_params_enabled_sensors = [i for (i, v) in zip(ConfigRPI.SENSOR_PARAMS, enabled_sensors) if v]
		sensor_magnitudes_enabled_sensors = [i for (i, v) in zip(ConfigRPI.SENSOR_MAGNITUDES, enabled_sensors) if v]

		num_enabled_sensors = len(sampling_rates_enabled_sensors)

		# Create dict of commands from lists
		cmd_types = ['read'] * num_enabled_sensors		# Bc user can only enable/disable sensors in the rpi app
		serialcmd = {i+1: create_cmd(cmd_types[i], sensor_types_enabled_sensors[i], sensor_params_enabled_sensors[i]) for i in range(0, num_enabled_sensors)}

		# Create dict of sampling rates from list
		periodicity = {i+1: sampling_rates_enabled_sensors[i] for i in range(0, num_enabled_sensors)}

		# Create dict of magnitudes from list
		magnitudes = {i+1: sensor_magnitudes_enabled_sensors[i] for i in range(0, num_enabled_sensors)}

		# Create dict of delays from list
		# START_DELAY = 0		# Hardcoded delay!
		# ADDED_DELAY = 3		# Hardcoded delay!
		# delay = {i+1: START_DELAY + i * ADDED_DELAY for i in range(0, num_enabled_sensors)}
	else:
		serialcmd = {}
		periodicity = {}
		magnitudes = {}
		# delay = {}

	return serialcmd, periodicity, magnitudes
