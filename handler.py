from telegram.ext import ContextTypes
import aiohttp
from telegram import InlineKeyboardButton, InlineKeyboardMarkup
from telegram import Update
from telegram.ext import ConversationHandler
from sqlmodel import Session, select

import keyboard
from db import Card, engine

# Define states for the add card conversation
CARD_NUMBER, CARD_PIN = 0, 1
# Define a state for the remove card conversation
REMOVE_CARD = 0


async def start(update: Update, _context: ContextTypes.DEFAULT_TYPE):
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


async def list_card(update: Update, _context: ContextTypes.DEFAULT_TYPE) -> None:
    text = await update.callback_query.message.reply_text("Checking card status...")
    user_id = str(update.effective_chat.id)
    stmt = select(Card).where(Card.user_id == user_id)
    with Session(engine) as session:
        cards = session.exec(stmt)
        for card in cards:
            try:
                card_data = await check_card_status(card.card_number, card.pin)
                await update.callback_query.message.reply_text(summarise_card_data(card_data))
            except Exception as e:
                await update.callback_query.message.reply_text(f"Failed to check card status: {e}")
    await text.edit_text("Finished checking card status.")


async def add_card_start(update: Update, _context: ContextTypes.DEFAULT_TYPE) -> int:
    await update.callback_query.message.reply_text('Please enter the card number:')
    return CARD_NUMBER


async def card_number_received(update: Update, context) -> int:
    user_data = context.user_data
    user_data['card_number'] = update.message.text
    await update.message.reply_text('Please enter the pin:')
    return CARD_PIN


async def card_pin_received(update: Update, context) -> int:
    user_id = str(update.effective_chat.id)
    user_data = context.user_data
    user_data['pin'] = update.message.text
    card_number = user_data['card_number']
    pin = user_data['pin']

    try:
        if len(card_number) != 19 or len(pin) != 4:
            raise ValueError("card_number or pin is wrong")
        card_data = await check_card_status(card_number, pin)
        card = Card(user_id=user_id, serial_number=card_data['data']['source_serial'], card_number=card_number, pin=pin)
        with Session(engine) as session:
            session.add(card)
            session.commit()
        await update.message.reply_text("Card added successfully.")
        await update.message.reply_text(summarise_card_data(card_data))
    except ValueError as e:
        await update.message.reply_text(str(e))
    except Exception as e:
        await update.message.reply_text(f"An error occurred: {e}")
    return ConversationHandler.END


async def remove_card_start(update: Update, _context: ContextTypes.DEFAULT_TYPE) -> int:
    user_id = str(update.effective_chat.id)
    stmt = select(Card).where(Card.user_id == user_id)
    with Session(engine) as session:
        cards = session.exec(stmt)
        select_keyboard = [[InlineKeyboardButton(card.serial_number, callback_data=card.serial_number)] for card in cards]
        if len(select_keyboard) == 0:
            await update.callback_query.message.reply_text('No cards to remove!')
            return ConversationHandler.END
        reply_markup = InlineKeyboardMarkup(select_keyboard)
        await update.callback_query.message.reply_text('Select a card to remove:', reply_markup=reply_markup)
        return REMOVE_CARD


async def card_selected(update: Update, _context: ContextTypes.DEFAULT_TYPE) -> int:
    selected_card = update.callback_query.data
    if selected_card and len(selected_card) == 7:
        user_id = str(update.callback_query.from_user.id)
        stmt = select(Card).where(Card.user_id == user_id).where(Card.serial_number == selected_card)
        with Session(engine) as session:
            card = session.exec(stmt).first()
            if not card:
                await update.callback_query.message.reply_text('Invalid card selected!')
                return ConversationHandler.END
            session.delete(card)
            session.commit()
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
