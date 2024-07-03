"""
Bot backend utilities
"""
import os
import json
import pickle

from datetime import datetime
from constants import (
	DATETIME_INPUT_FORMAT,
	IMAGES_DIR,
	KOMSA_LIST_FNAME,
	STATIC_DATA_FNAME,
)

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
		return date.replace(year=datetime.now().year, month=8)
	except ValueError:
		return None


async def save_photo(context, picture) -> str:
	""" If photo hasnt been saved already, download it to drive """

	fname = picture.file_id
	if fname in os.listdir(IMAGES_DIR):
		return fname

	file = await context.bot.getFile(picture)
	file_path = os.path.join(IMAGES_DIR, fname)
	await file.download_to_drive(file_path)

	return fname


async def load_photo(context, file_id):
	""" Prepare photo instance to be sent by bot.send_photo method """

	photo = await context.bot.getFile(file_id)
	if not photo:
		photo = open(os.path.join(IMAGES_DIR, file_id), 'rb')
	else:
		if file_id not in os.listdir(IMAGES_DIR):
			await save_photo(context, file_id)
		photo = file_id

	return photo


def load_static_data() -> dict:
	if STATIC_DATA_FNAME not in os.listdir():
		return {}

	with open(STATIC_DATA_FNAME, 'rb') as f:
		return pickle.load(f)


def save_static_data(data:dict) -> None:
	print('saving static data')

	with open(STATIC_DATA_FNAME, 'wb') as f:
		pickle.dump(data, f)


def load_komsa_list() -> dict:
	if KOMSA_LIST_FNAME not in os.listdir():
		return {}

	with open(KOMSA_LIST_FNAME, 'rb') as f:
		return pickle.load(f)


def save_komsa_list(data:dict) -> None:
	with open(KOMSA_LIST_FNAME, 'wb') as f:
		pickle.dump(data, f)


async def print_komsa_description(context, description:dict, reply_markup=None):

	if description['photo'] is not None:
		await context.bot.send_photo(context._chat_id,
									 photo=await load_photo(context, description['photo']),
									 caption=description['description'],
									 reply_markup=reply_markup)
	else:
		await context.bot.send_message(context._chat_id, text=description['description'], reply_markup=reply_markup)
