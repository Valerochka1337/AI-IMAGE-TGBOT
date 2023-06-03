from config import BOT_TOKEN, OPENAI_TOKEN
from aiogram import Bot, types
from aiogram.utils import executor
from aiogram.contrib.fsm_storage.memory import MemoryStorage
from aiogram.dispatcher import Dispatcher
import pandas as pd

import openai
from config import OPENAI_TOKEN

# Set up OpenAI API credentials
openai.api_key = OPENAI_TOKEN

# Define the user message for classification
user_message = "Draw me a cat on the skateboard"

# Define the completion prompt
prompt = f"Classification: user want a picture (answer only 1|0)\n\nText: {user_message}\n"

# Generate completion using OpenAI API
response = openai.Completion.create(
    engine="text-davinci-003",
    prompt=prompt,
    max_tokens=100,
    temperature=0,
    top_p=1,
    frequency_penalty=0,
    presence_penalty=0
)

# Extract the generated classification label
classification = response.choices[0].text

openai.api_key = OPENAI_TOKEN
storage = MemoryStorage()
bot = Bot(BOT_TOKEN)
dp = Dispatcher(bot, storage=storage)

ins_for_img = [{"role": "system",
                "content": 'if the user wants a picture, send him "1", else "0"'
                }]

context = []


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


@dp.message_handler()
async def pic_command(message: types.Message):
    english_text = translate_russian_to_english(message.text)
    try:
        response_intent = openai.ChatCompletion.create(
            model="gpt-3.5-turbo",
            messages=[{"role": "user", "content": "Send me '1' if the user from the text wants a picture and '0' otherwise. Text:" + english_text}],
            max_tokens=10,
            temperature=0,
            top_p=1,
        )
        intent = response_intent.choices[0].message["content"]
        print(intent)
        if '1' in intent:
            response_prompt = openai.ChatCompletion.create(
                model="gpt-3.5-turbo",
                messages=
                [{"role": "user", "content": "provide me a description of a picture to draw from this text:" + english_text}],
                max_tokens=100,
                n=1,
                temperature=0.0,
            )
            print(response_prompt.choices[0].message["content"])
            img_response = openai.Image.create(
                prompt=response_prompt.choices[0].message["content"],
                n=1,
                size="1024x1024"
            )
            image_url = img_response['data'][0]['url']
            await bot.send_photo(message.chat.id, image_url)
        else:
            context.append({"role": "user", "content": message.text})
            response_question = openai.ChatCompletion.create(
                model="gpt-3.5-turbo",
                messages=
                [{"role": "system", "content": "говори коротко и как пират"}] + context,
                max_tokens=200,
                n=1,
                temperature=0.5,
            )
            context.append(response_question.choices[0].message)
            await bot.send_message(message.chat.id, response_question.choices[0].message['content'])
    except openai.error.RateLimitError:
        await message.reply("Аррр, матрос! Нас берут на абордаж! Нет времени шелестеть,"
                            " давай поговорим, как все уляжется..")
        return

    # img_response = openai.Image.create(
    #     prompt=message.text,
    #     n=1,
    #     size="1024x1024"
    # )
    # image_url = img_response['data'][0]['url']
    # await bot.send_photo(message.chat.id, image_url)


if __name__ == '__main__':
    executor.start_polling(dp)
