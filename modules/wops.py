"""
Module for event "Wolf of Pirogova Street"

"""

import os
import json
import utils
import datetime

from telegram import (
	InlineKeyboardButton,
	InlineKeyboardMarkup
)

from constants import (
	BUTTON_NAMINGS,
	MISC_MESSAGES,
	MODULES_DIR,
)

SAVE_FNAME = os.path.join(MODULES_DIR, 'wops_save.json')
MODULE_USER_MODE_NAME = 'Волк с Пирогова Стрит'

WOPS_MESSAGES = {
	"enter":f"Вы перешли в режим {MODULE_USER_MODE_NAME}",
	"return_to_mode_error":f"Вернитесь в режим {MODULE_USER_MODE_NAME}",
	"update_news":"Введите новые новости (это может быть только текст) (Поддерживается HTML форматирование, но будте осторожны со спецсимволами, например <>)",
	"news_were_updated":"Новости были обновлены",
}

class WOPS_BUTTON_NAMINGS:
	wops_main_menu       = "Игровое меню"
	make_request         = "Отправить данные"
	latest_news            = "Последние новости"
	send_calc_results    = "Отправить результаты подсчётов пользователям"
	update_news          = "Обновить новости"
	change_calc_function = "Обновить функцию подсчёта данных"


def get_handlers(instance):

	command_handlers = {
		"wops_users_len"                  : instance.print_users_len,
		"wops_change_calculate_functions" : instance.wops_change_calculate_functions,
		"wops_echo"                       : instance.wops_echo,
	}

	callback_handlers = {
		instance.wops_enter      : "wops_enter",
		instance.wops_main_menu  : "wops_main_menu",
		instance.get_latest_news : "get_latest_news",
		instance.update_news     : "update_news",
	}
	return command_handlers, callback_handlers


async def return_to_mode_error(update, context):
	await context.bot.send_message(context._chat_id,
				text=WOPS_MESSAGES['return_to_mode_error'])


def wops_main_menu_keyboard():
	return InlineKeyboardMarkup([[InlineKeyboardButton(WOPS_BUTTON_NAMINGS.wops_main_menu, callback_data="wops_main_menu")]])


def calculate1(calc_data) -> dict:
	pass


def calculate2(calc_data) -> dict:
	pass


DEFAULT_USER_DATA = {"balance":100000, "parametres":{'p':0, 'q':0, 'beta':1}}


class WOPSModule:
	def __init__(self, users):
		self.users = users

		self.user_data, self.latest_news = self.load() # {user_id:data}
		self.calculate_functions = {'calculate1':calculate1, 'calculate2':calculate2}
		self.calculate_function = self.calculate_functions['calculate1']

		self.calculation_requests = {} # {request_id:}


	async def print_users_len(self, update, context):
		if self.users[context._user_id].role != "root":
			return

		print(f"module_wops_users_len: {len(self.users)}")


	async def wops_echo(self, update, context):
		print(self.user_data)
		await context.bot.send_message(context._chat_id, text="echo")


	async def wops_message_handler(self, update, context):

		user = self.users[context._user_id]
		if user.current_state == "update_news":
			await self.update_news(update, context)


	async def wops_enter(self, update, context):
		await context.bot.answer_callback_query(update.callback_query.id)

		user = self.users[context._user_id]
		user.user_mode = "wops"

		if user.user_id not in self.user_data:
			self.user_data[user.user_id] = DEFAULT_USER_DATA

		await context.bot.send_message(context._user_id, text=WOPS_MESSAGES["enter"])
		await self.wops_main_menu(update, context)


	async def wops_main_menu(self, update, context):
		await context.bot.answer_callback_query(update.callback_query.id)

		user = self.users[context._user_id]
		user.current_state = None

		keyboard = [[InlineKeyboardButton(WOPS_BUTTON_NAMINGS.latest_news, callback_data="get_latest_news")]]

		if user.role == 'user':
			text = ""
			keyboard.append([InlineKeyboardButton(WOPS_BUTTON_NAMINGS.make_request, callback_data="wops_make_request default")])
		elif user.role == 'root':
			text = "Главное меню <b>Волк с Пирогова Стрит</b>"
			keyboard.append([InlineKeyboardButton(WOPS_BUTTON_NAMINGS.update_news, callback_data="update_news")])

		keyboard = InlineKeyboardMarkup(keyboard)
		await context.bot.send_message(context._chat_id,
									   text=text,
									   parse_mode="HTML",
									   reply_markup=keyboard)


	async def print_latest_news(self, context, chat_id, reply_markup=wops_main_menu_keyboard()):
		text = f'Последние новости:\n\n{self.latest_news}'
		try:
			await context.bot.send_message(chat_id,
										   text=text,
										   parse_mode="HTML",
										   reply_markup=reply_markup)
		except:
			await context.bot.send_message(chat_id,
										   text=text,
										   reply_markup=reply_markup)


	async def get_latest_news(self, update, context):
		if self.users[context._user_id].user_mode != 'wops':
			await return_to_mode_error(update, context)
			return

		await context.bot.answer_callback_query(update.callback_query.id)
		await self.print_latest_news(context, context._chat_id)


	async def update_news(self, update, context):
		user = self.users[context._user_id]

		if user.user_mode != 'wops':
			await return_to_mode_error(update, context)
			return

		if update.callback_query is not None:
			await context.bot.answer_callback_query(update.callback_query.id)
			await self.print_latest_news(context, context._chat_id, reply_markup=None)

			await context.bot.send_message(context._chat_id,
										   text=WOPS_MESSAGES['update_news'],
										   reply_markup=wops_main_menu_keyboard())

			user.current_state = "update_news"
		else:
			self.latest_news = update.message.text
			await context.bot.send_message(context._chat_id,
										   text=WOPS_MESSAGES['news_were_updated'],
										   reply_markup=wops_main_menu_keyboard())
			user.current_state = None


	async def wops_make_request(self, update, context):
		pass


	async def wops_change_calculate_functions(self, update, context):
		pass


	async def calculate(self, update, context, calculate_request):
		pass


	def save(self) -> None:
		with open(SAVE_FNAME, 'w') as f:
			json.dump({'user_data':self.user_data, 'latest_news':self.latest_news}, f)


	def load(self) -> tuple:
		if not os.path.exists(SAVE_FNAME):
			return {}, ""

		with open(SAVE_FNAME, 'r') as f:
			data = json.load(f)

		return {int(key):value for key, value in data['user_data'].items()}, data['latest_news']
