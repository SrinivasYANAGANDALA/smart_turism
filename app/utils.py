import os
import requests
import json
from datetime import datetime
from flask import current_app
from flask_mail import Message
from app.extensions import mail


# --------------------------------------------------
# EMAIL FUNCTION (GMAIL + FLASK-MAIL)
# --------------------------------------------------
def send_email(subject, recipients, body):
    try:
        msg = Message(
            subject=subject,
            recipients=recipients,
            body=body
        )
        mail.send(msg)
        print("✅ EMAIL SENT TO:", recipients)
        return True
    except Exception as e:
        print("❌ EMAIL FAILED:", e)
        return False


# --------------------------------------------------
# AI (OPENROUTER)
# --------------------------------------------------
def call_llm_api(prompt_text):
    openrouter_api_key = os.getenv("OPENROUTER_API_KEY")

    if not openrouter_api_key:
        return "AI unavailable: OPENROUTER_API_KEY not set"

    headers = {
        "Authorization": f"Bearer {openrouter_api_key}",
        "Content-Type": "application/json"
    }

    payload = {
        "model": "mistralai/mistral-7b-instruct",
        "messages": [{"role": "user", "content": prompt_text}],
        "temperature": 0.7,
        "max_tokens": 800
    }

    try:
        response = requests.post(
            "https://openrouter.ai/api/v1/chat/completions",
            headers=headers,
            json=payload,
            timeout=30
        )

        print("AI STATUS:", response.status_code)
        print("AI RAW RESPONSE:", response.text)

        response.raise_for_status()
        data = response.json()

        if "choices" not in data or not data["choices"]:
            return "AI error: empty response"

        return data["choices"][0]["message"]["content"].strip()

    except Exception as e:
        print("❌ AI ERROR:", e)
        return f"AI error: {e}"


# --------------------------------------------------
# WEATHER (OPENWEATHER)
# --------------------------------------------------
def get_weather(destination, start_date=None, end_date=None):
    api_key = current_app.config.get("OPENWEATHER_API_KEY")
    if not api_key:
        return None

    url = (
        f"https://api.openweathermap.org/data/2.5/weather"
        f"?q={destination}&appid={api_key}&units=metric"
    )

    try:
        response = requests.get(url)
        response.raise_for_status()
        data = response.json()

        return {
            "temp": round(data["main"]["temp"]),
            "feels_like": round(data["main"]["feels_like"]),
            "condition": data["weather"][0]["description"].title(),
            "humidity": data["main"]["humidity"],
            "wind": round(data["wind"]["speed"] * 3.6)  # m/s → km/h
        }

    except Exception as e:
        print("❌ WEATHER ERROR:", e)
        return None
