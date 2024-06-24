
import events
import datetime
import bot_functions

from constants import BUTTON_NAMINGS, MISC_MESSAGES, DAILY_NEWSLETTER_TIME
from utils import clr, read_config, read_date_from_message

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
	#PollAnswerHandler,
	#PollHandler,
	filters,
)


__author__ = 'Yegor Yershov'


class BotUser:
	def __init__(self, role:str = "user"):
		"""
		roles: user, tutor, root
		"""

		self.role = role
		self.current_state = None
		self.authorization = None

		# FIXME
		#self.event_creation_data = {}
		self.modified_event = None
		self.modified_event_old_position = None


		self.notifications_flag = False # Notificaitons toggle
		self.notifications = [] # Events list to be notified about


	async def print_authorization_data(self, update, context) -> None:
		return


	async def authorize(self, update, context) -> None:
		self.current_state = None

		data = update.message.text.split(' ')
		if len(data) < 3:
			context.bot.send_message(context._chat_id, text="Некорректный формат")
			return

		config = read_config()

		auth_data = {
					'grade':data[0],
					'surname':data[1],
					'name':data[2]}

		if len(data) == 4:
			password = data[3]
			if password == config["ROOT_PASSWORD"]:
				self.role = 'root'
				await context.bot.send_message(context._chat_id, text="Вы успешно авторизировались как комсёнок")
			elif password == config["TUTOR_PASSWORD"]:
				self.role = 'tutor'
				await context.bot.send_message(context._chat_id, text="Вы успешно авторизировались как воспитатель")
		else:
			if not bot_functions.match_auth_data(auth_data):
				await context.bot.send_message(context._chat_id, text=MISC_MESSAGES['wrong_auth_data'])
				return

		self.authorization = auth_data


	async def setup_daily_newsletter(self, update, context, job_queue):
		self.notifications_flag = True
		job_queue.run_daily(self.daily_newsletter,
							DAILY_NEWSLETTER_TIME,
							chat_id=context._chat_id,
							user_id=context._user_id,
							name="Daily Newsletter")

	async def daily_newsletter(self, context):
		pass


class Bot:
	def __init__(self):
		"""
			pass
		"""
		self.connected_users = bot_functions.load_users()

		self.current_events = events.load_events()


	async def start_session(self, update: Update, context: ContextTypes.DEFAULT_TYPE, job_queue) -> None:
		user = update.message.from_user

		if user.id not in self.connected_users:
			print(f'{clr.yellow}{user.first_name} {user.last_name} {user.username} [{user.id}] Has just launched the bot')
			self.connected_users[context._user_id] = BotUser()

			self.connected_users[context._user_id].setup_daily_newsletter()



		await self.main_menu(update, context)

		# await context.bot.send_message(update.message.chat.id, "You've already started me")


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

		if answer_text is not None:
			await context.bot.send_message(update.message.chat.id, text = answer_text)


	async def echo(self, update, context) -> None:

		# print(context._chat_id)
		await context.bot.send_message(context._chat_id, text = "echo")
		# await self.main_menu(update, context)
		await context.bot.answer_callback_query(update.callback_query.id)


	async def main_menu(self, update: Update, context: ContextTypes.DEFAULT_TYPE, force_message = False) -> None:
		self.connected_users[context._user_id].current_state = None
		self.connected_users[context._user_id].modified_event = None

		keyboard = [[InlineKeyboardButton(BUTTON_NAMINGS.echo, callback_data='echo')], 
					[InlineKeyboardButton(BUTTON_NAMINGS.get_events, callback_data = 'get_events')]]

		if self.connected_users[context._user_id].role == 'root': # TDDO
			keyboard.append([InlineKeyboardButton(BUTTON_NAMINGS.create_event, callback_data = 'event_modification new_event')])
		if self.connected_users[context._user_id].authorization is None:
			keyboard.append([InlineKeyboardButton(BUTTON_NAMINGS.user_authorization,
							callback_data='_change_user_state authorization user_authorization')])

		keyboard = InlineKeyboardMarkup(keyboard)

		response_text = 'Welcome!'

		if update.callback_query and not force_message:# and update.callback_query.data == 'main_menu':
			await update.callback_query.edit_message_text(text = response_text, reply_markup = keyboard)
		else:
			await context.bot.send_message(context._chat_id, text = response_text, reply_markup = keyboard)

		if update.callback_query is not None:
			await context.bot.answer_callback_query(update.callback_query.id)


	async def get_events(self, update, context) -> None:
		keyboard = [[InlineKeyboardButton(BUTTON_NAMINGS.main_menu, callback_data='main_menu')]]
		for key in sorted(self.current_events.keys()):
			keyboard.append([InlineKeyboardButton(key, callback_data = f'show_events_on_day {key}')])

		keyboard = InlineKeyboardMarkup(keyboard)

		await update.callback_query.edit_message_text(text = 'Выберите день:', reply_markup = keyboard)
		await context.bot.answer_callback_query(update.callback_query.id)


	async def show_events_on_day(self, update, context) -> None:
		keyboard = [[InlineKeyboardButton(BUTTON_NAMINGS.main_menu, callback_data='main_menu')]]

		day = update.callback_query.data.split(' ')[1]
		for key in sorted(self.current_events[day]):
			keyboard.append([InlineKeyboardButton(key, callback_data = f'print_event {day} {key}')])

		keyboard = InlineKeyboardMarkup(keyboard)
		await update.callback_query.edit_message_text(text = 'Выберите время:', reply_markup = keyboard)
		await context.bot.answer_callback_query(update.callback_query.id)


	async def print_event(self, update, context) -> None:
		day, time = tuple(update.callback_query.data.split(' ')[1::])

		keyboard = [[InlineKeyboardButton(BUTTON_NAMINGS.main_menu, callback_data='main_menu force_message'),
					]]

		if self.connected_users[context._user_id].role == 'root':
			keyboard.append([InlineKeyboardButton(BUTTON_NAMINGS.modify_event,
					 				callback_data=f'event_modification change_existing_event {day} {time}'),
							InlineKeyboardButton(BUTTON_NAMINGS.remove_event, 
									callback_data=f'remove_event {day} {time} enquire'),
							])

		keyboard = InlineKeyboardMarkup(keyboard)

		await self.current_events[day][time].print_event(update, context, reply_markup = keyboard)

		await context.bot.answer_callback_query(update.callback_query.id)
		#await self.main_menu(update, context, force_message = True)


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


	async def save_modified_event(self, update, context):

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


	async def decline_modified_event(self, update, context):

		if context._user_id not in self.connected_users.keys():
			await context.bot.answer_callback_query(update.callback_query.id)
			return

		self.connected_users[context._user_id].modified_event = None

		await context.bot.answer_callback_query(update.callback_query.id, text = f"Вы отменили редактирование мероприятия")
		await self.main_menu(update, context, force_message = True)


	async def user_settings(self, update, context):

		user = self.connected_users[context._user_id]
		status = update.callback_query.data.split(' ')[1]

		keyboard = [[InlineKeyboardButton(BUTTON_NAMINGS.main_menu, callback_data='main_menu')],
					[InlineKeyboardButton(BUTTON_NAMINGS.user_authorization,
							callback_data='_change_user_state authorization user_authorization')],
					 [InlineKeyboardButton(BUTTON_NAMINGS.technical_support, callback_data='user_settings technical_support')],
		]

		keyboard = InlineKeyboardMarkup(keyboard)

		if status == technical_support:
			await context.bot.send_message(context._chat_id, text=MISC_MESSAGES['technical_support'])

		if user.authorization is not None:
			await user.print_authorization_data(update, context, reply_markup=keyboard)
		else:
			await context.bot.send_message(context._chat_id, text="Выберите нужный пункт для настройки", reply_markup=keyboard)

		await context.bot.answer_callback_query(update.callback_query.id)


def main():
	print(f'{clr.green}Starting bot...')
	config = read_config()
	bot = Bot()

	application = Application.builder().token(config['BOT_TOKEN']).build()
	application.add_handler(CommandHandler("start", bot.start_session, pass_job_queue=True))
	application.add_handler(MessageHandler(filters.ALL, bot.handle_message))

	application.add_handler(CallbackQueryHandler(bot.echo, pattern='echo'))
	application.add_handler(CallbackQueryHandler(bot.main_menu, pattern='main_menu'))
	application.add_handler(CallbackQueryHandler(bot.get_events, pattern='get_events'))
	application.add_handler(CallbackQueryHandler(bot.print_event, pattern='print_event'))
	application.add_handler(CallbackQueryHandler(bot.show_events_on_day, pattern='show_events_on_day'))
	application.add_handler(CallbackQueryHandler(bot.save_modified_event, pattern='save_modified_event'))
	application.add_handler(CallbackQueryHandler(bot.decline_modified_event, pattern='decline_modified_event'))
	application.add_handler(CallbackQueryHandler(bot.event_modification, pattern='event_modification'))
	application.add_handler(CallbackQueryHandler(bot._change_user_state, pattern='_change_user_state'))
	application.add_handler(CallbackQueryHandler(bot.remove_event, pattern='remove_event'))
	application.add_handler(CallbackQueryHandler(bot.user_settings, pattern='user_settings'))


	print(f'{clr.cyan}Bot is online')

	application.run_polling()
	bot_functions.save_users(bot.connected_users)


if __name__ == '__main__':
	main()
