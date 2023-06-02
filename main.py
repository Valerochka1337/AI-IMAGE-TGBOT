from config import BOT_TOKEN, OPENAI_TOKEN
from aiogram import Bot, types
from aiogram.utils import executor
from aiogram.contrib.fsm_storage.memory import MemoryStorage
from aiogram.dispatcher import Dispatcher
import openai
import pandas as pd

openai.api_key = OPENAI_TOKEN
storage = MemoryStorage()
bot = Bot(BOT_TOKEN)
dp = Dispatcher(bot, storage=storage)


@dp.message_handler(commands=["pic"])
async def pic_command(message: types.Message):
    picture_url = "https://images.nightcafe.studio/jobs/xiXo0OdL84rI7K4kt2F2/xiXo0OdL84rI7K4kt2F2--1--ubajl.jpg?tr=w-1600,c-at_max"
    response_text = "Ya YA Ez geit"
    await bot.send_photo(message.chat.id, picture_url, response_text)


if __name__ == '__main__':
    executor.start_polling(dp)
