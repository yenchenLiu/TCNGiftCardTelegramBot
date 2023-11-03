from telegram.ext import ContextTypes
import aiohttp
import sqlite3
from telegram import InlineKeyboardButton, InlineKeyboardMarkup
from telegram import Update
from telegram.ext import ConversationHandler

import keyboard

# Database setup
conn = sqlite3.connect('card_info.db', check_same_thread=False)
cursor = conn.cursor()

# Create table to store card info
cursor.execute('''
CREATE TABLE IF NOT EXISTS cards (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER,
    serial_number TEXT, 
    card_number TEXT, 
    pin TEXT
)
''')
conn.commit()
# Define states for the add card conversation
CARD_NUMBER, CARD_PIN = 0, 1
# Define a state for the remove card conversation
REMOVE_CARD = 0


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("""TCN Gift card query program\n
Enter the card number + pin code to query, and the system will not record your cards.\n
For example 502125102XXXXXXXXXX 1234\n
You can also add the card info to the system and quickly query""", reply_markup=keyboard.main_menu_keyboard())


# Function to check card status
async def check_card_status(card_number: str, pin: str) -> dict:
    url = f"https://tnc-cms.herokuapp.com/thecardnetwork/production/getcard?cardNumber={card_number}&pin={pin}"
    async with aiohttp.ClientSession() as session:
        async with session.get(url) as response:
            if response.status == 200:
                return await response.json()
            else:
                raise ValueError(f'API request failed with status code {response.status}')


# Command handler to remove a card
async def remove_card(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    user_id = update.effective_chat.id
    args = context.args
    if len(args) == 1:
        card_number = args[0]
        cursor.execute('DELETE FROM cards WHERE user_id = ? AND card_number = ?',
                       (user_id, card_number))
        conn.commit()
        await update.message.reply_text("Card removed successfully.")
    else:
        await update.message.reply_text("Please provide the card number.")


async def list_card(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    text = await update.callback_query.message.reply_text("Checking card status...")
    user_id = update.effective_chat.id
    cursor.execute('SELECT user_id, card_number, pin FROM cards WHERE user_id = ?', (user_id,))
    cards = cursor.fetchall()

    for user_id, card_number, pin in cards:
        try:
            card_data = await check_card_status(card_number, pin)

            await update.callback_query.message.reply_text(summarise_card_data(card_data))
        except Exception as e:
            await update.callback_query.message.reply_text(f"Failed to check card status: {e}")
    await text.edit_text("Finished checking card status.")


async def add_card_start(update: Update, context) -> int:
    await update.callback_query.message.reply_text('Please enter the card number:')
    return CARD_NUMBER


async def card_number_received(update: Update, context) -> int:
    user_data = context.user_data
    user_data['card_number'] = update.message.text
    await update.message.reply_text('Please enter the pin:')
    return CARD_PIN


async def card_pin_received(update: Update, context) -> int:
    user_id = update.effective_chat.id
    user_data = context.user_data
    user_data['pin'] = update.message.text
    card_number = user_data['card_number']
    pin = user_data['pin']

    try:
        if len(card_number) != 19 or len(pin) != 4:
            raise ValueError("card_number or pin is wrong")
        card_data = await check_card_status(card_number, pin)
        cursor.execute('INSERT INTO cards (user_id, serial_number, card_number, pin) VALUES (?, ?, ?, ?)',
                       (user_id, card_data['data']['source_serial'], card_number, pin))
        conn.commit()
        await update.message.reply_text("Card added successfully.")
        await update.message.reply_text(summarise_card_data(card_data))
    except ValueError as e:
        await update.message.reply_text(str(e))
    except Exception as e:
        await update.message.reply_text(f"An error occurred: {e}")
    return ConversationHandler.END


async def remove_card_start(update: Update, context) -> int:
    user_id = update.callback_query.from_user.id
    cursor.execute('SELECT serial_number FROM cards WHERE user_id = ?', (user_id,))
    cards = cursor.fetchall()
    select_keyboard = [[InlineKeyboardButton(card[0], callback_data=card[0])] for card in cards]
    if len(select_keyboard) == 0:
        await update.callback_query.message.reply_text('No cards to remove!')
        return ConversationHandler.END
    reply_markup = InlineKeyboardMarkup(select_keyboard)
    await update.callback_query.message.reply_text('Select a card to remove:', reply_markup=reply_markup)
    return REMOVE_CARD


async def card_selected(update: Update, context) -> int:
    selected_card = update.callback_query.data
    if selected_card and len(selected_card) == 19:
        user_id = update.callback_query.from_user.id
        cursor.execute('DELETE FROM cards WHERE user_id = ? AND serial_number = ?', (user_id, selected_card))
        conn.commit()
        await update.callback_query.message.reply_text('Card removed successfully!')
    else:
        await update.callback_query.message.reply_text('Invalid card selected!')
    return ConversationHandler.END


def summarise_card_data(card_data: dict) -> str:
    serial_number = card_data['data']['source_serial']
    card_status = card_data['data']['card_status']
    product_name = card_data['data']['product_name']
    card_current_value = card_data['data']['card_current_value']
    card_value_expiry_date = card_data['data']['card_value_expiry_date']
    register_name = f"{card_data['data']['name']}({card_data['data']['email']})" if card_data['data']['name'] else "N/A"

    return f"""
    Serial Number:{serial_number}\nStatus:{card_status}\nProduct:{product_name}\nValue:{card_current_value}\nExpiry Date:{card_value_expiry_date}\nRegister:{register_name}
    """.strip()
