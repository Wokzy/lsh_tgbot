
import utils
import events

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
				user.modified_event.picture_file_id = await events.save_event_picture(bot = context.bot, 
																					 picture = update.message.photo[-1])
	elif state == 'new_event':
		user.modified_event = events.Event()

	if answer_text is not None:
		await context.bot.send_message(context._chat_id, text = answer_text)

	return state

