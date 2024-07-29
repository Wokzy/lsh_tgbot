"""
Bot backend utilities
"""
import os
import copy
import json
import pickle

from datetime import datetime
from constants import (
	DATETIME_INPUT_FORMAT,
	IMAGES_DIR,
	KOMSA_LIST_FNAME,
	STATIC_DATA_FNAME,
	EVENTS_FNAME,
	EVENTS_DIR
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



def update_object_instance(instance, obj):
	""" 
	Pass instance and empty initialized objects
	This function will recreate object
	and transfer data from old instances
	"""

	instance_attrs = dir(instance)
	new_instance = copy.deepcopy(obj)

	for attr in instance_attrs:
		if attr.startswith("__") or attr.endswith("__"):
			continue

		setattr(new_instance, attr, getattr(instance, attr))

	return new_instance


def load_static_data(objects_map) -> dict:
	if STATIC_DATA_FNAME not in os.listdir():
		return {}

	with open(STATIC_DATA_FNAME, 'rb') as f:
		static_data = pickle.load(f)

	for key, obj in objects_map.items():
		if key not in static_data.keys():
			continue

		if isinstance(static_data[key], list):
			for i in range(len(static_data[key])):
				static_data[key][i] = update_object_instance(static_data[key][i], obj)
		elif isinstance(static_data[key], dict):
			for i in static_data[key]:
				static_data[key][i] = update_object_instance(static_data[key][i], obj)
		else:
			static_data[key] = update_object_instance(static_data[key], obj)

	return static_data


def load_events(event_object) -> dict:
	file_path = os.path.join(EVENTS_DIR, EVENTS_FNAME)
	if not os.path.exists(file_path):
		return {}, {}

	with open(file_path, 'rb') as f:
		#events = pickle.load(f) # DEPRECATED
		event_mapping = pickle.load(f)

	_delete = []
	for event_id in event_mapping.keys():
		if event_mapping[event_id].datetime.month != 8:
			_delete.append(event_id)
			continue

		event_mapping[event_id] = update_object_instance(event_mapping[event_id], event_object)

	for event_id in _delete:
		del event_mapping[event_id]

	events = {}
	for event in event_mapping.values():
		if event.string_date() not in events.keys():
			events[event.string_date()] = {}

		events[event.string_date()][event.string_time()] = event

	return events, event_mapping


def load_komsa_list() -> dict:
	if KOMSA_LIST_FNAME not in os.listdir():
		return {}

	with open(KOMSA_LIST_FNAME, 'rb') as f:
		komsa_list = pickle.load(f)

	# for key in komsa_list.keys():
	# 	komsa_list[key] = update_object_instance(komsa_list[key], user_instance)

	return komsa_list


def save_events(events:dict) -> None:
	file_path = os.path.join(EVENTS_DIR, EVENTS_FNAME)

	with open(file_path, 'wb') as f:
		pickle.dump(events, f)


def save_static_data(data:dict) -> None:
	print('saving static data')

	with open(STATIC_DATA_FNAME, 'wb') as f:
		pickle.dump(data, f)


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
