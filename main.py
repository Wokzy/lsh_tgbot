
import sys
import events
import datetime
import bot_functions

from telegram import (
	# KeyboardButton,
	# KeyboardButtonPollType,
	# Poll,
	# ReplyKeyboardMarkup,
	InlineKeyboardButton,
	InlineKeyboardMarkup,
	# ReplyKeyboardRemove,
	Update,
)

from telegram.ext import (
	Application,
	CommandHandler,
	ContextTypes,
	MessageHandler,
	CallbackQueryHandler,
	JobQueue,
	# PollAnswerHandler,
	# PollHandler,
	filters,
)

from constants import (
	FAQ,
	DEBUG_MODE,
	ROLE_MAPPING,
	MISC_MESSAGES,
	BUTTON_NAMINGS,
	KOMSA_CALL_COOLDOWN,
	DAILY_NEWSLETTER_TIME,
	KOMSA_CALL_REQUEST_EXPIRATION_TIME,
)

from utils import (
	clr,
	save_photo,
	load_photo,
	save_events,
	load_events,
	read_config,
	load_komsa_list,
	save_komsa_list,
	load_static_data,
	save_static_data,
	print_komsa_description,
)




__author__ = 'Yegor Yershov'

CONFIG = read_config()


class BotUser:
	def __init__(self, role:str = "user", user_id = None, chat_id = None, auth_data = {}, notifications_flag=False, notify_events=set()):
		"""
		roles: user, tutor, root
		"""

		self.user_id = user_id
		self.chat_id = chat_id

		self.role = role
		self.current_state = None
		self.auth_data = auth_data

		# FIXME
		#self.event_creation_data = {}
		self.modified_event = None
		self.modified_event_old_position = None


		self.notifications_flag = notifications_flag # Notificaitons toggle
		self.notify_events = notify_events


	async def print_authorization_data(self, update, context, reply_markup=None) -> None:

		text = "Информация о вас пока что отстутствует"

		if self.auth_data:
			text = 'Информация о вас:\n\n' + \
				  f'Роль: {ROLE_MAPPING[self.role]}\n' + \
				  f'Класс: {self.auth_data.get("grade", "Unknown")}\n' + \
				  f'Имя Фамилия: {self.auth_data.get("name", "NoName")} {self.auth_data.get("surname", "NoSurname")}'

		await context.bot.send_message(context._chat_id, text=text, reply_markup=reply_markup)


	def setup_daily_newsletter(self, context, daily_newsletter):
		self.notifications_flag = True

		job_name = f"newsletter_{self.chat_id}_{self.user_id}"

		if len(context.job_queue.get_jobs_by_name(job_name)) > 0:
			return

		context.job_queue.run_daily(daily_newsletter,
							DAILY_NEWSLETTER_TIME,
							chat_id=self.chat_id,
							user_id=self.user_id,
							name=job_name)


	def setup_event_notifications(self, context, event_modification):
		context.job_queue.run_repeating(
			callback=event_modification,
			interval=60*15, # 15 minutes
			name=f"{self.user_id}",
			chat_id=self.chat_id,
			user_id=self.user_id,
			first=1
			)


	async def notify(self, context, event) -> None:
		print(f'{clr.green}Notification mock {self.user_id}{clr.yellow}')
		await event.print_event(update=None, context=context)



class Bot:
	def __init__(self):
		"""
			Load user's and event's info

			self.komsa = {'user_id':{'description', 'photo'}}
			self.call_komsa_cooldown = {'user_id':cooldown_finish_datetime (datetime.datetime)}
			self.pending_call_requests = {'request_id':bot_functions.CallKomsaRequest}
		"""

		self.static_data = load_static_data(objects_map={'connected_users':BotUser,
											"pending_call_requests":bot_functions.CallKomsaRequest()})
		self.connected_users = self.static_data.get('connected_users', {})
		self.current_events, self.event_mapping = load_events(event_object=events.Event())

		self.komsa = load_komsa_list()
		self.call_komsa_cooldown = self.static_data.get('call_komsa_cooldown', {}) if "--no-call-requests" not in sys.argv else {}
		self.pending_call_requests = self.static_data.get('pending_call_requests', {}) if "--no-call-requests" not in sys.argv else {}

		self.__refreshed = False


	def save_all_data(self) -> None:
		self.static_data['connected_users'] = self.connected_users
		self.static_data['call_komsa_cooldown'] = self.call_komsa_cooldown
		self.static_data['pending_call_requests'] = self.pending_call_requests

		save_events(self.event_mapping)
		save_static_data(self.static_data)
		save_komsa_list(self.komsa)
		print(f'{clr.green}saved{clr.yellow}')


	async def async_save(self, update, context):
		if self.connected_users[context._user_id].role != 'root':
			return
		self.save_all_data()


	async def refresh(self, update, context) -> None:
		""" root command to refresh all data (usually used after reboot) """
		if self.__refreshed or context._user_id not in CONFIG['ROOT_USERS']:
			return

		print(f'{clr.yellow}', end='')
		for user_id, user in self.connected_users.items():
			if user.notifications_flag:
				user.setup_daily_newsletter(context, self.daily_newsletter)
				user.setup_event_notifications(context, self.event_notification)

		self.__refreshed = True
		print(context.job_queue.jobs())
		print(f'{clr.yellow}Refreshed')


	async def user_count(self, update, context):
		if context._user_id not in self.connected_users:
			return

		user = self.connected_users[context._user_id]
		if user.role != 'root':
			return

		res = f'Total amount of unique users: {len(self.connected_users.keys())}'

		await context.bot.send_message(context._chat_id, text=res)


	async def start_session(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
		if update.message is None:
			return

		user = update.message.from_user

		if user.id not in self.connected_users:
			print(f'{clr.yellow}{user.first_name} {user.last_name} {user.username} [{user.id}] Has just launched the bot')
			self.connected_users[context._user_id] = BotUser(user_id=context._user_id, chat_id=context._chat_id)

			self.connected_users[context._user_id].setup_daily_newsletter(context, self.daily_newsletter)
			self.connected_users[context._user_id].setup_event_notifications(context, self.event_notification)

		await self.main_menu(update, context)

		# await context.bot.send_message(update.message.chat.id, "You've already started me")


	async def daily_newsletter(self, context, reply_markup=None) -> None:
		""" Newsletter """

		message = self.static_data.get('newsletter', {'text':'No newsletter', 'photo':None})

		if reply_markup is None:
			reply_markup = InlineKeyboardMarkup([[InlineKeyboardButton(BUTTON_NAMINGS.canteen_menu, callback_data = 'canteen_menu')]])


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


	async def authorize(self, update, context) -> bool:
		user = self.connected_users[context._user_id]
		status = await bot_functions.authorize_user(user, update, context)


	async def handle_message(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
		answer_text = None

		if update.message.from_user.id not in self.connected_users.keys():
			answer_text = "Enter /start to start bot"
		else:
			user = self.connected_users[context._user_id]
			if user.modified_event is not None:
				await self.event_modification(update, context)
			if user.current_state == 'authorization':
				await self.authorize(update, context)
				await self.main_menu(update, context, force_message = True)
				return
			if user.current_state == 'edit_newsletter':
				await self.edit_newsletter(update, context)
			elif user.current_state == 'edit_canteen_menu':
				await self.canteen_menu(update, context)
			elif user.current_state == 'update_komsa_description':
				await self.update_komsa_description(update, context)
			elif user.current_state is not None and 'call_komsa_description' in user.current_state:
				await self.user_confirm_komsa_call(update, context)

		if answer_text is not None:
			await context.bot.send_message(update.message.chat.id, text = answer_text)


	async def echo(self, update, context) -> None:

		# print(context._chat_id)
		await context.bot.send_message(context._chat_id, text = "echo")
		# await self.main_menu(update, context)
		await context.bot.answer_callback_query(update.callback_query.id)
		#print(context.job_queue.jobs())
		print(self.connected_users[context._user_id].notify_events)


	async def main_menu(self, update: Update, context: ContextTypes.DEFAULT_TYPE, force_message = False) -> None:
		self.connected_users[context._user_id].current_state = None
		self.connected_users[context._user_id].modified_event = None

		keyboard = [[InlineKeyboardButton(BUTTON_NAMINGS.echo, callback_data='echo')], 
					[InlineKeyboardButton(BUTTON_NAMINGS.get_events, callback_data='get_events')],
					[InlineKeyboardButton(BUTTON_NAMINGS.canteen_menu, callback_data='canteen_menu')],
					[InlineKeyboardButton(BUTTON_NAMINGS.user_settings, callback_data='user_settings default')],
					[InlineKeyboardButton(BUTTON_NAMINGS.faq, callback_data='faq default')],
					[InlineKeyboardButton(BUTTON_NAMINGS.komsa_list, callback_data='call_komsa default')]]

		if self.connected_users[context._user_id].role == 'root': # TDDO
			keyboard.append([InlineKeyboardButton(BUTTON_NAMINGS.create_event, callback_data = 'event_modification new_event')])
			keyboard.append([InlineKeyboardButton(BUTTON_NAMINGS.edit_newsletter, callback_data = 'edit_newsletter default')])
			keyboard.append([InlineKeyboardButton(BUTTON_NAMINGS.update_komsa_description, callback_data = 'update_komsa_description')])
		if not self.connected_users[context._user_id].auth_data and self.connected_users[context._user_id].role != 'root':
			keyboard.append([InlineKeyboardButton(BUTTON_NAMINGS.user_authorization,
							callback_data='_change_user_state authorization user_authorization')])

		keyboard = InlineKeyboardMarkup(keyboard)

		response_text = 'Welcome!'

		if update.callback_query is not None:
			force_message = force_message or 'force_message' in update.callback_query.data

		if update.callback_query and not force_message and update.callback_query.message.text is not None:
			await update.callback_query.edit_message_text(text = response_text, reply_markup = keyboard)
		else:
			await context.bot.send_message(context._chat_id, text = response_text, reply_markup = keyboard)

		if update.callback_query is not None:
			await context.bot.answer_callback_query(update.callback_query.id)


	async def get_events(self, update, context) -> None:

		user = self.connected_users[context._user_id]
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
				if not self.current_events[day][key].hidden or user.role == 'root':
					keyboard.append([InlineKeyboardButton(key, callback_data = f'get_events {day} {key}')])
		elif len(callback_data) == 2:
			day, time = callback_data
			event = self.current_events[day][time]
			keyboard = events.get_event_keyboard(user, event)
		else:
			state, day, time = callback_data
			event = self.current_events[day][time]
			if state == 'hide':
				event.hidden = True
				await context.bot.answer_callback_query(update.callback_query.id, text=MISC_MESSAGES['hide_event'])
			elif state == 'reveal':
				event.hidden = False
				await context.bot.answer_callback_query(update.callback_query.id, text=MISC_MESSAGES['reveal_event'])

			keyboard = events.get_event_keyboard(user, event)
			keyboard = InlineKeyboardMarkup(keyboard)

			await context.bot.edit_message_reply_markup(chat_id=context._chat_id,
														message_id=update.callback_query.message.id,
														reply_markup=keyboard)
			return

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
			save_events(self.event_mapping)
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
		self.event_mapping[user.modified_event.event_id] = user.modified_event
		save_events(self.event_mapping)

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

		if user.auth_data:
			await user.print_authorization_data(update, context, reply_markup=keyboard)
		else:
			await context.bot.send_message(context._chat_id, text="Выберите нужный пункт для настройки", reply_markup=keyboard)

		await context.bot.answer_callback_query(update.callback_query.id)


	async def edit_newsletter(self, update, context) -> None:


		keyboard = [[InlineKeyboardButton(BUTTON_NAMINGS.main_menu, callback_data='main_menu force_message')]]
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


	async def setup_notification(self, update, context, user=None, event=None) -> None:

		if event is None:
			state, day, time = update.callback_query.data.split(' ')[1::]
			user = self.connected_users[context._user_id]
			event = self.current_events[day][time]
		else:
			state = 'enable'

		if state == 'enable' and event.event_id not in user.notify_events:
			user.notify_events.add(event.event_id)
			await context.bot.answer_callback_query(update.callback_query.id, text='Напоминание установлено')
		elif state == 'disable' and event.event_id in user.notify_events:
			user.notify_events.remove(event.event_id)
			await context.bot.answer_callback_query(update.callback_query.id, text='Напоминание отключено')

		keyboard = events.get_event_keyboard(user, event)
		keyboard = InlineKeyboardMarkup(keyboard)
		await context.bot.edit_message_reply_markup(chat_id=context._chat_id,
													message_id=update.callback_query.message.id,
													reply_markup=keyboard)


	async def event_notification(self, context):
		""" Check all notifications and notify """

		user = self.connected_users[context._user_id]
		for event_id in list(user.notify_events):
			event = self.event_mapping[event_id]
			if DEBUG_MODE or (event.datetime - datetime.datetime.now()).total_seconds() < 3600:
				await user.notify(context, event)
				user.notify_events.remove(event_id)


	async def update_komsa_description(self, update, context):

		user = self.connected_users[context._user_id]

		keyboard = [[InlineKeyboardButton(BUTTON_NAMINGS.main_menu, callback_data='main_menu')]]
		keyboard = InlineKeyboardMarkup(keyboard)

		if update.callback_query is not None:
			user.current_state = 'update_komsa_description'

			if user.user_id in self.komsa.keys():
				await print_komsa_description(context, self.komsa[user.user_id], user)

			await context.bot.send_message(context._chat_id, text=MISC_MESSAGES['update_komsa_description'], reply_markup=keyboard)
			await context.bot.answer_callback_query(update.callback_query.id)
			return

		description = {'text':None, 'photo':None}

		if not update.message.photo:
			description['description'] = update.message.text
		else:
			description['description'] = update.message.caption
			description['photo'] = await save_photo(context, update.message.photo[-1])

		self.komsa[user.user_id] = description

		save_komsa_list(self.komsa)
		await context.bot.send_message(context._chat_id, text=MISC_MESSAGES['update_komsa_description_success'], reply_markup=keyboard)


	async def faq(self, update, context):

		state = update.callback_query.data.split(' ')[1]

		if state == 'default':
			keyboard = [[InlineKeyboardButton(FAQ[i][0], callback_data=f"faq {i}")] for i in range(len(FAQ))]
			keyboard.insert(0, [InlineKeyboardButton(BUTTON_NAMINGS.main_menu, callback_data='main_menu')])
			response_text = MISC_MESSAGES['faq']
		else:
			keyboard = [[InlineKeyboardButton(BUTTON_NAMINGS.faq_other_questions, callback_data='faq default')],
						[InlineKeyboardButton(BUTTON_NAMINGS.main_menu, callback_data='main_menu')]]
			response_text = FAQ[int(state)][1]

		keyboard = InlineKeyboardMarkup(keyboard)
		await context.bot.answer_callback_query(update.callback_query.id)
		await update.callback_query.edit_message_text(text=response_text, reply_markup=keyboard)


	async def order_song_for_disco(self, update, context):
		pass
		# await context.bot.send_message("Отправьте название трека и его исполнителя (по желанию можно прикрепить ссылку)")


	async def user_confirm_komsa_call(self, update, context):

		user = self.connected_users[context._user_id]

		if update.callback_query is None:
			description = update.message.text
			komsa_id = int(user.current_state.split(' ')[1])
			request = bot_functions.CallKomsaRequest(sender_id=context._user_id,
													 reciever_id=komsa_id,
													 description=description)
			self.pending_call_requests[request.request_id] = request

			keyboard = [[InlineKeyboardButton(BUTTON_NAMINGS.confirm_call, callback_data=f'user_confirm_komsa_call do_call {request.request_id}'),
						 InlineKeyboardButton(BUTTON_NAMINGS.decline_call, callback_data=f'main_menu')],
						[InlineKeyboardButton(BUTTON_NAMINGS.edit_komsa_call_description,
											  callback_data=f'user_confirm_komsa_call default {komsa_id}'),]]

			keyboard = InlineKeyboardMarkup(keyboard)

			await context.bot.send_message(context._chat_id,
										   text=MISC_MESSAGES['confirm_call'],
										   reply_markup=keyboard)

			return

		callback_query = update.callback_query.data.split(' ')[1::]
		state = callback_query[0]


		await context.bot.answer_callback_query(update.callback_query.id)

		if state == 'default':
			komsa_id = callback_query[1]

			keyboard = [[InlineKeyboardButton(BUTTON_NAMINGS.return_to_main_menu, callback_data=f'main_menu')]]
			keyboard = InlineKeyboardMarkup(keyboard)

			user.current_state = f"call_komsa_description {komsa_id}"

			await context.bot.send_message(context._chat_id,
										   text=MISC_MESSAGES['call_komsa_description'],
										   reply_markup=keyboard)


		if state == 'do_call':

			request = self.pending_call_requests[int(callback_query[1])]
			request.confirmed_by_user = True

			self.call_komsa_cooldown[context._user_id] = datetime.datetime.now() + KOMSA_CALL_COOLDOWN
			await bot_functions.send_confirm_call_message_to_tutor(self.connected_users, request=request, context=context)
			await update.callback_query.edit_message_text(text="Запрос отправлен")


	async def call_komsa(self, update, context):

		# ======================= FIXME =========================

		_delete = []
		for key, request in self.pending_call_requests.items():
			try:
				if (datetime.datetime.now() - request.creation_date) > KOMSA_CALL_REQUEST_EXPIRATION_TIME:
					_delete.append(key)
			except AttributeError:
				_delete.append(key)

		for item in _delete:
			del self.pending_call_requests[item]

		# =======================================================

		user = self.connected_users[context._user_id]

		if len(self.komsa) == 0:
			await context.bot.answer_callback_query(update.callback_query.id, text="add komsa list")
			return


		await context.bot.answer_callback_query(update.callback_query.id)

		callback_data = update.callback_query.data.split(' ')[1::]
		state = callback_data[0]

		if state == 'default':
			state = 'show'
			callback_data.append(list(self.komsa.keys())[0])

		if state == 'show':
			if context._user_id not in self.call_komsa_cooldown.keys():
				self.call_komsa_cooldown[context._user_id] = datetime.datetime.now() - datetime.timedelta(days=1)

			komsa_id = int(callback_data[1])
			prev_komsa_id = list(self.komsa.keys())[(list(self.komsa.keys()).index(komsa_id) - 1) % len(self.komsa.keys())]
			next_komsa_id = list(self.komsa.keys())[(list(self.komsa.keys()).index(komsa_id) + 1) % len(self.komsa.keys())]

			keyboard = [[InlineKeyboardButton(BUTTON_NAMINGS.main_menu, callback_data='main_menu')],
						[InlineKeyboardButton("<", callback_data=f'call_komsa show {prev_komsa_id}'),
						 InlineKeyboardButton(">", callback_data=f'call_komsa show {next_komsa_id}')]]

			if user.role == 'user' and CONFIG['ALLOW_INVITATIONS']:
				if not bot_functions.check_call_request_sender(self.pending_call_requests, sender_id=context._user_id):
					if datetime.datetime.now() >= self.call_komsa_cooldown[context._user_id]:
						keyboard.append([InlineKeyboardButton(BUTTON_NAMINGS.call_komsa,
															  callback_data=f'user_confirm_komsa_call default {komsa_id}')])

			await print_komsa_description(context,
										  self.komsa[komsa_id],
										  user=self.connected_users[komsa_id],
										  reply_markup=InlineKeyboardMarkup(keyboard))


	async def confirm_call_from_tutor(self, update, context):
		state, request_id = update.callback_query.data.split(' ')[1::]
		request_id = int(request_id)

		await context.bot.answer_callback_query(update.callback_query.id)

		if state == 'confirm':
			await update.callback_query.edit_message_text(text="Вы разрешили")
			await bot_functions.send_confirm_call_message_to_root(
									users=self.connected_users,
									request=self.pending_call_requests[request_id],
									context=context)
		else:
			sender = self.connected_users[self.pending_call_requests[request_id].sender_id]
			tutor = self.connected_users[context._user_id]
			text = f"Воспитатель {tutor.auth_data['name']} {tutor.auth_data['surname']} запретил вам вызвать комсёнка"

			await update.callback_query.edit_message_text(text="Вы запретили")
			await context.bot.send_message(sender.chat_id, text=text)

			del self.pending_call_requests[request_id]



	async def confirm_call_from_root(self, update, context):
		state, request_id = update.callback_query.data.split(' ')[1::]
		request_id = int(request_id)

		request = self.pending_call_requests[request_id]
		sender = self.connected_users[request.sender_id]
		root = self.connected_users[request.reciever_id]

		if state == 'confirm':
			await update.callback_query.edit_message_text(text="Не забудте прийти")

			text = f"Комсёнок {root.auth_data['name']} {root.auth_data['surname']} к вам придёт, ждите"
			await context.bot.send_message(sender.chat_id, text=text)
		else:
			await update.callback_query.edit_message_text(text="Вы отказались прийти")

			text = f"К сожалению комсёнок {root.auth_data['name']} {root.auth_data['surname']} к вам не сможет прийти"
			await context.bot.send_message(sender.chat_id, text=text)

		del self.pending_call_requests[request_id]
		await context.bot.answer_callback_query(update.callback_query.id)







def main():
	print(f'{clr.green}Starting bot...')
	config = read_config()
	bot = Bot()

	application = Application.builder().token(config['BOT_TOKEN']).read_timeout(7).get_updates_read_timeout(42).build()

	application.add_handler(CommandHandler("start", bot.start_session))
	application.add_handler(CommandHandler("refresh", bot.refresh))
	application.add_handler(CommandHandler("save_all", bot.async_save))
	application.add_handler(CommandHandler("user_count", bot.user_count))

	application.add_handler(MessageHandler(filters.PHOTO, bot.handle_message))
	application.add_handler(MessageHandler(filters.TEXT, bot.handle_message))

	callback_handlers = {
			bot.echo                     : 'echo',
			bot.main_menu                : 'main_menu',
			bot.get_events               : 'get_events',
			bot.save_modified_event      : 'save_modified_event',
			bot.decline_modified_event   : 'decline_modified_event',
			bot.event_modification       : 'event_modification',
			bot.remove_event             : 'remove_event',
			bot.user_settings            : 'user_settings',
			bot.edit_newsletter          : 'edit_newsletter',
			bot.canteen_menu             : 'canteen_menu',
			bot.setup_notification       : 'setup_notification',
			bot.update_komsa_description : 'update_komsa_description',
			bot.faq                      : 'faq',
			bot.call_komsa               : 'call_komsa',
			bot.confirm_call_from_tutor  : "confirm_call_from_tutor",
			bot.confirm_call_from_root   : "confirm_call_from_root",
			bot.user_confirm_komsa_call  : "user_confirm_komsa_call",
	}

	for function, pattern in callback_handlers.items():
		application.add_handler(CallbackQueryHandler(function, pattern=pattern))

	application.add_handler(CallbackQueryHandler(bot._change_user_state, pattern='_change_user_state'))


	print(f'{clr.cyan}Bot is online')

	application.run_polling()
	bot.save_all_data()


if __name__ == '__main__':
	if '--help' in sys.argv:
		print('--debug\n--no-call-requests')
		raise SystemExit
	main()
