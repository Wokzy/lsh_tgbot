"""
Bot backend utilities
"""
import os
import copy
import json
import pickle
import shutil

from datetime import datetime
from constants import (
	DATETIME_INPUT_FORMAT,
	IMAGES_DIR,
	KOMSA_LIST_FNAME,
	STATIC_DATA_FNAME,
	EVENTS_FNAME,
	EVENTS_DIR,
	USERS_FNAME,
	EVENTS_JSON_FNAME,
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

	try:
		photo = await context.bot.getFile(file_id)
		if file_id not in os.listdir(IMAGES_DIR):
			await save_photo(context, file_id)
		photo = file_id
	except Exception as e:
		print(e)
		photo = open(os.path.join(IMAGES_DIR, file_id), 'rb')

	return photo


async def send_photo(context, photo, caption, chat_id=None, reply_markup=None):
	if chat_id is None:
		chat_id = context._chat_id
	message = await context.bot.send_photo(chat_id,
										   caption=caption,
										   photo=photo,
										   parse_mode="HTML",
										   reply_markup=reply_markup)

	if not isinstance(photo, str):
		return await save_photo(context, message.photo[-1])

	return



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


def load_static_data() -> dict:
	if STATIC_DATA_FNAME not in os.listdir():
		return {}

	with open(STATIC_DATA_FNAME, 'rb') as f:
		static_data = pickle.load(f)


	# for key, obj in objects_map.items():
	# 	if key not in static_data.keys():
	# 		continue

	# 	if isinstance(static_data[key], list):
	# 		for i in range(len(static_data[key])):
	# 			static_data[key][i] = update_object_instance(static_data[key][i], obj)
	# 	elif isinstance(static_data[key], dict):
	# 		for i in static_data[key]:
	# 			static_data[key][i] = update_object_instance(static_data[key][i], obj)
	# 	else:
	# 		static_data[key] = update_object_instance(static_data[key], obj)

	return static_data


def load_events(event_object) -> dict:
	# file_path = os.path.join(EVENTS_DIR, EVENTS_FNAME)
	file_path = os.path.join(EVENTS_DIR, EVENTS_JSON_FNAME)
	if not os.path.exists(file_path):
		return {}, {}

	with open(file_path, 'r') as f:
		# events = pickle.load(f) # DEPRECATED
		event_mapping = json.load(f)
		# event_mapping = pickle.load(f)

	event_mapping = {int(key):event_object(**value) for key, value in event_mapping.items()}

	# _delete = []
	# for event_id in event_mapping.keys():
	# 	if event_mapping[event_id].datetime.month != 8:
	# 		_delete.append(event_id)
	# 		continue

	# 	event_mapping[event_id] = update_object_instance(event_mapping[event_id], event_object)

	# for event_id in _delete:
	# 	del event_mapping[event_id]

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


def load_users(user_obj) -> dict:
	if USERS_FNAME not in os.listdir():
		return {}

	with open(USERS_FNAME, 'r') as f:
		users = json.load(f)

	return {user['user_id']:user_obj(**user) for user in users}


def save_events(events:dict) -> None:
	# file_path = os.path.join(EVENTS_DIR, EVENTS_FNAME)
	file_path = os.path.join(EVENTS_DIR, EVENTS_JSON_FNAME)

	out = {key:value.to_json() for key, value in events.items()}
	with open(file_path, 'w') as f:
		json.dump(out, f)


def save_static_data(data:dict) -> None:
	print('saving static data')

	# shutil.copyfile(STATIC_DATA_FNAME, f'_backups/{STATIC_DATA_FNAME}_{int(datetime.now().timestamp())}.bin')

	with open(STATIC_DATA_FNAME, 'wb') as f:
		try:
			pickle.dump(data, f)
		except Exception as e:
			print(e)
			# print(data)


def save_komsa_list(data:dict) -> None:
	with open(KOMSA_LIST_FNAME, 'wb') as f:
		pickle.dump(data, f)


def save_users(users:list) -> None:

	out = [user.to_json() for user in users]
	with open(USERS_FNAME, 'w') as f:
		json.dump(out, f)



async def print_komsa_description(context, description:dict, user, reply_markup=None):

	name = user.auth_data.get('name', '')
	surname = user.auth_data.get('surname', '')
	text = f"<b>{name} {surname}</b>\n\n{description['description']}"

	if description['photo'] is not None:
		output = await send_photo(context,
								  photo=await load_photo(context, description['photo']),
								  caption=text,
								  reply_markup=reply_markup)

		if isinstance(output, str):
			description['photo'] = output
	else:
		await context.bot.send_message(context._chat_id,
									   text=text,
									   parse_mode="HTML",
									   reply_markup=reply_markup)


