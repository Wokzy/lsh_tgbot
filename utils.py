"""
Bot backend utilities
"""
import json

class clr:
	"""
		Logging colors
	"""
	blue = '\033[94m'
	cyan = '\033[96m'
	green = '\033[92m'
	yellow = '\033[93m'
	red = '\033[91m'
	white = '\033[0m'
	bold = '\033[1m'


def read_config(filename:str = 'config.json') -> dict:

	file = open('config.json', 'r')
	config = json.load(file)
	file.close()

	return config

