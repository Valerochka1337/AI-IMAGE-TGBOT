from config import BOT_TOKEN, OPENAI_TOKEN
from aiogram import Bot, types
from aiogram.utils import executor
from aiogram.contrib.fsm_storage.memory import MemoryStorage
from aiogram.dispatcher import Dispatcher
import pandas as pd
import re

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

IMAGE_CHATGPT_PREFIX = """Image ChatGPT is designed to be able to assist with a wide range of text and visual related tasks, from answering simple questions to providing in-depth explanations and discussions on a wide range of topics. Visual ChatGPT is able to generate human-like text based on the input it receives, allowing it to engage in natural-sounding conversations and provide responses that are coherent and relevant to the topic at hand.

Image ChatGPT is able to process and understand large amounts of text and images. As a language model, Image ChatGPT can not directly draw/generate images, but it has a list of tools to finish visual tasks.

Overall, Visual ChatGPT is a powerful visual dialogue assistant tool that can help with a wide range of tasks and provide valuable insights and information on a wide range of topics. 

Tools are STRICTLY FORMATTED and cannot be used differently from the format below. Image ChatGPT cannot use other tools or change the format

Image ChatGPT has access to the following tools:

TOOLS:
[IMAGE]{description_of_image}

Image ChatGPT has a STRICT FORMAT ANSWER to a human:

FORMAT OF ANSWER:
Some text response to a human (optional)
[IMAGE]{Description of the image} (optional)
...

"""

IMAGE_CHATGPT_SUFFIX = """
Image ChatGPT is facing a real human, who thinks that it can provide him with images by itself. However, you can just use a tool, which can be converted to a real answer and sent as a response to a human.

Since Image ChatGPT is a text language model, Image ChatGPT must use tools to create images rather than imagination.

If a user wants you to send him a picture just USE A TOOL [IMAGE]{description of the image}

Use NO IMAGE URL, {description of the image} MUST contain only an IMAGE DESCRIPTION, it will be converted to a real image afterwards and sent to the user

DO NOT say that you CANNOT DRAW PICTURES, do not say you use tools. Just answer him and if the image is needed provide it using following format:

[IMAGE]{your description of the image in english}

Please speak only russian and assume that ALL [IMAGE]{...} used should be assumed as a real image, not a text.

ADDITIONAL: Please, use images only if the user wants them
"""


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

self_messages = [{"role": "system", "content":"You are a helpful assistant, who speaks russian"},{"role": "system", "content":IMAGE_CHATGPT_PREFIX}]


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
            if len(part) > 5:
                result["data"].append({"type": "image", "content": part})
        elif part:
            if len(part) > 5:
                result["data"].append({"type": "text", "content": part})

    return result


@dp.message_handler()
async def respond(message: types.Message):
    global context
    print("Message got from" + message.from_user.first_name + "message:" + message.text)
    # print("translated message from" + message.from_user.first_name + "message:" + english_text)
    try:
        response = openai.ChatCompletion.create(
            model="gpt-3.5-turbo",
            messages=self_messages + context + [{"role": "user", "content": message.text}] + [{"role": "system", "content": IMAGE_CHATGPT_SUFFIX}],
            max_tokens=500,
            temperature=0,
            top_p=1,
        )
        context += [{"role": "user", "content": message.text}] + [{"role":"assistant", "content":response.choices[0].message["content"]}]

        response_msg = response.choices[0].message["content"]
        print(response_msg)
        for el in parse_response(response_msg)["data"]:
            if el["type"] == "text":
                await bot.send_message(message.chat.id, el['content'])
            else:
                await bot.send_photo(message.chat.id, generate_image(el['content']))

    except Exception as e:
        print(e)
        await message.reply("Блин, ну не могу пока я так, не могу....")


# @dp.message_handler()
# async def pic_command(message: types.Message):
#     english_text = translate_russian_to_english(message.text)
#     try:
#         response_intent = openai.ChatCompletion.create(
#             model="gpt-3.5-turbo",
#             messages=[{"role": "user",
#                        "content": "Send me '1' if the user from the text wants a picture and '0' otherwise. Text:" + english_text}],
#             max_tokens=10,
#             temperature=0,
#             top_p=1,
#         )
#         intent = response_intent.choices[0].message["content"]
#         print(intent)
#         if '1' in intent:
#             response_prompt = openai.ChatCompletion.create(
#                 model="gpt-3.5-turbo",
#                 messages=
#                 [{"role": "user",
#                   "content": "provide me a description of a picture to draw from this text:" + english_text}],
#                 max_tokens=100,
#                 n=1,
#                 temperature=0.0,
#             )
#             print(response_prompt.choices[0].message["content"])
#             img_response = openai.Image.create(
#                 prompt=response_prompt.choices[0].message["content"],
#                 n=1,
#                 size="1024x1024"
#             )
#             image_url = img_response['data'][0]['url']
#             await bot.send_photo(message.chat.id, image_url)
#         else:
#             context.append({"role": "user", "content": message.text})
#             response_question = openai.ChatCompletion.create(
#                 model="gpt-3.5-turbo",
#                 messages=
#                 [{"role": "system", "content": "говори коротко и как пират"}] + context,
#                 max_tokens=200,
#                 n=1,
#                 temperature=0.5,
#             )
#             context.append(response_question.choices[0].message)
#             await bot.send_message(message.chat.id, response_question.choices[0].message['content'])
#     except openai.error.RateLimitError:
#         await message.reply("Аррр, матрос! Нас берут на абордаж! Нет времени шелестеть,"
#                             " давай поговорим, как все уляжется..")
#         return

    # img_response = openai.Image.create(
    #     prompt=message.text,
    #     n=1,
    #     size="1024x1024"
    # )
    # image_url = img_response['data'][0]['url']
    # await bot.send_photo(message.chat.id, image_url)


if __name__ == '__main__':
    executor.start_polling(dp)
