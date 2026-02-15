import os
import requests
import tempfile
import asyncio
from dotenv import load_dotenv

from ai_assistant import ai_reply
from calculator import calculate_garage, get_total_price, extract_kp_file

from aiogram import Bot, Dispatcher, types, F
from aiogram.filters import CommandStart
from aiogram.types import ReplyKeyboardMarkup, KeyboardButton

# ================= ENV =================
load_dotenv()

BOT_TOKEN = os.getenv("BOT_TOKEN")
CALC_API_URL = os.getenv("CALC_API_URL")
CALC_API_TOKEN = os.getenv("CALC_API_TOKEN")

if not BOT_TOKEN:
    raise RuntimeError("BOT_TOKEN отсутствует в .env")

# ================= BOT =================
bot = Bot(token=BOT_TOKEN)
dp = Dispatcher()

sessions = {}

# ================= KEYBOARDS =================
def kb(options):
    k = ReplyKeyboardMarkup(resize_keyboard=True, one_time_keyboard=True)
    for o in options:
        k.add(KeyboardButton(text=o))
    return k

KB_YES_NO = kb(["Да", "Нет"])

KB_ROOF = kb([
    "Односкатная вперед",
    "Односкатная назад",
    "Односкатная вбок",
    "Двускатная"
])

KB_INSULATION = kb([
    "Минеральная вата",
    "Пенополистирол",
    "PIR"
])

# ================= API =================
def call_calculator(data, need_kp):
    payload = {
        "input_cells": {
            "C14": str(data["length"]),
            "C16": str(data["width"]),
            "G14": str(data["height"]),
            "G16": str(data["peak"]),
            "C18": data["roof"],
            "E70": data["insulation"],
            "E72": "100",
            "E76": data["insulation"],
            "E78": "100",
            "G18": "Отдельностоящий",
            "G9": "1",
        },
        "cells_to_return": {
            "total": {"sheet": "Калькулятор", "cell": "G4"}
        }
    }

    if need_kp:
        payload["generate_kp"] = True

    headers = {
        "Authorization": f"Bearer {CALC_API_TOKEN}",
        "Content-Type": "application/json"
    }

    r = requests.post(CALC_API_URL, json=payload, headers=headers, timeout=40)
    r.raise_for_status()
    return r.json()

# ================= SEND KP =================
async def send_kp_if_exists(chat_id, result):
    for key, value in result.items():
        if isinstance(value, str) and value.lower().endswith(".pdf"):
            r = requests.get(value, timeout=30)

            with tempfile.NamedTemporaryFile(delete=False, suffix=".pdf") as f:
                f.write(r.content)
                path = f.name

            await bot.send_document(
                chat_id,
                types.FSInputFile(path),
                caption="📄 Коммерческое предложение"
            )
            return True

    return False

# ================= START =================
@dp.message(CommandStart())
async def start(msg: types.Message):
    sessions[msg.from_user.id] = {}
    await msg.answer("Длина гаража (м):")

# ================= FLOW =================
@dp.message()
async def flow(msg: types.Message):
    uid = msg.from_user.id
    s = sessions.get(uid)

    # если пользователь не в режиме опроса → AI
    if s is None:
        await ai_reply(msg)
        return

    try:
        if "length" not in s:
            s["length"] = float(msg.text)
            await msg.answer("Ширина (м):")

        elif "width" not in s:
            s["width"] = float(msg.text)
            await msg.answer("Высота стен (м):")

        elif "height" not in s:
            s["height"] = float(msg.text)
            await msg.answer("Высота в коньке (м):")

        elif "peak" not in s:
            s["peak"] = float(msg.text)
            await msg.answer("Тип крыши:", reply_markup=KB_ROOF)

        elif "roof" not in s:
            s["roof"] = msg.text
            await msg.answer("Тип утеплителя:", reply_markup=KB_INSULATION)

        elif "insulation" not in s:
            s["insulation"] = msg.text
            await msg.answer("Сформировать КП (PDF)?", reply_markup=KB_YES_NO)

        elif "need_kp" not in s:
            s["need_kp"] = (msg.text == "Да")
            await msg.answer("⏳ Считаю стоимость...")

            result = call_calculator(s, s["need_kp"])
            price = result.get("total", 0)

            await msg.answer(
                f"💰 Стоимость гаража:\n{int(price):,} ₽".replace(",", " ")
            )

            if s["need_kp"]:
                sent = await send_kp_if_exists(msg.chat.id, result)
                if not sent:
                    await msg.answer("❌ API не вернул PDF")

            sessions.pop(uid, None)

    except Exception as e:
        print("ERROR:", e)
        await msg.answer("Ошибка ввода, попробуйте ещё раз.")

# ================= RUN =================
async def main():
    print("🤖 Bot started")
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
