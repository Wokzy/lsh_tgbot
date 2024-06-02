
import events

from constants import BUTTON_NAMINGS
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
				waining_for_password (root)
				waining_for_event_name
				waining_for_event_date
				waining_for_event_description (with picture)
		"""

		self.is_root = is_root
		self.current_state = None

		# FIXME
		self.event_creation_data = {}
		self.created_event = None


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
			if user.current_state == 'waining_for_event_name':
				user.event_creation_data['name'] = update.message.text
				user.current_state = 'waining_for_event_date'
				answer_text = "Send event time in format HH:MM d.m (Example 14:00 28.08)"
			elif user.current_state == 'waining_for_event_date':
				date = read_date_from_message(update.message.text)
				if not date:
					answer_text = "Invalid date format, please try again"
				else:
					user.event_creation_data['date'] = date
					user.current_state = 'waining_for_event_description'
					answer_text = 'Write a description for an event and send photo optinally'
			elif user.current_state == 'waining_for_event_description':
				user.event_creation_data['description'] = update.message.text

				#Load picture (TODO)
				user.created_event = events.Event(**user.event_creation_data)
				await user.created_event.print_event(update, context)

				keyboard = [[InlineKeyboardButton(BUTTON_NAMINGS.confirm_event_creation, callback_data='confirm_event_creation')],
							[InlineKeyboardButton(BUTTON_NAMINGS.decline_event_creation, callback_data='decline_event_creation')]]
				keyboard = InlineKeyboardMarkup(keyboard)

				await context.bot.send_message(context._chat_id, text = "Is everything correct?", reply_markup = keyboard)

		if answer_text is not None:
			await context.bot.send_message(update.message.chat.id, text = answer_text)


	async def echo(self, update, context) -> None:

		# print(context._chat_id)
		await context.bot.send_message(context._chat_id, text = "echo")
		# await self.main_menu(update, context)
		await context.bot.answer_callback_query(update.callback_query.id)


	async def main_menu(self, update: Update, context: ContextTypes.DEFAULT_TYPE, force_message = False) -> None:
		self.connected_users[context._user_id].current_state = None

		keyboard = [[InlineKeyboardButton(BUTTON_NAMINGS.echo, callback_data='echo')], 
					[InlineKeyboardButton(BUTTON_NAMINGS.get_events, callback_data = 'get_events')]]

		if self.connected_users[context._user_id].is_root or True: # TDDO
			keyboard.append([InlineKeyboardButton(BUTTON_NAMINGS.create_event, callback_data = 'create_event')])

		keyboard = InlineKeyboardMarkup(keyboard)

		response_text = 'Welcome!'

		if update.callback_query and not force_message:
			await update.callback_query.edit_message_text(text = response_text, reply_markup = keyboard)
			await context.bot.answer_callback_query(update.callback_query.id)
		else:
			await context.bot.send_message(context._chat_id, text = response_text, reply_markup = keyboard)


	async def get_events(self, update, context) -> None:
		keyboard = [[InlineKeyboardButton(BUTTON_NAMINGS.main_menu, callback_data='main_menu')]]
		for key in self.current_events.keys():
			keyboard.append([InlineKeyboardButton(key, callback_data = f'show_events_on_day {key}')])

		keyboard = InlineKeyboardMarkup(keyboard)

		await update.callback_query.edit_message_text(text = 'Please select a day:', reply_markup = keyboard)
		await context.bot.answer_callback_query(update.callback_query.id)


	async def show_events_on_day(self, update, context) -> None:
		keyboard = [[InlineKeyboardButton(BUTTON_NAMINGS.main_menu, callback_data='main_menu')]]

		day = update.callback_query.data.split(' ')[1]
		for key in self.current_events[day]:
			keyboard.append([InlineKeyboardButton(key, callback_data = f'print_event {day} {key}')])

		keyboard = InlineKeyboardMarkup(keyboard)
		await update.callback_query.edit_message_text(text = 'Please select an event for this day:', reply_markup = keyboard)
		await context.bot.answer_callback_query(update.callback_query.id)


	async def print_event(self, update, context) -> None:
		day, time = tuple(update.callback_query.data.split(' ')[1::])
		await self.current_events[day][time].print_event(update, context)

		await context.bot.answer_callback_query(update.callback_query.id)
		await self.main_menu(update, context, force_message = True)


	async def create_event(self, update, context) -> None:
		if self.connected_users[context._user_id].current_state is None:
			keyboard = [[InlineKeyboardButton(BUTTON_NAMINGS.main_menu, callback_data='main_menu')]]
			keyboard = InlineKeyboardMarkup(keyboard)

			self.connected_users[context._user_id].current_state = 'waining_for_event_name'
			await update.callback_query.edit_message_text(text = 'Send a name for an event: ', reply_markup = keyboard)


		await context.bot.answer_callback_query(update.callback_query.id)


	async def confirm_event_creation(self, update, context):

		if context._user_id not in self.connected_users.keys():
			await context.bot.answer_callback_query(update.callback_query.id)
			return

		user = self.connected_users[context._user_id]
		if user.created_event is None:
			await self.main_menu(update, context)
			return

		if user.created_event.string_date() not in self.current_events:
			self.current_events[user.created_event.string_date()] = {}

		self.current_events[user.created_event.string_date()][user.created_event.string_time()] = user.created_event
		events.save_events(self.current_events)

		print(f"Event was created, current_amount: {len(self.current_events)}")

		await context.bot.answer_callback_query(update.callback_query.id, text = f"Event was succesfully created on {user.created_event.string_datetime()}")
		await self.main_menu(update, context)


	async def decline_event_creation(self, update, context):

		if context._user_id not in self.connected_users.keys():
			await context.bot.answer_callback_query(update.callback_query.id)
			return

		user = self.connected_users[context._user_id]

		user.created_event = None
		user.event_creation_data = {}

		await context.bot.answer_callback_query(update.callback_query.id, text = f"You've canceled event creation")
		await self.main_menu(update, context)


def main():
	print(f'{clr.green}Starting bot...')
	config = read_config()
	bot = Bot()

	application = Application.builder().token(config['BOT_TOKEN']).build()
	application.add_handler(CommandHandler("start", bot.start_session))
	application.add_handler(MessageHandler(filters.TEXT, bot.handle_message))

	application.add_handler(CallbackQueryHandler(bot.echo, pattern='echo'))
	application.add_handler(CallbackQueryHandler(bot.main_menu, pattern='main_menu'))
	application.add_handler(CallbackQueryHandler(bot.create_event, pattern='create_event'))
	application.add_handler(CallbackQueryHandler(bot.get_events, pattern='get_events'))
	application.add_handler(CallbackQueryHandler(bot.print_event, pattern='print_event'))
	application.add_handler(CallbackQueryHandler(bot.show_events_on_day, pattern='show_events_on_day'))
	application.add_handler(CallbackQueryHandler(bot.confirm_event_creation, pattern='confirm_event_creation'))
	application.add_handler(CallbackQueryHandler(bot.decline_event_creation, pattern='decline_event_creation'))

	print(f'{clr.cyan}Bot is online')

	application.run_polling()


if __name__ == '__main__':
	main()
