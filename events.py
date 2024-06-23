
import os
import random
import pickle
import hashlib

from datetime import datetime
from constants import EVENTS_DIR, IMAGES_DIR, EVENTS_FNAME#, TOTAL_DAYS_WITH_EVENTS


class Event:
	def __init__(self, name:str = 'None', date:datetime = datetime.now(), 
						description:str = 'None', picture_file_id:str = None):
		self.name = name
		self.datetime = date
		self.picture_file_id = picture_file_id
		self.description = description


	def string_datetime(self) -> str:
		return self.datetime.strftime('%d.%m %H:%M')

	def string_date(self) -> str:
		return self.datetime.strftime('%d.%m')

	def string_time(self) -> str:
		return self.datetime.strftime('%H:%M')


	async def print_event(self, update, context, reply_markup = None) -> str:
		# TODO

		text = f"**{self.name}**\n\n{self.description}\n\n**{self.string_datetime()}**"

		if self.picture_file_id is not None:
			photo = await context.bot.getFile(self.picture_file_id)
			if not photo:
				photo = open(os.path.join(IMAGES_DIR, fname), 'rb')
			else:
				photo = self.picture_file_id

			await context.bot.send_photo(context._chat_id, caption = text, parse_mode="Markdown", photo = photo, reply_markup = reply_markup)
		else:
			await context.bot.send_message(context._chat_id, text = text, parse_mode="Markdown", reply_markup = reply_markup)


async def save_event_picture(bot, picture) -> str:
	""" Returns filename of picture """
	# fname = f'{random.randint(1, 1<<256)}{datetime.datetime.now().timestamp()}'.encode('utf-8')
	# fname = hashlib.sha3_256(fname).hexdigest()

	fname = picture.file_id
	if fname in os.listdir(IMAGES_DIR):
		return fname

	file = await bot.getFile(picture)
	file_path = os.path.join(IMAGES_DIR, fname)
	await file.download_to_drive(file_path)

	return fname


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

