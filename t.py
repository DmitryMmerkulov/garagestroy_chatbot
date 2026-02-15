import os
import requests
from aiogram import Bot, Dispatcher, types
from aiogram.types import ReplyKeyboardMarkup, KeyboardButton
from aiogram.utils import executor
from dotenv import load_dotenv

# ========== ENV ==========
load_dotenv()
BOT_TOKEN = os.getenv("BOT_TOKEN")
CALC_API_URL = os.getenv("CALC_API_URL")
CALC_API_TOKEN = os.getenv("CALC_API_TOKEN")

if not BOT_TOKEN or not CALC_API_URL or not CALC_API_TOKEN:
    raise RuntimeError("Проверь .env")

# ========== BOT ==========
bot = Bot(token=BOT_TOKEN)
dp = Dispatcher(bot)
sessions = {}

# ========== KEYBOARDS ==========
def kb(options):
    k = ReplyKeyboardMarkup(resize_keyboard=True, one_time_keyboard=True)
    for o in options:
        k.add(KeyboardButton(o))
    return k

KB_ROOF = kb([
    "Односкатная вбок",
    "Односкатная назад",
    "Односкатная вперед",
    "Двускатная",
    "Четырехскатная"
])

KB_YES_NO = kb(["Да", "Нет"])

KB_DOOR = kb([
    "Металлическая утеплённая",
    "ПВХ"
])

KB_WINDOW = kb([
    "1000x600мм с фрамугой",
    "1000x1000мм с поворотно-откидной створкой"
])

KB_INSULATION = kb([
    "Минеральная вата",
    "Пенополистирол",
    "PIR"
])

KB_FOUNDATION = kb([
    "Уже имеется",
    "Свайный",
    "Сваи+стяжка",
    "Монолитная плита"
])

# ========== API ==========
def call_calculator(d, need_kp):
    input_cells = {
        "C10": "Гараж",
        "C12": "На одну машину",

        "C14": str(d["length"]),
        "C16": str(d["width"]),
        "G14": str(d["height"]),
        "G16": str(d["peak"]),

        "C18": d["roof"],
        "G18": "Отдельностоящий",
        "G9": "1",

        # Ворота
        "D38": True,
        "D40": str(d["gate_qty"]),
        "G40": str(d["gate_width"]),
        "G42": str(d["gate_height"]),
        "D118": str(d["gate_qty"]),  # автоматика = кол-во ворот

        # Дверь (ВСЕГДА 1)
        "D57": True,
        "F57": "1" if d["door"] == "Металлическая утеплённая" else "2",
        "G59": "1",

        # Доп двери
        "D110": str(d["extra_doors_qty"]),

        # Окна
        "A97": "Да",
        "C99": d["window_size"],
        "H99": str(d["windows_qty"]),
        "C101": "",
        "H101": "0",
        "C103": "",
        "H103": "0",

        # Сэндвич
        "E70": d["insulation"],
        "E72": "100",
        "E76": d["insulation"],
        "E78": "100",

        # Доп
        "D114": "Да" if d["drainage"] else "Нет",
        "D116": "Да" if d["electricity"] else "Нет",

        # Фундамент
        "C122": d["foundation"]
    }

    payload = {
        "input_cells": input_cells,
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

def send_kp_pdf(bot, chat_id, url):
    r = requests.get(url, timeout=40)
    r.raise_for_status()

    with tempfile.NamedTemporaryFile(delete=False, suffix=".pdf") as f:
        f.write(r.content)
        file_path = f.name

    with open(file_path, "rb") as pdf:
        bot.send_document(
            chat_id,
            pdf,
            caption="📄 Коммерческое предложение (PDF)"
        )

    os.remove(file_path)

# ========== BOT FLOW ==========
@dp.message_handler(commands=["start"])
async def start(msg: types.Message):
    sessions[msg.from_user.id] = {}
    await msg.answer("Длина гаража (м):")

@dp.message_handler()
async def flow(msg: types.Message):
    uid = msg.from_user.id
    s = sessions[uid]

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
            await msg.answer("Количество ворот (шт):")

        elif "gate_qty" not in s:
            s["gate_qty"] = int(msg.text)
            await msg.answer("Ширина ворот (мм):")

        elif "gate_width" not in s:
            s["gate_width"] = int(msg.text)
            await msg.answer("Высота ворот (мм):")

        elif "gate_height" not in s:
            s["gate_height"] = int(msg.text)
            await msg.answer("Тип двери:", reply_markup=KB_DOOR)

        elif "door" not in s:
            s["door"] = msg.text
            await msg.answer("Дополнительные двери нужны?", reply_markup=KB_YES_NO)

        elif "extra_doors" not in s:
            if msg.text == "Да":
                s["extra_doors"] = True
                await msg.answer("Количество дополнительных дверей:")
            else:
                s["extra_doors"] = False
                s["extra_doors_qty"] = 0
                await msg.answer("Размер окон:", reply_markup=KB_WINDOW)

        elif s.get("extra_doors") and "extra_doors_qty" not in s:
            s["extra_doors_qty"] = int(msg.text)
            await msg.answer("Размер окон:", reply_markup=KB_WINDOW)

        elif "window_size" not in s:
            s["window_size"] = msg.text
            await msg.answer("Количество окон:")

        elif "windows_qty" not in s:
            s["windows_qty"] = int(msg.text)
            await msg.answer("Тип утеплителя:", reply_markup=KB_INSULATION)

        elif "insulation" not in s:
            s["insulation"] = msg.text
            await msg.answer("Водосточная система?", reply_markup=KB_YES_NO)

        elif "drainage" not in s:
            s["drainage"] = (msg.text == "Да")
            await msg.answer("Электрика и освещение?", reply_markup=KB_YES_NO)

        elif "electricity" not in s:
            s["electricity"] = (msg.text == "Да")
            await msg.answer("Тип фундамента:", reply_markup=KB_FOUNDATION)

        elif "foundation" not in s:
            s["foundation"] = msg.text
            await msg.answer("Сформировать КП (PDF)?", reply_markup=KB_YES_NO)

        elif "need_kp" not in s:
            s["need_kp"] = (msg.text == "Да")
            await msg.answer("⏳ Считаю стоимость...")
            result = call_calculator(s, s["need_kp"])

            price = f"{result['total']:,.0f} ₽".replace(",", " ")
            await msg.answer(f"💰 Стоимость гаража:\n{price}")

            if s["need_kp"] and "kp_url" in result:
                await msg.answer("📄 Отправляю КП...")
                send_kp_pdf(bot, msg.chat.id, result["kp_url"])

            sessions.pop(uid)

    except Exception as e:
        print("ERROR:", e)
        await msg.answer("Введите корректное значение.")

# ========== RUN ==========
if __name__ == "__main__":
    print("🤖 Bot started")
    executor.start_polling(dp, skip_updates=True)
