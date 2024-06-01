
import events

from utils import clr, read_config
from constants import BUTTON_NAMINGS, ROOT_USERS

from telegram import (
	KeyboardButton,
	# KeyboardButtonPollType,
	# Poll,
	ReplyKeyboardMarkup,
	InlineKeyboardButton,
	InlineKeyboardMarkup,
	# ReplyKeyboardRemove,
	Update,
	User
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



# class Session:
# 	def __init__(self, chat_id:int, is_root:bool = False):
# 		"""
# 			IsRoot flag is used to determine users with root privileges

# 			States:
# 				none
# 				main_menu
# 		"""

# 		self.chat_id = chat_id
# 		self.state = 'none'

# 		self.is_root = True # Development state
# 		self.event_creation_state = 0

# 		self.notifications = {} # dict with events to be notified about (TODO)


# 	async def main_menu(self, update, context) -> None:
# 		""" Main bot menu """

# 		self.state = 'main_menu'

# 		keyboard = [[KeyboardButton(BUTTON_NAMINGS.echo), KeyboardButton(BUTTON_NAMINGS.get_events)]]
# 		if self.is_root:
# 			keyboard[0][0].append(KeyboardButton(BUTTON_NAMINGS.create_event))

# 		keyboard = ReplyKeyboardMarkup(keyboard, one_time_keyboard=True)

# 		await context.bot.send_message(update.message.chat.id, text = 'Welcome!', reply_markup = keyboard)


# 	async def handle_message(self, update, context) -> None:
# 		match self.state:
# 			case 'main_menu':
# 				await self.main_menu_handler(update, context)
# 			case 'event_creation':
# 				if self.event_creation_state == 0:
# 					name, picture_fname = events.read_event_data_from_user(update, context)
# 					events.create_event(CURRENT_EVENTS, name = 'name', date = 'test', info = 'description', picture = picture_fname)
# 					self.event_creation_state = -1
# 					self.state = 'main_menu'


# 	async def main_menu_handler(self, update, context) -> None:
# 		if update.message.text == BUTTON_NAMINGS.create_event and self.is_root:
# 			self.state = 'event_creation'
# 			await context.bot.send_message(update.message.chat.id, text = "Please send picture and description for an event: ")
# 		elif update.message.text == BUTTON_NAMINGS.echo:
# 			await context.bot.send_message(update.message.chat.id, text = update.message.text)
# 		elif update.message.text == BUTTON_NAMINGS.get_events:
# 			self.state = 'event_printing'
# 		else:
# 			await context.bot.send_message(update.message.chat.id, text = "Unrecognized request")


class Bot:
	def __init__(self):
		"""
			#### self.sessions = {user_id:session_class}
		"""
		self.cached_users = []

		self.current_events = events.load_events()


	async def start_session(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
		user = update.message.from_user

		if user not in self.cached_users:
			print(f'{clr.yellow}{user.first_name} {user.last_name} {user.username} [{user.id}] Has just launched the bot')
			self.cached_users.append(user)

		await self.main_menu(update, context)

		# await context.bot.send_message(update.message.chat.id, "You've already started me")


	async def handle_message(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
		if update.message.from_user not in self.cached_users:
			await context.bot.send_message(update.message.chat.id, "Enter /start to start bot")
		else:
			# await self.sessions[update.message.from_user].handle_message(update, context)
			await context.bot.send_message(update.message.chat.id, update.message.text)


	async def echo(self, update, context) -> None:

		# print(context._chat_id)
		await context.bot.send_message(context._chat_id, text = "echo")
		# await self.main_menu(update, context)
		await context.bot.answer_callback_query(update.callback_query.id)


	async def main_menu(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
		keyboard = [[InlineKeyboardButton(BUTTON_NAMINGS.echo, callback_data='echo')], 
					[InlineKeyboardButton(BUTTON_NAMINGS.get_events, callback_data = 'get_events')]]

		if context._user_id in ROOT_USERS or True: # TDDO
			keyboard.append([InlineKeyboardButton(BUTTON_NAMINGS.create_event, callback_data = 'create_event')])

		keyboard = InlineKeyboardMarkup(keyboard)

		response_text = 'Welcome!'

		if update.callback_query:
			await update.callback_query.edit_message_text(text = response_text, reply_markup = keyboard)
			await context.bot.answer_callback_query(update.callback_query.id)
		else:
			await context.bot.send_message(context._chat_id, text = response_text, reply_markup = keyboard)

	async def get_events(self, update, context) -> None:
		keyboard = []
		for i in range(1, 27):
			# TODO CALLBACKS
			keyboard.append([InlineKeyboardButton(f'{i}.08', callback_data = 'echo')])

		keyboard = InlineKeyboardMarkup(keyboard)

		await context.bot.send_message(context._chat_id, text = 'Please select a day:', reply_markup = keyboard)
		await context.bot.answer_callback_query(update.callback_query.id)


	async def create_event(self, update, context) -> None:
		await context.bot.send_message(context._chat_id, text = 'This function is not ready yet(')
		await context.bot.answer_callback_query(update.callback_query.id)


def main():
	print(f'{clr.green}Starting bot...')
	config = read_config()
	bot = Bot()

	application = Application.builder().token(config['BOT_TOKEN']).build()
	application.add_handler(CommandHandler("start", bot.start_session))
	application.add_handler(MessageHandler(filters.TEXT, bot.handle_message))

	application.add_handler(CallbackQueryHandler(bot.main_menu, pattern='main_menu'))
	application.add_handler(CallbackQueryHandler(bot.create_event, pattern='create_event'))
	application.add_handler(CallbackQueryHandler(bot.get_events, pattern='get_events'))
	application.add_handler(CallbackQueryHandler(bot.echo, pattern='echo'))
	#application.add_handler(PollAnswerHandler(receive_poll_answer))

	print(f'{clr.cyan}Bot is online')

	application.run_polling()


if __name__ == '__main__':
	main()
