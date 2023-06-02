import logging
import os
import psycopg2 as pg
import re
import requests
import json
import threading, time
import numpy as np
from aiogram import Bot, Dispatcher, executor, types
from aiogram.contrib.fsm_storage.memory import MemoryStorage
from aiogram.dispatcher.filters.state import State, StatesGroup
from aiogram.dispatcher import FSMContext
from aiogram.types import ReplyKeyboardRemove, \
    ReplyKeyboardMarkup, KeyboardButton, \
    BotCommand, BotCommandScopeDefault, BotCommandScopeChat

# Create a new bot by instantiating the Bot class.
bot_token = ('6121301545:AAEFl8I_lmMPldudcCuhGtJk9vT_F90sIm4')
bot = Bot(token=bot_token)
dp = Dispatcher(bot, storage=MemoryStorage())

conn = pg.connect(
    host="localhost",
    database="rgz_rpp",
    user="postgres",
    password="1234"
)
cursor = conn.cursor()

api_key = "98X0NBIA93MCV2KS"
url = f"https://alphavantage.co/query?function=TIME_SERIES_DAILY_ADJUSTED&symbol=IBM&apikey={api_key}"
response = requests.get(url)
data = json.loads(response.text)
print(data)

def get_daily_closing_prices(symbol):
    try:
        conn = pg.connect(
            host="localhost",
            database="rgz_rpp",
            user="postgres",
            password="1234"
        )
        cursor = conn.cursor()
        url = f"https://www.alphavantage.co/query?function=TIME_SERIES_DAILY_ADJUSTED&symbol={symbol}&apikey={'98X0NBIA93MCV2KS'}"
        response = requests.get(url)
        data = response.json()
        time_series = data["Time Series (Daily)"]
        closing_prices = [float(entry["4. close"]) for entry in time_series.values()]  #
        print(closing_prices[0]) 
        median_price = np.median(closing_prices)
        if symbol in list:
            cursor.execute("UPDATE data_bumaga SET mediaan_price = %s WHERE name = %s",
                           (median_price, symbol))
        else:
            cursor.execute(
                "INSERT INTO data_bumaga(name, mediaan_price) VALUES (%(name)s,, %(mediaan_price)s)",
                {
                    "name": symbol,
                    "mediaan_price": median_price
                }
            )
        return median_price

    except KeyError:
        return None


start = KeyboardButton(text='старт')
Add = KeyboardButton(text='Добавить')
save = KeyboardButton(text='посмотреть')

commands = [
    types.BotCommand(command='/start', description='Начало'),
    types.BotCommand(command='/Add', description='Добавить ценную бумагу к портфелю'),
    types.BotCommand(command='/save', description='Показатели отслеживаемых ценных бумаг'),
    types.BotCommand(command='/median', description='Удалить ценную бумагу из портфеля')
]


async def setup_bot_commands(arg):
    await bot.set_my_commands(commands, scope=BotCommandScopeDefault())
class ManageStateGroup(StatesGroup):
    Add_currency_name_state = State()
    save_currency_name_state= State()
    Add_currency_rate_state = State()
    Edit_currency_name_state = State()
    Edit_currency_rate_state = State()
    Delete_currency_state = State()
    median_currency_name_state = State()


class Step2(StatesGroup):
    currency_name2 = State()
    amount = State()

saved_state_global = {}

@dp.message_handler(commands=['start'])
async def add_chat_id(message: types.Message):
    await message.reply("Добро пожаловать в бота")

@dp.message_handler(commands=['Add'])
async def add_currency_command(message: types.Message):
    await ManageStateGroup.Add_currency_name_state.set()
    await message.reply("Введите имя ценной бумаги")

@dp.message_handler(state=ManageStateGroup.Add_currency_name_state)
async def process_currency(message: types.Message, state: FSMContext):
    await state.update_data(currency_name=message.text)
    user_data = await state.get_data()
    print(user_data)
    await ManageStateGroup.Add_currency_rate_state.set()
    try:
        add_currency_in_database(user_data['currency_name'])
        await message.reply("Ценная бумага сохранена ")
    except Exception as e:
        logging.error("Ошибка записи в БД", e)
        error_message = e.args[0] if len(e.args) > 0 else "Причина неизвестна"
        await message.reply(f"ценную бумагу не удалось сохранить: {error_message}")
    finally:
        await state.finish()


def add_currency_in_database(currency_name: str):
    conn = pg.connect(
        host="localhost",
        database="rgz_rpp",
        user="postgres",
        password="1234"
    )
    cursor = conn.cursor()
    # Запрашиваем все имеющиеся валюты, по параметру currency_name
    print(currency_name)
    cursor.execute("SELECT 1 FROM bumaga WHERE name = %(currency_name)s", {"currency_name": currency_name})
    found_currencies = cursor.fetchall()

    # Если найдена хотя бы одна валюта, currency_name которой совпадает с тем, что мы пытаемся сохранить, тогда
    # кидаем исключение с текстом "Валюта уже существует"
    if len(found_currencies) > 0:
        raise Exception("Валюта уже существует")

    cursor.execute(
        "INSERT INTO bumaga(name) VALUES (%(name)s)",
        {
            "name": currency_name
        })
    conn.commit()
    conn.close()

@dp.message_handler(commands=['median'])
async def add_currency_command(message: types.Message):
    await ManageStateGroup.median_currency_name_state.set()
    await message.reply("Введите имя ценной бумаги")

@dp.message_handler(state=ManageStateGroup.median_currency_name_state)
async def save_currency(message: types.Message, state: FSMContext):
    await state.update_data(currency_name=message.text)
    prosto = await state.get_data()
    conn = pg.connect(
        host="localhost",
        database="rgz_rpp",
        user="postgres",
        password="1234"
    )
    cursor = conn.cursor()
    cursor.execute("SELECT mediaan_price FROM data_bumaga WHERE name = %(currency_name)s", {"currency_name": prosto['currency_name']})
    afghan = cursor.fetchone()
    await message.reply(afghan)

def periodic():
    conn = pg.connect(
        host="localhost",
        database="rgz_rpp",
        user="postgres",
        password="1234"
    )
    cursor = conn.cursor()
    ticker = threading.Event()
    while not ticker.wait(5/300):
        i = 0
        cursor.execute("Select name from bumaga")
        blanks = cursor.fetchall()
        print(blanks)
        for i in blanks:
            get_daily_closing_prices(i[0])


if __name__ == '__main__':
    executor.start_polling(dp, skip_updates=True)
    threading.Thread(target=periodic()).start()


