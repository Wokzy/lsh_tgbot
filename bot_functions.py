
import os
import utils
import events
import pickle

from utils import read_config


CONFIG = read_config()


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
		if not update.message.text.isalnum():
			answer_text = "Некорректное название мероприятия"
		else:
			user.modified_event.name = update.message.text # This state is expected to be called from message_handler
	elif state == 'event_date':
		event_datetime = utils.read_date_from_message(update.message.text)
		if not event_datetime:
			answer_text = 'Некорретный формат времени'
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
				'surname':data[1],
				'name':data[2]}

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

	user.auth_data = auth_data
	await user.print_authorization_data(update, context)

	return True
