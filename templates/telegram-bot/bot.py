import asyncio
import logging
from aiogram import Bot, Dispatcher, types
from aiogram.filters import Command

TOKEN = 'YOUR_BOT_TOKEN'
logging.basicConfig(level=logging.INFO)

bot = Bot(token=TOKEN)
dp = Dispatcher()

@dp.message(Command('start'))
async def cmd_start(message: types.Message):
    await message.answer(f'Hello, {message.from_user.full_name}!')

@dp.message(Command('help'))
async def cmd_help(message: types.Message):
    await message.answer('Commands: /start, /help, /ping')

@dp.message(Command('ping'))
async def cmd_ping(message: types.Message):
    await message.answer('Pong!')

async def main():
    await dp.start_polling(bot)

if __name__ == '__main__':
    asyncio.run(main())
