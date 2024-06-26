
import events
import datetime
import bot_functions

from constants import (
	BUTTON_NAMINGS,
	MISC_MESSAGES,
	DAILY_NEWSLETTER_TIME,
	ROLE_MAPPING
)

from utils import (
	clr,
	read_config,
	save_photo,
	load_photo,
	read_date_from_message
)

from telegram import (
	KeyboardButton,
	# KeyboardButtonPollType,
	# Poll,
	ReplyKeyboardMarkup,
	InlineKeyboardButton,
	InlineKeyboardMarkup,
	# ReplyKeyboardRemove,
	Update
)

from telegram.ext import (
	Application,
	CommandHandler,
	ContextTypes,
	MessageHandler,
	CallbackQueryHandler,
	JobQueue,
	#PollAnswerHandler,
	#PollHandler,
	filters,
)


__author__ = 'Yegor Yershov'

CONFIG = read_config()


class BotUser:
	def __init__(self, role:str = "user", user_id = None, chat_id = None):
		"""
		roles: user, tutor, root
		"""

		self.user_id = user_id
		self.chat_id = chat_id

		self.role = role
		self.current_state = None
		self.authorization = None

		# FIXME
		#self.event_creation_data = {}
		self.modified_event = None
		self.modified_event_old_position = None


		self.notifications_flag = False # Notificaitons toggle


	async def print_authorization_data(self, update, context) -> None:

		if self.authorization is not None:
			text = 'Информация о вас:\n\n' + \
				  f'Роль: {ROLE_MAPPING[self.role]}\n' + \
				  f'Класс: {self.authorization["grade"]}\n' + \
				  f'Имя Фамилия: {self.authorization["name"]} {self.authorization["surname"]}'

		await context.bot.send_message(context._chat_id, text=text)


	async def authorize(self, update, context) -> None:
		self.current_state = None

		data = update.message.text.split(' ')

		if CONFIG["ROOT_PASSWORD"] in data or context._user_id in CONFIG['ROOT_USERS']:
			self.role = 'root'
			await context.bot.send_message(context._chat_id, text="Вы успешно авторизировались как комсёнок")
			return

		if len(data) < 3:
			await context.bot.send_message(context._chat_id, text="Некорректный формат")
			return

		auth_data = {
					'grade':data[0],
					'surname':data[1],
					'name':data[2]}

		if len(data) == 4:
			if data[3] == CONFIG["TUTOR_PASSWORD"]:
				self.role = 'tutor'
				await context.bot.send_message(context._chat_id, text="Вы успешно авторизировались как воспитатель")
		elif not bot_functions.match_auth_data(auth_data):
			await context.bot.send_message(context._chat_id, text=MISC_MESSAGES['wrong_auth_data'])
			return

		self.authorization = auth_data
		await self.print_authorization_data(update, context)


	def setup_daily_newsletter(self, context, daily_newsletter):
		self.notifications_flag = True
		context.job_queue.run_daily(daily_newsletter,
							DAILY_NEWSLETTER_TIME,
							chat_id=self.chat_id,
							user_id=self.user_id,
							name="Daily Newsletter")

		print(context.job_queue.jobs())


class Bot:
	def __init__(self):
		"""
			Load user's and event's info
		"""

		self.static_data = bot_functions.load_static_data()
		self.connected_users = self.static_data.get('connected_users', {})
		self.current_events = events.load_events()


	def save_all_data(self) -> None:
		self.static_data['connected_users'] = self.connected_users

		events.save_events(self.current_events)
		bot_functions.save_static_data(self.static_data)
		print(f'{clr.green}saved{clr.yellow}')


	async def async_save(self, update, context):
		if self.connected_users[context._user_id].role != 'root':
			return
		self.save_all_data()


	async def refresh(self, update, context) -> None:
		""" root command to refresh all data (usually used after reboot) """
		if context._user_id not in CONFIG['ROOT_USERS']:
			return

		print(f'{clr.yellow}', end='')
		for user_id, user in self.connected_users.items():
			if user.notifications_flag:
				user.setup_daily_newsletter(context, self.daily_newsletter)

		print(f'{clr.yellow}Refreshed')


	async def start_session(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
		user = update.message.from_user

		if user.id not in self.connected_users:
			print(f'{clr.yellow}{user.first_name} {user.last_name} {user.username} [{user.id}] Has just launched the bot')
			self.connected_users[context._user_id] = BotUser(user_id=context._user_id, chat_id=context._chat_id)

			self.connected_users[context._user_id].setup_daily_newsletter(context, self.daily_newsletter)



		await self.main_menu(update, context)

		# await context.bot.send_message(update.message.chat.id, "You've already started me")


	async def daily_newsletter(self, context, reply_markup=None) -> None:
		""" Newsletter """

		message = self.static_data.get('newsletter', {'text':'No newsletter', 'photo':None})

		if message['photo'] is None:
			await context.bot.send_message(context._chat_id,
										   text=message['text'],
										   parse_mode="Markdown",
										   reply_markup=reply_markup)
		else:
			message['photo'] = await load_photo(context, message['photo'])
			await context.bot.send_photo(context._chat_id,
										 caption=message['text'],
										 photo=message['photo'],
										 parse_mode="Markdown",
										 reply_markup=reply_markup)


	async def handle_message(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
		answer_text = None

		if update.message.from_user.id not in self.connected_users.keys():
			answer_text = "Enter /start to start bot"
		else:
			user = self.connected_users[context._user_id]
			if user.modified_event is not None:
				await self.event_modification(update, context)
			if user.current_state == 'authorization':
				await user.authorize(update, context)
				await self.main_menu(update, context, force_message = True)
				return
			elif user.current_state == 'edit_newsletter':
				await self.edit_newsletter(update, context)
			elif user.current_state == 'edit_canteen_menu':
				await self.canteen_menu(update, context)

		if answer_text is not None:
			await context.bot.send_message(update.message.chat.id, text = answer_text)


	async def echo(self, update, context) -> None:

		# print(context._chat_id)
		await context.bot.send_message(context._chat_id, text = "echo")
		# await self.main_menu(update, context)
		await context.bot.answer_callback_query(update.callback_query.id)
		print(context.job_queue.jobs())


	async def main_menu(self, update: Update, context: ContextTypes.DEFAULT_TYPE, force_message = False) -> None:
		self.connected_users[context._user_id].current_state = None
		self.connected_users[context._user_id].modified_event = None

		keyboard = [[InlineKeyboardButton(BUTTON_NAMINGS.echo, callback_data='echo')], 
					[InlineKeyboardButton(BUTTON_NAMINGS.get_events, callback_data = 'get_events')],
					[InlineKeyboardButton(BUTTON_NAMINGS.canteen_menu, callback_data = 'canteen_menu')],
					[InlineKeyboardButton(BUTTON_NAMINGS.user_settings, callback_data = 'user_settings default')]]

		if self.connected_users[context._user_id].role == 'root': # TDDO
			keyboard.append([InlineKeyboardButton(BUTTON_NAMINGS.create_event, callback_data = 'event_modification new_event')])
			keyboard.append([InlineKeyboardButton(BUTTON_NAMINGS.edit_newsletter, callback_data = 'edit_newsletter default')])
		if self.connected_users[context._user_id].authorization is None and self.connected_users[context._user_id].role != 'root':
			keyboard.append([InlineKeyboardButton(BUTTON_NAMINGS.user_authorization,
							callback_data='_change_user_state authorization user_authorization')])

		keyboard = InlineKeyboardMarkup(keyboard)

		response_text = 'Welcome!'

		if update.callback_query is not None:
			force_message = force_message or 'force_message' in update.callback_query.data

		if update.callback_query and not force_message:# and update.callback_query.data == 'main_menu':
			await update.callback_query.edit_message_text(text = response_text, reply_markup = keyboard)
		else:
			await context.bot.send_message(context._chat_id, text = response_text, reply_markup = keyboard)

		if update.callback_query is not None:
			await context.bot.answer_callback_query(update.callback_query.id)


	async def get_events(self, update, context) -> None:

		callback_data = update.callback_query.data.split(' ')[1::]

		keyboard = [[InlineKeyboardButton(BUTTON_NAMINGS.main_menu, callback_data='main_menu')]]

		answer_text = None

		if len(callback_data) == 0:
			answer_text = 'Выберите день:'
			for key in sorted(self.current_events.keys()):
				keyboard.append([InlineKeyboardButton(key, callback_data = f'get_events {key}')])
		elif len(callback_data) == 1:
			answer_text = 'Выберите время:'
			day = callback_data[0]
			for key in sorted(self.current_events[day]):
				keyboard.append([InlineKeyboardButton(key, callback_data = f'get_events {day} {key}')])
		else:
			day, time = callback_data
			keyboard = [[InlineKeyboardButton(BUTTON_NAMINGS.main_menu, callback_data='main_menu force_message')]]
			if self.connected_users[context._user_id].role == 'root':
				keyboard.append([InlineKeyboardButton(BUTTON_NAMINGS.modify_event,
						 				callback_data=f'event_modification change_existing_event {day} {time}'),
								InlineKeyboardButton(BUTTON_NAMINGS.remove_event, 
										callback_data=f'remove_event {day} {time} enquire'),
								])

		keyboard = InlineKeyboardMarkup(keyboard)

		if answer_text is not None:
			await update.callback_query.edit_message_text(text = answer_text, reply_markup = keyboard)
		else:
			await self.current_events[day][time].print_event(update, context, reply_markup = keyboard)

		await context.bot.answer_callback_query(update.callback_query.id)


	async def remove_event(self, update, context) -> None:
		day, time, status = update.callback_query.data.split(' ')[1::]

		if status == 'enquire':
			keyboard = [[InlineKeyboardButton(BUTTON_NAMINGS.confirm_removal, 
											callback_data=f'remove_event {day} {time} confirm'),
						 InlineKeyboardButton(BUTTON_NAMINGS.decline_removal,
											callback_data=f'remove_event {day} {time} decline'),
					]]

			keyboard = InlineKeyboardMarkup(keyboard)
			await context.bot.send_message(context._chat_id,
											text = MISC_MESSAGES['removal_approvement'],
											reply_markup = keyboard)
			await context.bot.answer_callback_query(update.callback_query.id)
		elif status == 'confirm':
			del self.current_events[day][time]
			events.save_events(self.current_events)
			await context.bot.answer_callback_query(update.callback_query.id, text = "Мероприятие было удалено")
			await self.main_menu(update, context)
		elif status == 'decline':
			await context.bot.answer_callback_query(update.callback_query.id, text = "Вы отменили удаление мероприятия")
			await self.main_menu(update, context)


	async def _change_user_state(self, update, context) -> None:
		# FIXME
		callback_query = update.callback_query.data.split(' ')[1::]
		self.connected_users[context._user_id].current_state = callback_query[0]
		if len(callback_query) > 1:
			await context.bot.send_message(context._chat_id, text = MISC_MESSAGES[callback_query[1]])
		await context.bot.answer_callback_query(update.callback_query.id)


	async def event_modification(self, update, context) -> None:
		if context._user_id not in self.connected_users.keys():
			await context.bot.answer_callback_query(update.callback_query.id)
			return

		state = await bot_functions.handle_event_modification_callback_query(self, update, context)

		keyboard = [
					[InlineKeyboardButton(BUTTON_NAMINGS.decline_modified_event,
											callback_data='decline_modified_event')],
					[InlineKeyboardButton(BUTTON_NAMINGS.change_event_date,
											callback_data='_change_user_state event_date event_dating')],
					[InlineKeyboardButton(BUTTON_NAMINGS.change_event_name,
											callback_data='_change_user_state event_name event_naming')],
					[InlineKeyboardButton(BUTTON_NAMINGS.change_event_description,
											callback_data='_change_user_state event_description event_descriptioning')],
					[InlineKeyboardButton(BUTTON_NAMINGS.change_event_picture,
											callback_data='_change_user_state event_picture event_picturing')],
					[InlineKeyboardButton(BUTTON_NAMINGS.save_modified_event,
											callback_data='save_modified_event')],
					]
		keyboard = InlineKeyboardMarkup(keyboard)

		#self.connected_users[context._user_id].current_state = 'waiting_for_event_name'

		if state == 'new_event':
			await update.callback_query.edit_message_text(text = "Приступайте к созданию мероприятия: ", reply_markup = keyboard)
		else:
			await self.connected_users[context._user_id].modified_event.print_event(update, context, reply_markup = keyboard)

		if update.callback_query is not None:
			await context.bot.answer_callback_query(update.callback_query.id)


	async def save_modified_event(self, update, context) -> None:

		if context._user_id not in self.connected_users.keys():
			await context.bot.answer_callback_query(update.callback_query.id)
			return

		user = self.connected_users[context._user_id]
		if user.modified_event is None:
			await self.main_menu(update, context, force_message = True)
			return

		if user.modified_event.string_date() not in self.current_events:
			self.current_events[user.modified_event.string_date()] = {}

		if user.modified_event_old_position is not None:
			del self.current_events[user.modified_event_old_position[0]][user.modified_event_old_position[1]]

		self.current_events[user.modified_event.string_date()][user.modified_event.string_time()] = user.modified_event
		events.save_events(self.current_events)

		print(f"Event was saved by {context._user_id}")

		await context.bot.answer_callback_query(update.callback_query.id, text = f"Мероприятие было успешно сохранено на {user.modified_event.string_datetime()}")
		await self.main_menu(update, context, force_message = True)


	async def decline_modified_event(self, update, context) -> None:

		if context._user_id not in self.connected_users.keys():
			await context.bot.answer_callback_query(update.callback_query.id)
			return

		self.connected_users[context._user_id].modified_event = None

		await context.bot.answer_callback_query(update.callback_query.id, text = f"Вы отменили редактирование мероприятия")
		await self.main_menu(update, context, force_message = True)


	async def user_settings(self, update, context) -> None:

		user = self.connected_users[context._user_id]
		status = update.callback_query.data.split(' ')[1]

		keyboard = [[InlineKeyboardButton(BUTTON_NAMINGS.main_menu, callback_data='main_menu')],
					[InlineKeyboardButton(BUTTON_NAMINGS.user_authorization,
							callback_data='_change_user_state authorization user_authorization')],
					 [InlineKeyboardButton(BUTTON_NAMINGS.technical_support, callback_data='user_settings technical_support')],
		]

		keyboard = InlineKeyboardMarkup(keyboard)

		if status == "technical_support":
			await context.bot.send_message(context._chat_id, text=MISC_MESSAGES['technical_support'])

		if user.authorization is not None:
			await user.print_authorization_data(update, context, reply_markup=keyboard)
		else:
			await context.bot.send_message(context._chat_id, text="Выберите нужный пункт для настройки", reply_markup=keyboard)

		await context.bot.answer_callback_query(update.callback_query.id)


	async def edit_newsletter(self, update, context) -> None:


		keyboard = [[InlineKeyboardButton(BUTTON_NAMINGS.main_menu, callback_data='main_menu')]]
		keyboard = InlineKeyboardMarkup(keyboard)

		if update.callback_query is not None:
			self.connected_users[context._user_id].current_state = "edit_newsletter"
			await self.daily_newsletter(context, reply_markup=keyboard)
			await context.bot.send_message(context._chat_id, text=MISC_MESSAGES['edit_newsletter'])
			await context.bot.answer_callback_query(update.callback_query.id)
		else:
			self.connected_users[context._user_id].current_state = None
			if update.message.photo:
				self.static_data['newsletter'] = {"text":update.message.caption,
							  "photo":await save_photo(context, update.message.photo[-1])}
			else:
				self.static_data['newsletter'] = {'text':update.message.text, 'photo':None}

			await context.bot.send_message(context._chat_id, text=MISC_MESSAGES['newsletter_changed'], reply_markup=keyboard)


	async def canteen_menu(self, update, context) -> None:
		""" Print out canteen menu (supposed to be only text) """

		menu = self.static_data.get('canteen_menu', "Menu:")

		keyboard = [[InlineKeyboardButton(BUTTON_NAMINGS.main_menu, callback_data='main_menu')]]
		keyboard = InlineKeyboardMarkup(keyboard)

		if update.callback_query is None:
			self.connected_users[context._user_id].current_state = None

			if update.message.text is not None:
				self.static_data['canteen_menu'] = update.message.text
				await context.bot.send_message(context._chat_id,
											   text=MISC_MESSAGES['canteen_menu_chaged'],
											   reply_markup=keyboard)

			return



		if self.connected_users[context._user_id].role == 'root':
			await context.bot.send_message(context._chat_id, text=menu)
			self.connected_users[context._user_id].current_state = "edit_canteen_menu"
			await context.bot.send_message(context._chat_id,
										   text=MISC_MESSAGES['edit_canteen_menu'],
										   reply_markup=keyboard)
		else:
			await context.bot.send_message(context._chat_id, text=menu, reply_markup=keyboard)

		await context.bot.answer_callback_query(update.callback_query.id)




def main():
	print(f'{clr.green}Starting bot...')
	config = read_config()
	bot = Bot()

	application = Application.builder().token(config['BOT_TOKEN']).read_timeout(7).get_updates_read_timeout(42).build()
	application.add_handler(CommandHandler("start", bot.start_session))
	application.add_handler(CommandHandler("refresh", bot.refresh))
	application.add_handler(CommandHandler("save_all", bot.async_save))
	application.add_handler(MessageHandler(filters.ALL, bot.handle_message))

	application.add_handler(CallbackQueryHandler(bot.echo, pattern='echo'))
	application.add_handler(CallbackQueryHandler(bot.main_menu, pattern='main_menu'))
	application.add_handler(CallbackQueryHandler(bot.get_events, pattern='get_events'))
	application.add_handler(CallbackQueryHandler(bot.save_modified_event, pattern='save_modified_event'))
	application.add_handler(CallbackQueryHandler(bot.decline_modified_event, pattern='decline_modified_event'))
	application.add_handler(CallbackQueryHandler(bot.event_modification, pattern='event_modification'))
	application.add_handler(CallbackQueryHandler(bot.remove_event, pattern='remove_event'))
	application.add_handler(CallbackQueryHandler(bot.user_settings, pattern='user_settings'))
	application.add_handler(CallbackQueryHandler(bot.edit_newsletter, pattern='edit_newsletter'))
	application.add_handler(CallbackQueryHandler(bot.canteen_menu, pattern='canteen_menu'))

	application.add_handler(CallbackQueryHandler(bot._change_user_state, pattern='_change_user_state'))


	print(f'{clr.cyan}Bot is online')

	application.run_polling()
	bot.save_all_data()


if __name__ == '__main__':
	main()
