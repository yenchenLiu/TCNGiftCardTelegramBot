from telegram import Update
from telegram.ext import ApplicationBuilder, CommandHandler, ContextTypes, CallbackQueryHandler, MessageHandler
from telegram.ext.filters import MessageFilter
import handler
import conversation
from config import get_settings


class AnonymousQueryFilter(MessageFilter):
    def filter(self, message):
        data = message.text.split(' ')
        if len(data) != 2:
            return False
        card_number, pin = data
        if len(card_number) != 19 or len(pin) != 4:
            return False
        return True


async def menu_actions(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    query = update.callback_query.data
    if query == 'list':
        await handler.list_card(update, context)


async def anonymous_query(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    card_data = await handler.check_card_status(*update.message.text.split(' '))
    await update.message.reply_text(handler.summarise_card_data(card_data))


if __name__ == '__main__':
    application = ApplicationBuilder().token(get_settings().telegram_token).build()

    # Add command handlers
    application.add_handler(CommandHandler('start', handler.start))
    application.add_handler(conversation.add_card_conv_handler)
    application.add_handler(conversation.remove_card_conv_handler)
    # Start the bot
    application.add_handler(CallbackQueryHandler(menu_actions))

    application.add_handler(MessageHandler(AnonymousQueryFilter(), anonymous_query))
    application.run_polling()
