
import os
import utils
import random
import pickle
import hashlib

from datetime import datetime


class Event:
	def __init__(self, name:str = 'None', date:datetime = datetime.now().replace(month=8), 
						description:str = 'None', picture_file_id:str = None):
		self.name = name
		self.datetime = date
		self.picture_file_id = picture_file_id
		self.description = description

		self.hidden = False

		self.event_id = random.randint(1, 1<<64)


	def __eq__(self, another) -> bool:
		return self.event_id == another.event_id


	def string_datetime(self) -> str:
		return self.datetime.strftime('%d.%m %H:%M')

	def string_date(self) -> str:
		return self.datetime.strftime('%d.%m')

	def string_time(self) -> str:
		return self.datetime.strftime('%H:%M')


	async def print_event(self, update, context, reply_markup = None) -> str:
		# TODO

		text = f"*{self.string_datetime()}*\n\n*{self.name}*\n\n{self.description}"

		if self.picture_file_id is not None:

			photo = await utils.load_photo(context, self.picture_file_id)
			await context.bot.send_photo(context._chat_id, caption=text, parse_mode="Markdown", photo=photo, reply_markup=reply_markup)
		else:
			await context.bot.send_message(context._chat_id, text=text, parse_mode="Markdown", reply_markup=reply_markup)


def read_event_data_from_user(update, context) -> tuple[str, str]:
	if update.message.photo:
		print(update.message.photo)
	name = update.message.text

	return name, ''

