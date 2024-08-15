"""
Module for event "Wolf of Pirogova Street"

"""

import os
import sys
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
USERS_LIST_FNAME = os.path.join(MODULES_DIR, 'wops_users_list.txt')
MODULE_USER_MODE_NAME = 'Волк с Пирогова Стрит'

WOPS_MESSAGES = {
	"enter":f"Вы перешли в режим {MODULE_USER_MODE_NAME}",
	"return_to_mode_error":f"Вернитесь в режим {MODULE_USER_MODE_NAME}",
	"update_news":"Введите новые новости (это может быть только текст) (Поддерживается HTML форматирование, но будте осторожны со спецсимволами, например <>)",
	"news_were_updated":"Новости были обновлены",
	"wrong_data_type" : "Некорректный тип данных",
}

class WOPS_BUTTON_NAMINGS:
	wops_main_menu             = "Игровое меню"
	make_request               = "Отправить данные"
	latest_news                = "Последние новости"
	send_calc_results          = "Отправить результаты подсчётов пользователям"
	update_news                = "Обновить новости"
	change_calc_function       = "Обновить функцию подсчёта данных"
	make_move                  = "Сделать ход"
	change_p                   = "Изменить цену товара"
	change_q                   = "Изменить объем товара"
	change_science             = "Вложиться в науку"
	change_advert              = "Вложиться в рекламу"
	get_back                   = "Вернуться назад"
	try_again                  = "Попробовть снова"
	finish_move                = "Завершить свой ход"
	take_loan                  = "Взять кредит"
	finish_game_state          = "Завершить ход для всех"
	get_top_players            = "Список лучших игроков"
	confirm                    = "Подтвердить"
	decline                    = "Отметить"
	wops_change_calc_constants = "Изменить игровые константы"


def get_handlers(instance):

	command_handlers = {
		"wops_users_len"      : instance.print_users_len,
		"wops_echo"           : instance.wops_echo,
		"wops_drop_all_stats" : instance.wops_drop_all_stats
	}

	callback_handlers = {
		instance.wops_enter                 : "wops_enter",
		instance.wops_main_menu             : "wops_main_menu",
		instance.get_latest_news            : "get_latest_news",
		instance.update_news                : "update_news",
		instance.wops_change_param          : "wops_change_param",
		instance.wops_take_loan             : "wops_take_loan",
		instance.wops_make_move             : "wops_make_move",
		instance.wops_finish_move           : "wops_finish_move",
		instance.wops_finish_game_state     : "wops_finish_game_state",
		instance.wops_get_top_players       : "wops_get_top_players",
		instance.wops_change_calc_constants : "wops_change_calc_constants",
	}
	return command_handlers, callback_handlers


async def return_to_mode_error(update, context):
	await context.bot.send_message(context._chat_id,
				text=WOPS_MESSAGES['return_to_mode_error'])


def wops_main_menu_keyboard():
	return InlineKeyboardMarkup([[InlineKeyboardButton(WOPS_BUTTON_NAMINGS.wops_main_menu, callback_data="wops_main_menu")]])


def verify_user(user) -> bool:
	if user.role == 'root':
		return True

	auth_data = user.auth_data
	if 'name' not in auth_data or 'surname' not in auth_data or 'grade' not in auth_data:
		return False

	with open(USERS_LIST_FNAME, 'r') as f:
		for line in f:
			name, surname, grade = line.strip().split(' ')
			# print(name, surname, grade)
			# print(auth_data['name'] == name, auth_data['surname'] == surname, auth_data['grade'] == grade)
			if auth_data['name'] == name and auth_data['surname'] == surname and auth_data['grade'] == grade:
				return True

	return False

global CALC_CONSTANTS
CALC_CONSTANTS = {'a':1,
				  'b':1,
				  'c':300,
				  'd':0.03,
				  'A':80,
				  'beta':1,
				  'science_level_price':100_000,
				  'advert_level_price':100_000,
				  'r':.15,
				}


def pq_function(calc_data) -> float:
	return  #*CALC_CONSTANTS['c'] - CALC_CONSTANTS['d']*calc_data['q']


def qd_function(calc_data) -> float:
	# return CALC_CONSTANTS['a'] - CALC_CONSTANTS['b']*calc_data['p']
	return max(0, (calc_lambda(calc_data['advert']) * CALC_CONSTANTS['c']) / CALC_CONSTANTS['d'])


def calc_beta(investment):
	x = investment // CALC_CONSTANTS['science_level_price']
	return 1 - .5 * (1 - (1 / 1.2)**x)

def calc_lambda(investment):
	x = investment // CALC_CONSTANTS['advert_level_price']
	return 1 + .25 * (1 - (1 / 1.2)**x)


def calculate_profit(calc_data) -> float:
	p0 = calc_data['p']
	q0 = calc_data['q']
	science = calc_data['science']
	calc_data['last_profit'] = (p0 * min(q0, qd_function(calc_data))) - (q0*CALC_CONSTANTS['A']*calc_beta(science)) - calc_data['loan']*(1 + CALC_CONSTANTS['r'])
	calc_data['balance'] += calc_data['last_profit']


def loan_is_profitable(calc_data) -> bool:
	return calc_data['p'] > calc_beta(calc_data['science'])*CALC_CONSTANTS['A']*(1 + CALC_CONSTANTS['r'])



DEFAULT_USER_DATA = {"balance":600_000, 
					 'p':0,
					 'q':0,
					 'loan':0,
					 'science':0,
					 'advert':0,
					 'last_profit':0, # Profit from last move
					 "finished_move":False}


class WOPSModule:
	def __init__(self, users):
		self.users = users

		self.user_data, self.latest_news, _calc_constants = self.load() # {user_id:data}

		global CALC_CONSTANTS
		if len(_calc_constants.keys()) == len(CALC_CONSTANTS):
			CALC_CONSTANTS = _calc_constants

		self.calculation_requests = {} # {request_id:}


	async def print_users_len(self, update, context):
		if self.users[context._user_id].role != "root":
			return

		print(f"module_wops_users_len: {len(self.users)}")


	async def wops_echo(self, update, context):
		print(self.user_data)
		await context.bot.send_message(context._chat_id, text="echo")


	async def wops_message_handler(self, update, context):

		if update.message.text is None:
			return

		user = self.users[context._user_id]
		if user.current_state == "update_news":
			await self.update_news(update, context)
		elif user.current_state == 'take_loan':
			await self.wops_take_loan(update, context)
		elif user.current_state is not None:
			if 'wops_change_param' in user.current_state:
				await self.wops_change_param(update, context)
			elif 'wops_change_calc_constants' in user.current_state:
				await self.wops_change_calc_constants(update, context)


	async def wops_enter(self, update, context):

		user = self.users[context._user_id]

		if not verify_user(user):
			await context.bot.answer_callback_query(update.callback_query.id, text="Это меню вам не доступно")
			return

		user.user_mode = "wops"

		if user.user_id not in self.user_data and user.role == 'user':
			self.user_data[user.user_id] = DEFAULT_USER_DATA

		await context.bot.answer_callback_query(update.callback_query.id, text=WOPS_MESSAGES["enter"])
		await self.wops_main_menu(update, context)


	async def wops_main_menu(self, update, context):
		await context.bot.answer_callback_query(update.callback_query.id)

		user = self.users[context._user_id]
		user.current_state = None

		keyboard = [[InlineKeyboardButton(WOPS_BUTTON_NAMINGS.latest_news, callback_data="get_latest_news")]]

		text = "Главное меню <b>Волк с Пирогова Стрит</b>"
		if user.role == 'user':
			keyboard.append([InlineKeyboardButton(WOPS_BUTTON_NAMINGS.make_move, callback_data="wops_make_move")])
		elif user.role == 'root':
			keyboard.append([InlineKeyboardButton(WOPS_BUTTON_NAMINGS.update_news, callback_data="update_news")])
			keyboard.append([InlineKeyboardButton(WOPS_BUTTON_NAMINGS.get_top_players, callback_data="wops_get_top_players")])
			keyboard.append([InlineKeyboardButton(WOPS_BUTTON_NAMINGS.finish_game_state, callback_data="wops_finish_game_state default")])
			keyboard.append([InlineKeyboardButton(WOPS_BUTTON_NAMINGS.wops_change_calc_constants, callback_data="wops_change_calc_constants default")])

		keyboard = InlineKeyboardMarkup(keyboard)

		if update.callback_query is not None and update.callback_query.message.text is not None:
			await update.callback_query.edit_message_text(text=text, parse_mode="HTML", reply_markup=keyboard)
		else:
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


	async def wops_make_move(self, update, context):

		if update.callback_query is not None:
			await context.bot.answer_callback_query(update.callback_query.id)

		user = self.users[context._user_id]
		user_data = self.user_data[user.user_id]
		if user_data['finished_move']:
			await context.bot.send_message(user.chat_id,
										   text='Вы уже завершили свой ход')
			return

		top_users = list(self.user_data.keys())
		top_users.sort(key = lambda user_id: self.user_data[user_id]['balance'])


		text =  "Ваши текущие параметры:\n" + \
				f"<b>Ваш текущий капитал:</b> {user_data['balance']}\n" + \
				f"<b>Цена товара:</b> {user_data['p']}\n" + \
				f"<b>Объём товара:</b> {user_data['q']}\n" + \
				f"<b>Кредит в этом ходу (ставка {CALC_CONSTANTS['r']*100}%):</b> {user_data['loan']}\n" + \
				f"<b>Сумма, вложенная в науку:</b> {user_data['science']}\n" + \
				f"<b>Сумма, вложенная в рекламу:</b> {user_data['advert']}\n\n" + \
				f"Вы находитесь на <b>{top_users.index(user.user_id) + 1} месте</b> среди остальных команд\n\n" + \
				"Здесь вы можете совершить следующие действия:"

		keyboard =  [
					[InlineKeyboardButton(WOPS_BUTTON_NAMINGS.wops_main_menu, callback_data="wops_main_menu")],
					[InlineKeyboardButton(WOPS_BUTTON_NAMINGS.change_p, callback_data="wops_change_param p")],
					[InlineKeyboardButton(WOPS_BUTTON_NAMINGS.change_q, callback_data="wops_change_param q")],
					[InlineKeyboardButton(WOPS_BUTTON_NAMINGS.change_science, callback_data="wops_change_param science")],
					[InlineKeyboardButton(WOPS_BUTTON_NAMINGS.change_advert, callback_data="wops_change_param advert")],
					]

		if user_data['loan'] == 0.0:
			keyboard.append([InlineKeyboardButton(WOPS_BUTTON_NAMINGS.take_loan, callback_data="wops_take_loan")])

		keyboard.append([InlineKeyboardButton(WOPS_BUTTON_NAMINGS.finish_move, callback_data="wops_finish_move default")])
		keyboard = InlineKeyboardMarkup(keyboard)

		await update.callback_query.edit_message_text(text=text, reply_markup=keyboard, parse_mode='HTML')


	async def wops_change_param(self, update, context):

		user = self.users[context._user_id]
		user_data = self.user_data[user.user_id]

		async def __wrong_input_type(update, context, param):
			if update.message.text.isnumeric():
				return False
			reply_markup = [[InlineKeyboardButton(WOPS_BUTTON_NAMINGS.try_again, callback_data=f"wops_change_param {param}")],
							[InlineKeyboardButton(WOPS_BUTTON_NAMINGS.wops_main_menu, callback_data="wops_main_menu")]]
			await context.bot.send_message(context._chat_id,
									 text=WOPS_MESSAGES['wrong_data_type'],
									 reply_markup=InlineKeyboardMarkup(reply_markup),
									 )
			return True

		if update.callback_query is not None:
			await context.bot.answer_callback_query(update.callback_query.id)
			param = update.callback_query.data.split(' ')[1]

			keyboard = [[InlineKeyboardButton(WOPS_BUTTON_NAMINGS.get_back, callback_data="wops_make_move")]]
			keyboard = InlineKeyboardMarkup(keyboard)

			_parameter_text = {
							"p"       :"Введите новую цену товара (целое число):",
							"q"       :"Введите новый объем товара (целое число):",
							"science" :"Введите сумму, которую хотите вложить в науку (целое число):",
							"advert"  :"Введите сумму, которую хотите вложить в рекламу (целое число):",
			}

			user.current_state = f"wops_change_param {param}"
			await update.callback_query.edit_message_text(
										   text=_parameter_text[param],
										   reply_markup=keyboard)
			return


		param = user.current_state.split(' ')[1]
		user.current_state = None

		if await __wrong_input_type(update, context, param):
			return

		value = int(update.message.text)

		if param == "p" or param == 'q':
			user_data[param] = value
		else:
			if value > user_data['balance']:
				reply_markup = [[InlineKeyboardButton(WOPS_BUTTON_NAMINGS.try_again, callback_data=f"wops_change_param {param}")],
								[InlineKeyboardButton(WOPS_BUTTON_NAMINGS.wops_main_menu, callback_data="wops_main_menu")]]
				await context.bot.send_message(user.chat_id,
											   text="Недостаточно средств на балансе",
											   reply_markup=InlineKeyboardMarkup(reply_markup))
				return

			user_data[param] += value
			user_data['balance'] -= value

		await context.bot.send_message(user.chat_id,
									   text="Успешно",
									   reply_markup=wops_main_menu_keyboard())


	async def wops_finish_move(self, update, context):
		await context.bot.answer_callback_query(update.callback_query.id)

		user = self.users[context._user_id]
		user_data = self.user_data[user.user_id]
		state = update.callback_query.data.split(' ')[1]

		if state == 'default':
			keyboard = [[InlineKeyboardButton(WOPS_BUTTON_NAMINGS.confirm, callback_data="wops_finish_move confirm"),
						 InlineKeyboardButton(WOPS_BUTTON_NAMINGS.decline, callback_data="wops_main_menu"),],]
			keyboard = InlineKeyboardMarkup(keyboard)
			text = "Вы уверены, что хотите <b>завершить свой ход?</b>\n После этого вы <b>не сможете отредактировать</b> свои параметры до получения прибыли"

			await update.callback_query.edit_message_text(text=text, reply_markup=keyboard, parse_mode="HTML")
			return

		calculate_profit(user_data)
		user_data['finished_move'] = True

		await update.callback_query.edit_message_text(text='Вы завершили свой ход', reply_markup=wops_main_menu_keyboard())


	async def wops_take_loan(self, update, context):
		user = self.users[context._user_id]
		user_data = self.user_data[user.user_id]


		if update.callback_query is not None:
			await context.bot.answer_callback_query(update.callback_query.id)

			# if not loan_is_profitable(user_data):
			# 	keyboard = [[InlineKeyboardButton(WOPS_BUTTON_NAMINGS.wops_main_menu, callback_data="wops_main_menu")],
			# 				[InlineKeyboardButton(WOPS_BUTTON_NAMINGS.change_p, callback_data="wops_change_param p")],]
			# 	text='Согласно вашим текущим параметрам - кредит не выгоден, попробуйте изменить цену товара'

			# 	await update.callback_query.edit_message_text(text=text, reply_markup=InlineKeyboardMarkup(keyboard))
			# 	return

			user.current_state = 'take_loan'
			await update.callback_query.edit_message_text(
								text="Введите сумму, которую хотите взять в кредит (целое число)",
								reply_markup=wops_main_menu_keyboard())
			return

		user.current_state = None

		if not update.message.text.isnumeric():
			await context.bot.send_message(user.chat_id,
										   text=WOPS_MESSAGES['wrong_data_type'],
										   reply_markup=wops_main_menu_keyboard())
			return

		user_data['loan'] = int(update.message.text)
		user_data['balance'] += user_data['loan']
		await context.bot.send_message(user.chat_id,
									   text=f"Вы успешно взяли кредит в размере {user_data['loan']} под {CALC_CONSTANTS['r']*100}%",
									   reply_markup=wops_main_menu_keyboard())


	async def wops_change_calc_constants(self, update, context):
		user = self.users[context._user_id]

		if update.callback_query is not None:
			await context.bot.answer_callback_query(update.callback_query.id)

			param = update.callback_query.data.split(' ')[1]
			if param == 'default':
				text = "Текущие значения констант:\n\nc: {}\nd: {}\nr: {}\nA: {}".format(
										CALC_CONSTANTS['c'],
										CALC_CONSTANTS['d'],
										CALC_CONSTANTS['r'],
										CALC_CONSTANTS['A'])

				keyboard = [[InlineKeyboardButton(f'Изменить константу {c}', callback_data=f"wops_change_calc_constants {c}")] for c in ('c', 'd', 'r', 'A')]
				keyboard = InlineKeyboardMarkup(keyboard)

				await update.callback_query.edit_message_text(text=text, reply_markup=keyboard)
				return


			_parameter_text = {
							"c"       :"Введите значение параметра c:",
							"d"       :"Введите значение параметра d:",
							"r"       :"Введите новую ставку по кредиту в виде десятичной дроби (0.15) - ставка 15%",
							"A"       :"Введите значение параметра A:",
			}

			user.current_state = f"wops_change_calc_constants {param}"
			await update.callback_query.edit_message_text(text=_parameter_text[param], reply_markup=wops_main_menu_keyboard())
			return

		param = user.current_state.split(' ')[1]
		user.current_state = None

		if not update.message.text.replace('.', '').isnumeric():
			await context.bot.send_message(user.chat_id,
					text='Некорректный тип данных, дробные числа вводите через точку',
					reply_markup=wops_main_menu_keyboard())
			return

		CALC_CONSTANTS[param] = float(update.message.text)
		await context.bot.send_message(user.chat_id,
						text=f'Константа {param} была успешно изменена',
						reply_markup=wops_main_menu_keyboard())


	async def wops_finish_game_state(self, update, context):
		await context.bot.answer_callback_query(update.callback_query.id)

		state = update.callback_query.data.split(' ')[1]

		if state == 'default':
			keyboard = [[InlineKeyboardButton(WOPS_BUTTON_NAMINGS.confirm, callback_data="wops_finish_game_state confirm"),
						 InlineKeyboardButton(WOPS_BUTTON_NAMINGS.decline, callback_data="wops_main_menu"),],]
			keyboard = InlineKeyboardMarkup(keyboard)
			text = "Вы уверены, что хотите <b>завершить ход для всех и подсчитать прибыль?</b>\n"

			await update.callback_query.edit_message_text(text=text, reply_markup=keyboard, parse_mode="HTML")
			return

		for user_id, user_data in self.user_data.items():
			user = self.users[user_id]
			user_data = self.user_data[user.user_id]

			if not user_data['finished_move']:
				calculate_profit(user_data)

			user_data['finished_move'] = False
			user_data['loan'] = 0

			_text = f"Игровая стадия завершена, ваша прибыль составила: {user_data['last_profit']}\n" + \
					f"Ваш текущий баланс: {user_data['balance']}"
			await context.bot.send_message(user.chat_id, text=_text, reply_markup=wops_main_menu_keyboard())

		await update.callback_query.edit_message_text(
									   text='Вы завершили игровую стадию',
									   reply_markup=wops_main_menu_keyboard())


	async def wops_get_top_players(self, update, context):
		await context.bot.answer_callback_query(update.callback_query.id)

		lst = list(self.user_data.keys())
		lst.sort(key = lambda user_id: self.user_data[user_id]['balance'])

		iterator = 0

		text = f"Вот пятёрка игроков с самым высоким балансом:\n\n"
		for user_id in lst:
			if self.users[user_id].role != 'user':
				continue

			iterator += 1
			auth_data = self.users[user_id].auth_data
			user_data = self.user_data[user_id]
			text += f"{iterator}. {auth_data['name']} {auth_data['surname']} {auth_data['grade']} имеет баланс: <b>{user_data['balance']}</b>"

			if iterator >= 5:
				break

		await update.callback_query.edit_message_text(text=text, reply_markup=wops_main_menu_keyboard(), parse_mode="HTML")


	async def wops_drop_all_stats(self, update, context):
		if self.users[context._user_id].role != 'root':
			return

		for user_id in self.user_data.keys():
			self.user_data[user_id] = DEFAULT_USER_DATA

		await context.bot.send_message(context._chat_id, text='Статистика всех игроков была сброшена',
									   reply_markup=wops_main_menu_keyboard())


	def save(self) -> None:
		global CALC_CONSTANTS
		with open(SAVE_FNAME, 'w') as f:
			json.dump({'user_data':self.user_data, 'latest_news':self.latest_news, 'CALC_CONSTANTS':CALC_CONSTANTS}, f)


	def load(self) -> tuple:
		if not os.path.exists(SAVE_FNAME) or '--wops-refresh' in sys.argv:
			return {}, "", {}

		with open(SAVE_FNAME, 'r') as f:
			data = json.load(f)


		return {int(key):value for key, value in data['user_data'].items()}, data['latest_news'], data['CALC_CONSTANTS']
