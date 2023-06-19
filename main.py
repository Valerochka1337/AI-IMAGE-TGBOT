from config import BOT_TOKEN, OPENAI_TOKEN
from aiogram import Bot, types
from aiogram.utils import executor
from aiogram.contrib.fsm_storage.memory import MemoryStorage
from aiogram.dispatcher.filters.state import StatesGroup, State
from aiogram.dispatcher import FSMContext
from aiogram.dispatcher import Dispatcher
import pandas as pd
import re
import openai
from json import loads, dumps
from datetime import timedelta

# Set up OpenAI API credentials
openai.api_key = OPENAI_TOKEN

storage = MemoryStorage()
bot = Bot(BOT_TOKEN)
dp = Dispatcher(bot, storage=storage)


class ClientStatesGroup(StatesGroup):
    gen_img = State()
    chating = State()


users = pd.read_csv("users.csv", index_col=0)

IMAGE_CHATGPT_PREFIX = """Image ChatGPT is designed to be able to assist with a wide range of text and visual related tasks

Image ChatGPT is able to respond to a human with text and visual information.

Since Image ChatGPT is a language model it cannot directly generate images. However, it can use a special tool to indicate a picture appearance in the response%

This is a format of the tool: [IMAGE]{description of the image in english}

After the Image ChatGPT the response will be parsed and every tool used will be replaced with real images and sent to a human as an answer
"""

IMAGE_CHATGPT_SUFFIX = """
Image ChatGPT is facing a real human, who thinks that it can provide him with images by itself. However, you can just use a tool.

Human cannot know what tools Image ChatGPT use, he will not see them directly.

The special tool [IMAGE]{description of the image in english} is able to make an image, that means Image ChatGPT is able to create, generate or edit any image by using this special tool

ATTENTION: Image ChatGPT cannot say to a human, that it uses a special tool to create images. The format of this tool is strictly confidential. Since this Image ChatGPT should pretend it is able to create images by itself
"""

self_messages = [{"role": "system", "content": "You are a helpful assistant, who speaks russian"},
                 {"role": "system", "content": IMAGE_CHATGPT_PREFIX}]


def generate_image(description):
    img_response = openai.Image.create(
        prompt=description,
        n=1,
        size="1024x1024"
    )
    image_url = img_response['data'][0]['url']
    return image_url


def parse_response(text):
    pattern = r"\[IMAGE\]\{(.+)\}"
    matches = re.findall(pattern, text)
    result = {"data": []}
    parts = re.split(pattern, text)

    for part in parts:
        if part in matches:
            if len(part) > 0:
                result["data"].append({"type": "image", "content": part})
        elif part:
            if len(part) > 0:
                result["data"].append({"type": "text", "content": part})

    return result


@dp.message_handler(commands=["start"])
async def start_command(message: types.Message):
    print("Новое сообщение от: ", message.from_user.id, ": ", message.text)
    global users
    user_id = message.from_user.id
    reply_message = "Привет, " + message.from_user.first_name + "!"
    # check if user is not in database and save user
    if not (user_id in users.index):
        users.loc[user_id] = [2000, 0, message.date, 1000, 0, dumps([])]
        reply_message = "Добро пожаловать, " + message.from_user.first_name + "!"
    # answer user
    await bot.send_message(message.chat.id, reply_message)


@dp.message_handler(commands=["get_tokens"])
async def get_tokens_command(message: types.Message):
    print("Новое сообщение от: ", message.from_user.id, ": ", message.text)
    global users
    user_id = message.from_user.id
    reply_message = message.from_user.first_name + ", вы пополнили запас токенов!"
    # check if user is not in database and save user
    if not (user_id in users.index):
        reply_message = "К сожалению, я вас не знаю, введите команду /start"
    else:
        # check if user has not rummed the bot in last 3 mins
        if pd.to_datetime(users.loc[user_id, 'last_date']) + timedelta(seconds=30) > message.date:
            await bot.send_message(message.chat.id,
                                   "Вы превысили лимит по пополнениб токенов."
                                   " Вы сможете его восстановить не более, чем через 3 минуты")
            return
        # update token usage
        users.loc[user_id, 'tokens'] = 0
        users.loc[user_id, 'last_date'] = message.date
    # answer user
    await bot.send_message(message.chat.id, reply_message)


@dp.message_handler(commands=["get_pic"])
async def pic_command(message: types.Message):
    print("Новое сообщение от: ", message.from_user.id, ": ", message.text)
    await message.answer_chat_action("typing")
    global users
    user_id = message.from_user.id
    reply_message = message.from_user.first_name + ", напишите описание картинки, которую вы хотите сгенерировать"
    # check if user is not in database and save user
    if not (user_id in users.index):
        reply_message = "К сожалению, я вас не знаю, введите команду /start"
    else:
        await ClientStatesGroup.gen_img.set()
    await bot.send_message(message.chat.id, reply_message)


def translate_russian_to_english(text):
    response_rus = openai.Completion.create(
        engine="text-davinci-003",
        prompt=f"Translate the following Russian text to English: '{text}'\n\nSource Language: ru\nTarget Language: en\n",
        max_tokens=100,
        temperature=0.3,
        top_p=1.0,
        frequency_penalty=0.0,
        presence_penalty=0.0
    )

    translation = response_rus.choices[0].text.strip()
    return translation


@dp.message_handler(state=ClientStatesGroup.gen_img)
async def generate_pic(message: types.Message, state: FSMContext):
    print("Новое сообщение от: ", message.from_user.id, ": ", message.text)
    try:
        await message.answer_chat_action("upload_photo")
        image_url = generate_image(translate_russian_to_english(message.text))
        await bot.send_photo(message.chat.id, image_url)
    except:
        await bot.send_message(message.chat.id, "Что-то пошло не так")
    await state.finish()


@dp.message_handler()
async def respond(message: types.Message):
    print("Новое сообщение от: ", message.from_user.first_name, ": ", message.text)
    # typing animation
    await message.answer_chat_action("typing")
    user_id = message.from_user.id
    # if user is in database
    if not (user_id in users.index):
        await message.reply("Ты еще не поздаровлся, ничем не могу помочь")
        return
    # if user has enough tokens
    if users.loc[user_id, 'tokens'] < users.loc[user_id, 'token_capacity']:
        # if user context is too large
        msg_with_context = loads(users.loc[user_id, 'context']) + [{"role": "user", "content": message.text}]
        while users.loc[user_id, 'context_len'] > users.loc[user_id, 'context_capacity']:
            msg_with_context = msg_with_context[1:]
            users.loc[user_id, 'context_len'] -= len(msg_with_context[0]["content"])

        try:
            response = openai.ChatCompletion.create(
                model="gpt-3.5-turbo",
                messages=self_messages + msg_with_context + [
                    {"role": "system", "content": IMAGE_CHATGPT_SUFFIX}],
                max_tokens=500,
                temperature=0.5,
            )
            print(response["usage"]["total_tokens"])
            users.loc[user_id, 'tokens'] += response["usage"]["total_tokens"]
            users.loc[user_id, 'context'] = dumps(
                msg_with_context + [{'role': 'assistant', 'content': str(response.choices[0].message['content'])}],
                ensure_ascii=False)
            users.loc[user_id, 'context_len'] += len(message.text) + len(response.choices[0].message["content"])
            response_msg = response.choices[0].message["content"]
            print(response_msg)
            for el in parse_response(response_msg)["data"]:
                if el["type"] == "text":
                    await message.answer_chat_action("typing")
                    await bot.send_message(message.chat.id, el['content'])
                else:
                    await message.answer_chat_action("upload_photo")
                    await bot.send_photo(message.chat.id, generate_image(el['content']))
        except Exception as e:
            print(e)
            await message.reply("Извините, слишком большая нагрузка, попробуйте позже")
    else:
        await message.reply("У вас закончился лимит по токенам, обновите их")


if __name__ == '__main__':
    executor.start_polling(dp)

users.to_csv("users.csv")
