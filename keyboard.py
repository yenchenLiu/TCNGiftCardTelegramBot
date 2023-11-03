from telegram import InlineKeyboardButton, InlineKeyboardMarkup


def main_menu_keyboard():
    keyboard = [[InlineKeyboardButton('Add Cards', callback_data='add')],
                [InlineKeyboardButton('Remove Cards', callback_data='remove')],
                [InlineKeyboardButton('List Cards', callback_data='list')]]
    return InlineKeyboardMarkup(keyboard)
