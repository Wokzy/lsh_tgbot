
import os
import random
import pickle
import hashlib

from datetime import datetime
from constants import EVENTS_DIR, IMAGES_DIR, EVENTS_FNAME


class Event:
	def __init__(self, name:str, date:datetime, info:str, picture_fname:str = None):
		self.name = name
		self.date = date
		self.picture_fname = picture_fname
		self.info = info


	async def print_event(self, update, context) -> None:
		# TODO
		await context.bot.send_message(update.message.chat.id, info)


def save_event_picture(event:Event):
	# TODO
	fname = f'{random.randint(1, 1<<256)}{datetime.datetime.now().timestamp()}'.encode('utf-8')
	fname = hashlib.sha3_256(fname).hexdigest()
	pass


def load_events() -> dict:
	file_path = os.path.join(EVENTS_DIR, EVENTS_FNAME)
	if not os.path.exists(file_path):
		return {}

	with open(file_path, 'rb') as f:
		events = pickle.load(f)
		f.close()

	return events


def save_events(events:dict) -> None:
	file_path = os.path.join(EVENTS_DIR, EVENTS_FNAME)

	with open(file_path, 'wb') as f:
		pickle.dump(events, f)
		f.close()


def read_event_data_from_user(update, context) -> tuple[str, str]:
	if update.message.photo:
		print(update.message.photo)
	name = update.message.text

	return name, ''



def create_event(current_events:dict, name:str, date:str, info:str, picture = None) -> dict:
	event = Event(name, datetime.datetime.now(), info)
	current_events[date] = event
	save_events(current_events)

	return current_events

