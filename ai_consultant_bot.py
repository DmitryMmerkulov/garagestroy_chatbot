import os
from aiogram import types
from aiogram.types import ReplyKeyboardMarkup, KeyboardButton
from dotenv import load_dotenv
from openai import OpenAI

# ========== ENV ==========
load_dotenv()
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")

if not OPENAI_API_KEY:
    raise RuntimeError("OPENAI_API_KEY не найден в .env")

client = OpenAI(api_key=OPENAI_API_KEY)

# ========== MEMORY ==========
user_memory = {}

# ========== KEYBOARD ==========
def ai_keyboard():
    kb = ReplyKeyboardMarkup(resize_keyboard=True)
    kb.add(KeyboardButton("🧮 Рассчитать стоимость"))
    kb.add(KeyboardButton("📞 Связаться с менеджером"))
    return kb

# ========== SYSTEM PROMPT ==========
SYSTEM_PROMPT = """
Ты — онлайн-консультант компании «ГаражСтрой».

Ты эксперт по строительству гаражей:
— металлические гаражи
— гаражи из сэндвич-панелей
— утепление (минвата, пенополистирол)
— ворота (DoorHan, Алютех)
— автоматика ворот
— двери (металлические утеплённые, ПВХ)
— окна ПВХ
— фундамент (плита, сваи)
— монтаж и доставка

Ты можешь:
— объяснять
— помогать с выбором
— сравнивать варианты
— давать рекомендации

Если человек хочет узнать цену —
предлагай нажать кнопку «Рассчитать стоимость».

Отвечай спокойно, по-человечески.
Без воды.
"""

# ========== AI CORE ==========
def ask_ai(user_id: int, user_text: str) -> str:
    history = user_memory.get(user_id, [])

    history.append({"role": "user", "content": user_text})

    response = client.chat.completions.create(
        model="gpt-4.1-mini",
        messages=[
            {"role": "system", "content": SYSTEM_PROMPT},
            *history[-10:]
        ],
        temperature=0.4,
        max_tokens=800
    )

    answer = response.choices[0].message.content

    history.append({"role": "assistant", "content": answer})
    user_memory[user_id] = history

    return answer

# ========== HANDLER ==========
async def ai_reply(message: types.Message):
    await message.answer("✍️ Думаю...")

    try:
        answer = ask_ai(message.from_user.id, message.text)

        await message.answer(
            answer,
            reply_markup=ai_keyboard()
        )

    except Exception as e:
        print("AI ERROR:", e)
        await message.answer(
            "Произошла ошибка. Попробуйте позже."
        )
