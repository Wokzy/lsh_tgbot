
import os
import utils
import events
import random
import pickle
import datetime

from telegram import InlineKeyboardButton, InlineKeyboardMarkup

from constants import (
	BUTTON_NAMINGS,
	MISC_MESSAGES,
	)


CONFIG = utils.read_config()


class CallKomsaRequest:
	def __init__(self, sender_id:int, reciever_id:int, description:str):
		self.request_id = random.randint(1, 1<<64)

		self.sender_id = sender_id
		self.reciever_id = reciever_id
		self.description = description

		self.creation_date = datetime.datetime.now()

		self.confirmed_by_user  = False
		self.confirmed_by_tutor = True  # debug mode
		self._filally_confirmed = False


def check_call_request_sender(lst:dict[int, CallKomsaRequest], sender_id:int) -> int:
	for request_id, request in lst.items():
		if request.sender_id == sender_id:
			return request_id

	return 0


async def send_confirm_call_message_to_root(users:dict, request:CallKomsaRequest, context) -> None:
	sender_data = users[request.sender_id].auth_data
	root = users[request.reciever_id]

	text = f'Вас вызывает {sender_data["name"]} {sender_data["surname"]}\n\n' + \
		   f'со следующим описанием:\n\n{request.description}'

	keyboard = [[InlineKeyboardButton(BUTTON_NAMINGS.accept_call_root, callback_data=f"confirm_call_from_root confirm {request.request_id}"),
				 InlineKeyboardButton(BUTTON_NAMINGS.decline_call_root, callback_data=f"confirm_call_from_root decline {request.request_id}")]]

	keyboard = InlineKeyboardMarkup(keyboard)

	await context.bot.send_message(root.chat_id, text=text, reply_markup=keyboard)


async def send_confirm_call_message_to_tutor(users:dict, request:CallKomsaRequest, context) -> None:

	keyboard = [[InlineKeyboardButton(BUTTON_NAMINGS.allow_call_tutor, callback_data=f"confirm_call_from_tutor confirm {request.request_id}"),
				 InlineKeyboardButton(BUTTON_NAMINGS.decline_call_tutor, callback_data=f"confirm_call_from_tutor decline {request.request_id}")]]

	keyboard = InlineKeyboardMarkup(keyboard)
	sender = users[request.sender_id]
	root = users[request.reciever_id]

	text = f'Ученик {sender.auth_data["name"]} {sender.auth_data["surname"]} хочет вызвать к себе комсёнка ' + \
		   f'{root.auth_data["name"]} {root.auth_data["surname"]}. Разрешаете ли вы ему это сделать?\n' + \
		   f'Ученик так же прикрепил описание:\n\n{request.description}'

	for user in users.values():
		if not user.auth_data or user.role != 'tutor':
			continue

		if user.auth_data["grade"] != sender.auth_data["grade"]:
			continue

		await context.bot.send_message(user.chat_id, text=text, reply_markup=keyboard)
		request.confirmed_by_tutor = False

	if request.confirmed_by_tutor:
		await send_confirm_call_message_to_root(users, request, context)



async def handle_event_modification_callback_query(bot, update, context) -> str:
	user = bot.connected_users[context._user_id]

	answer_text = None

	if update.callback_query is not None:
		callback_query = update.callback_query.data.split(' ')[1::]
		state = callback_query[0]
	else:
		state = user.current_state

	if state == 'change_existing_event':
		date, time = callback_query[1], callback_query[2]
		user.modified_event = bot.current_events[date][time]
		user.modified_event_old_position = (date, time)
		answer_text = "Выберите нужный параметр для изменения:"
	elif state == 'event_name':
		if not update.message.text:
			answer_text = "Некорректное название мероприятия"
		else:
			user.modified_event.name = update.message.text # This state is expected to be called from message_handler
	elif state == 'event_date':
		event_datetime = utils.read_date_from_message(update.message.text)
		if not event_datetime:
			answer_text = 'Некорретный формат времени'
		else:
			user.modified_event.datetime = event_datetime
	elif state == 'event_description':
		user.modified_event.description = update.message.text
	elif state == 'event_picture':
		if update.message.photo:
				user.modified_event.picture_file_id = await utils.save_photo(
					context = context, picture = update.message.photo[-1])
	elif state == 'new_event':
		user.modified_event = events.Event()

	if answer_text is not None:
		await context.bot.send_message(context._chat_id, text = answer_text)

	return state


def match_auth_data(data:dict) -> bool:
	""" TODO """
	return True


async def authorize_user(user, update, context) -> bool:
	""" Returns True if success """
	user.current_state = None

	data = update.message.text.split(' ')

	# if context._user_id in CONFIG['ROOT_USERS']:
	# 	user.role = 'root'
	# 	await context.bot.send_message(context._chat_id, text="Вы успешно авторизировались как комсёнок")
	# 	return True

	if len(data) < 3:
		await context.bot.send_message(context._chat_id, text="Некорректный формат")
		return False

	auth_data = {
				'grade':data[0],
				'name':data[1].title(),
				'surname':data[2].title()}

	if len(data) == 4:
		if data[3] == CONFIG["TUTOR_PASSWORD"]:
			user.role = 'tutor'
			await context.bot.send_message(context._chat_id, text="Вы успешно авторизировались как воспитатель")
		elif data[3] == CONFIG["ROOT_PASSWORD"]:
			user.role = 'root'
			await context.bot.send_message(context._chat_id, text="Вы успешно авторизировались как комсёнок")
	elif not match_auth_data(auth_data):
		await context.bot.send_message(context._chat_id, text=MISC_MESSAGES['wrong_auth_data'])
		return False
	else:
		user.role = "user"

	user.auth_data = auth_data
	await user.print_authorization_data(update, context)

	return True
