import os
import requests
from dotenv import load_dotenv

load_dotenv()

CALC_API_URL = os.getenv("CALC_API_URL")
CALC_API_TOKEN = os.getenv("CALC_API_TOKEN")

if not CALC_API_URL:
    raise RuntimeError("CALC_API_URL отсутствует в .env")


# ==========================================
# ВЫЗОВ API
# ==========================================
def calculate_garage(config: dict, need_kp: bool = False):

    payload = build_payload(config, need_kp)

    headers = {
        "Content-Type": "application/json"
    }

    if CALC_API_TOKEN:
        headers["Authorization"] = f"Bearer {CALC_API_TOKEN}"

    try:
        response = requests.post(
            CALC_API_URL,
            json=payload,
            headers=headers,
            timeout=90
        )

        response.raise_for_status()
        data = response.json()

        print("====== API RESPONSE ======")
        print(data)
        print("==========================")

        return data

    except Exception as e:
        print("CALCULATOR ERROR:", e)
        return {"error": str(e)}


# ==========================================
# PAYLOAD
# ==========================================
def build_payload(data: dict, need_kp: bool):

    input_cells = {
        # размеры
        "C14": str(data["length"]),
        "C16": str(data["width"]),
        "G14": str(data["height"]),
        "G16": str(data["peak_height"]),

        # кровля
        "C18": data["roof_type"],

        # утепление
        "E70": data["insulation"],
        "E72": "100",
        "E76": data["insulation"],
        "E78": "100",

        # размещение
        "G18": "Отдельностоящий",

        # объект на 1 машину
        "G9": "1",

        # ворота
        "E22": str(data["gates_count"]),
        "E24": str(data["automation_count"]),

        # дверь всегда 1
        "E40": "1",
        "E42": data["door_type"],

        # окна
        "E50": str(data["windows_count"]),
        "E52": data["window_size"],

        # водосток
        "E60": "Да" if data["drainage"] else "Нет",

        # электрика
        "E62": "Да" if data["electricity"] else "Нет",
    }

    payload = {
        "input_cells": input_cells,
        "cells_to_return": {
            "total": {"sheet": "Калькулятор", "cell": "G4"}
        }
    }

    if need_kp:
        payload["generate_kp"] = True

    return payload


# ==========================================
# УДОБНЫЕ ФУНКЦИИ
# ==========================================
def get_total_price(result: dict):
    if not result:
        return None
    if "total" in result:
        return int(float(result["total"]))
    return None


def extract_kp_file(result: dict):
    if not result:
        return None

    if "kp_pdf" in result:
        return result["kp_pdf"]

    if "pdf" in result:
        return result["pdf"]

    return None
