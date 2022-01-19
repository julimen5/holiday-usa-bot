import json
import logging
from datetime import date, datetime
from typing import List, Tuple, cast
from telegram import InlineKeyboardButton, InlineKeyboardMarkup, Update, KeyboardButton, ReplyKeyboardMarkup, ParseMode

from telegram.ext import Updater, CommandHandler, MessageHandler, Filters, CallbackContext, PicklePersistence
import os


class InputError(Exception):
    pass


PORT = int(os.environ.get('PORT', 8443))

months = ['January', 'February', 'March', 'April', 'May', 'June', 'July', 'August', 'September', 'October', 'November',
          'December']

with open("holidays.json") as jsonFile:
    jsonObject = json.load(jsonFile)
    jsonFile.close()

# Enable logging
logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
                    level=logging.INFO)

logger = logging.getLogger(__name__)
TOKEN = os.environ['TELEGRAM_TOKEN']
ENV = os.environ['ENV']


# Define a few command handlers. These usually take the two arguments update and
# context. Error handlers also receive the raised TelegramError object in error.
def start(update: Update, context: CallbackContext) -> None:
    """Sends a message with 5 inline buttons attached."""
    kb = [
        [KeyboardButton('/next_holiday')],
        [KeyboardButton('/holidays')],
        [KeyboardButton('/clear')],
        [KeyboardButton('/help')]
    ]
    user = update.message.from_user
    print('You talk with user {} and his user ID: {} '.format(user['username'], user['id']))
    kb_markup = ReplyKeyboardMarkup(kb)
    update.message.reply_text('Hi {user} \n Please choose:'.format(user=user['username']), reply_markup=kb_markup)


def help_command(update: Update, context: CallbackContext) -> None:
    """Displays info on how to use the bot."""
    update.message.reply_text(
        "Use /start to test this bot. Use /clear to clear the stored data so that you can see "
        "what happens, if the button data is not available. "
    )


def clear(update: Update, context: CallbackContext) -> None:
    """Clears the callback data cache"""
    context.bot.callback_data_cache.clear_callback_data()  # type: ignore[attr-defined]
    context.bot.callback_data_cache.clear_callback_queries()  # type: ignore[attr-defined]
    update.effective_message.reply_text('All clear!')


def next_holiday(update, context):
    today = datetime.combine(date.today(), datetime.min.time())
    hdays = jsonObject['holidays']
    filtered_hdays = filter(lambda x: datetime.strptime(x['date'], '%m/%d/%Y') >= today, hdays)
    holiday = min(filtered_hdays, key=lambda x: abs((datetime.strptime(x['date'], '%m/%d/%Y')) - today))
    update.message.reply_text(build_holiday(holiday), parse_mode=ParseMode.HTML)


def validate(month):
    if not month in months:
        raise InputError("Invalid month")


def build_holiday(holiday):
    return "\n <b>{name}</b> - {date} - Day: {day} - Month: {month} \n <strong>==================</strong>" \
        .format(name=holiday['name'], date=holiday['date'], day=holiday['day'], month=holiday['month'])


def holidays(update, context: CallbackContext) -> None:
    hdays = jsonObject['holidays']
    text = ''
    args = None
    if context.args:
        args = context.args[0].capitalize()
        validate(args)
        hdays = [obj for obj in hdays if obj['month'] == args]
    for hday in hdays:
        text += build_holiday(hday)
    if not text:
        text = "No holidays in {month}".format(month=args)
    update.message.reply_text(text, parse_mode=ParseMode.HTML)


def error(update, context):
    """Log Errors caused by Updates."""
    logger.warning('Update "%s" caused error "%s"', update, context.error)
    text = str(context.error) if isinstance(context.error, InputError) else "Something went wrong"
    update.message.reply_text(text)


def build_keyboard(current_list: List[int]) -> InlineKeyboardMarkup:
    """Helper function to build the next inline keyboard."""
    return InlineKeyboardMarkup.from_column(
        [InlineKeyboardButton(str(i), callback_data=(i, current_list)) for i in range(1, 6)]
    )


def main():
    """Start the bot."""
    # Create the Updater and pass it your bot's token.
    # Make sure to set use_context=True to use the new context based callbacks
    # Post version 12 this will no longer be necessary
    persistence = PicklePersistence(
        filename='arbitrarycallbackdatabot.pickle', store_callback_data=True
    )
    updater = Updater(TOKEN, persistence=persistence, arbitrary_callback_data=True)

    # Get the dispatcher to register handlers
    dp = updater.dispatcher

    # on different commands - answer in Telegram
    dp.add_handler(CommandHandler("start", start))
    dp.add_handler(CommandHandler("help", help_command))
    dp.add_handler(CommandHandler("clear", clear))
    dp.add_handler(CommandHandler("next_holiday", next_holiday))
    dp.add_handler(CommandHandler("holidays", holidays))

    # log all errors
    dp.add_error_handler(error)

    # Start the Bot
    if ENV == 'production':
        updater.start_webhook(listen="0.0.0.0",
                              port=int(PORT),
                              url_path=TOKEN,
                              webhook_url='https://dry-sea-48257.herokuapp.com/' + TOKEN)
    else:
        updater.start_polling()

    updater.idle()


if __name__ == '__main__':
    main()
