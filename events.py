
import os
import utils
import random
import pickle
import hashlib

from datetime import datetime
from telegram import InlineKeyboardButton
from constants import BUTTON_NAMINGS


class Event:
	def __init__(self, name:str = 'None', date = datetime.now().replace(month=8), 
						description:str = 'None', picture_file_id:str = None, hidden:bool = False,
						event_id:int = random.randint(1, 1<<64)):
		self.name = name
		self.picture_file_id = picture_file_id
		self.description = description

		if isinstance(date, float):
			self.datetime = datetime.fromtimestamp(date)
		else:
			self.datetime = date

		self.hidden = bool(hidden)

		self.event_id = int(event_id)


	def __eq__(self, another) -> bool:
		return self.event_id == another.event_id


	def to_json(self) -> dict:

		return {
				"name":self.name,
				"date":self.datetime.timestamp(),
				"picture_file_id":self.picture_file_id,
				"description":self.description,
				"hidden":self.hidden,
				"event_id":self.event_id
		}


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


def get_event_keyboard(user, event):
	day, time = event.string_date(), event.string_time()

	keyboard = [[InlineKeyboardButton(BUTTON_NAMINGS.main_menu, callback_data='main_menu force_message')]]

	if user.notifications_flag:
		if event.event_id not in user.notify_events:
			keyboard[0].append(InlineKeyboardButton(BUTTON_NAMINGS.notify,
				callback_data=f'setup_notification enable {day} {time}'))
		else:
			keyboard[0].append(InlineKeyboardButton(BUTTON_NAMINGS.disnotify,
				callback_data=f'setup_notification disable {day} {time}'))

	if user.role == 'root':
		keyboard.append([InlineKeyboardButton(BUTTON_NAMINGS.modify_event,
				 				callback_data=f'event_modification change_existing_event {day} {time}'),
						InlineKeyboardButton(BUTTON_NAMINGS.remove_event,
								callback_data=f'remove_event {day} {time} enquire'),
						])

		if event.hidden:
			keyboard.append([InlineKeyboardButton(BUTTON_NAMINGS.reveal_event,
												  callback_data=f"get_events reveal {day} {time}")])
		else:
			keyboard.append([InlineKeyboardButton(BUTTON_NAMINGS.hide_event,
												  callback_data=f"get_events hide {day} {time}")])

	return keyboard

