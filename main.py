

from utils import clr, read_config

from telegram import (
	# KeyboardButton,
	# KeyboardButtonPollType,
	# Poll,
	# ReplyKeyboardMarkup,
	# ReplyKeyboardRemove,
	Update,
	User
)

from telegram.ext import (
	Application,
	CommandHandler,
	ContextTypes,
	MessageHandler,
	#PollAnswerHandler,
	#PollHandler,
	filters,
)


__author__ = 'Yegor Yershov'

global running_users
running_users = []

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
	global running_users
	user = update.message.from_user

	if user not in running_users:
		running_users.append(user)
		await context.bot.send_message(update.message.chat.id, "started")
	else:
		await context.bot.send_message(update.message.chat.id, "already started")

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
	await context.bot.send_message(update.message.chat.id, update.message.text)


def main():
	print(f'{clr.green}Starting bot...')
	config = read_config()

	application = Application.builder().token(config['BOT_TOKEN']).build()
	application.add_handler(CommandHandler("start", start))
	application.add_handler(MessageHandler(filters.TEXT, handle_message))
	#application.add_handler(PollAnswerHandler(receive_poll_answer))

	print(f'{clr.cyan}Bot is online')

	application.run_polling()

if __name__ == '__main__':
	main()
