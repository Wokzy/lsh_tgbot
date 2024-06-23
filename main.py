
import events
import bot_functions

from constants import BUTTON_NAMINGS, MISC_MESSAGES
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
	def __init__(self, is_root:bool = False):
		"""
		states:
				waiting_for_password (root)
				waiting_for_event_name
				waiting_for_event_date
				waiting_for_event_description (with picture)
		"""

		self.is_root = is_root
		self.current_state = None

		# FIXME
		#self.event_creation_data = {}
		self.modified_event = None
		self.modified_event_old_position = None


class Bot:
	def __init__(self):
		"""
			self.connected_users = {user_id: {'is_root':bool, 'current_state':str}}
			
		"""
		self.connected_users = {}

		self.current_events = events.load_events()


	async def start_session(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
		user = update.message.from_user

		if user.id not in self.connected_users:
			print(f'{clr.yellow}{user.first_name} {user.last_name} {user.username} [{user.id}] Has just launched the bot')
			self.connected_users[context._user_id] = BotUser()

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

		if self.connected_users[context._user_id].is_root or True: # TDDO
			keyboard.append([InlineKeyboardButton(BUTTON_NAMINGS.create_event, callback_data = 'event_modification new_event')])

		keyboard = InlineKeyboardMarkup(keyboard)

		response_text = 'Welcome!'

		if update.callback_query and not force_message and update.callback_query.data == 'main_menu':
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
					 InlineKeyboardButton(BUTTON_NAMINGS.modify_event,
					 					callback_data=f'event_modification change_existing_event {day} {time}'),
					 #InlineKeyboardButton(BUTTON_NAMINGS.remove_event, callback_data=f'remove_event {day} {time}'),
					]]

		keyboard = InlineKeyboardMarkup(keyboard)

		await self.current_events[day][time].print_event(update, context, reply_markup = keyboard)

		await context.bot.answer_callback_query(update.callback_query.id)
		#await self.main_menu(update, context, force_message = True)


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

		user = self.connected_users[context._user_id]

		user.modified_event = None

		await context.bot.answer_callback_query(update.callback_query.id, text = f"Вы отменили редактирование мероприятия")
		await self.main_menu(update, context, force_message = True)


def main():
	print(f'{clr.green}Starting bot...')
	config = read_config()
	bot = Bot()

	application = Application.builder().token(config['BOT_TOKEN']).build()
	application.add_handler(CommandHandler("start", bot.start_session))
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


	print(f'{clr.cyan}Bot is online')

	application.run_polling()


if __name__ == '__main__':
	main()
