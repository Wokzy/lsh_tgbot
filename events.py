
import os
import random
import pickle
import hashlib

from datetime import datetime
from constants import EVENTS_DIR, IMAGES_DIR, EVENTS_FNAME#, TOTAL_DAYS_WITH_EVENTS


class Event:
	def __init__(self, name:str, date:datetime, description:str, picture_fname:str = None):
		self.name = name
		self.date = date
		self.picture_fname = picture_fname
		self.description = description


	def string_datetime(self) -> str:
		return self.date.strftime('%d.%m %H:%M')

	def string_date(self) -> str:
		return self.date.strftime('%d.%m')

	def string_time(self) -> str:
		return self.date.strftime('%H:%M')


	async def print_event(self, update, context) -> str:
		# TODO

		text = f"<b>{self.name}</b>\n\n{self.description}\n\n<b>{self.string_datetime()}</b>"
		await context.bot.send_message(context._chat_id, text = text, parse_mode="HTML")


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

