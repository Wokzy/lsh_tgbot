"""
Bot backend utilities
"""
import os
import json

from datetime import datetime
from constants import DATETIME_INPUT_FORMAT, IMAGES_DIR

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


def read_date_from_message(message:str, form = DATETIME_INPUT_FORMAT):
	try:
		date = datetime.strptime(message, form)
		return date.replace(datetime.now().year)
	except ValueError:
		return None


async def load_photo(context, file_id):
	""" Prepare photo instance to be sent by bot.send_photo method """

	photo = await context.bot.getFile(file_id)
	if not photo:
		photo = open(os.path.join(IMAGES_DIR, file_id), 'rb')
	else:
		photo = file_id

	return photo


async def save_photo(context, picture) -> str:
	""" If photo hasnt been saved already, download it to drive """

	fname = picture.file_id
	if fname in os.listdir(IMAGES_DIR):
		return fname

	file = await context.bot.getFile(picture)
	file_path = os.path.join(IMAGES_DIR, fname)
	await file.download_to_drive(file_path)

	return fname
