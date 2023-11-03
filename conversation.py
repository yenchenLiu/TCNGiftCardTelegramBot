from telegram.ext import ConversationHandler, CallbackQueryHandler, MessageHandler, filters

import handler

# Define states for the add card conversation
CARD_NUMBER, CARD_PIN = 0, 1
# Define a state for the remove card conversation
REMOVE_CARD = 0

# Add card conversation handler
add_card_conv_handler = ConversationHandler(
    entry_points=[CallbackQueryHandler(handler.add_card_start, pattern='add')],
    states={
        CARD_NUMBER: [MessageHandler(filters.TEXT & ~filters.COMMAND, handler.card_number_received)],
        CARD_PIN: [MessageHandler(filters.TEXT & ~filters.COMMAND, handler.card_pin_received)],
    },
    fallbacks=[],
)

# Remove card conversation handler
remove_card_conv_handler = ConversationHandler(
    entry_points=[CallbackQueryHandler(handler.remove_card_start, pattern='remove')],
    states={
        REMOVE_CARD: [CallbackQueryHandler(handler.card_selected)],
    },
    fallbacks=[],
)
