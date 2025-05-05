#!/usr/bin/env python3
import json
import time
import logging
from http.server import BaseHTTPRequestHandler, HTTPServer
from datetime import datetime, timedelta
import threading
import os
import requests

# === SETTINGS ===
TOKEN = "telegram_bot_token"
CHAT_ID = "chat_id"
PORT = 8081
STATS_FILE = "stats.json"
STATE_FILE = "state.json"

logging.basicConfig(level=logging.INFO)

def format_duration(seconds):
    minutes = int(seconds) // 60
    sec = int(seconds) % 60
    parts = []
    if minutes > 0:
        parts.append(f"{minutes} мин")
    if sec > 0 or not parts:
        parts.append(f"{sec} сек")
    return ' '.join(parts)

# === FUNCTIONS ===
def load_json(path, default):
    try:
        with open(path) as f:
            return json.load(f)
    except Exception as e:
        logging.warning(f"Не удалось загрузить {path}: {e}")
        return default

def save_json(path, data):
    with open(path, "w") as f:
        json.dump(data, f, indent=2)

def send_message(text):
    url = f"https://api.telegram.org/bot{TOKEN}/sendMessage"
    requests.post(url, data={"chat_id": CHAT_ID, "text": text})

def update_stats(duration_sec):
    now = datetime.now()
    today = now.strftime("%Y-%m-%d")
    stats = load_json(STATS_FILE, {})
    day = stats.setdefault(today, {"events": 0, "total_downtime_seconds": 0})
    day["events"] += 1
    day["total_downtime_seconds"] += duration_sec
    save_json(STATS_FILE, stats)

def daily_reset():
    while True:
        now = datetime.now()
        next_reset = (now + timedelta(days=1)).replace(hour=0, minute=0, second=0, microsecond=0)
        seconds_until_reset = (next_reset - now).total_seconds()
        logging.info(f"Ожидание {round(seconds_until_reset)} сек до сброса")
        time.sleep(seconds_until_reset)

        stats = load_json(STATS_FILE, {})
        today = datetime.now().strftime("%Y-%m-%d")
        current_month = datetime.now().strftime("%Y-%m")

        # Очистка всей статистики первого числа
        if datetime.now().day == 1:
            stats = {}
            logging.info("Первое число месяца: статистика сброшена полностью.")
        else:
            # Удаление всего, кроме сегодняшнего дня и текущего месяца
            stats = {k: v for k, v in stats.items() if k == today or k.startswith(current_month)}

        save_json(STATS_FILE, stats)
        logging.info("Обновлён stats.json")

        # Очистка логов
        try:
            with open("bot.log", "w") as f:
                f.write("")
            logging.info("Лог-файл очищен.")
        except Exception as e:
            logging.error(f"Ошибка очистки логов: {e}")

def handle_status():
    stats = load_json(STATS_FILE, {})
    today = datetime.now().strftime("%Y-%m-%d")
    month = datetime.now().strftime("%Y-%m")
    today_data = stats.get(today, {"events": 0, "total_downtime_seconds": 0})

    month_events = 0
    month_duration = 0
    for day, data in stats.items():
        if day.startswith(month):
            month_events += data["events"]
            month_duration += data["total_downtime_seconds"]

    msg = (
        f"📅 Статистика за сегодня ({today}):\n"
        f"- Переключений: {today_data['events']}\n"
        f"- Время в резерве: {format_duration(today_data['total_downtime_seconds'])}\n\n"
        f"📊 За месяц ({month}):\n"
        f"- Переключений: {month_events}\n"
        f"- Время в резерве: {format_duration(month_duration)}"
    )
    send_message(msg)

# === HTTP-SERVER FOR MWAN3 ===
class Handler(BaseHTTPRequestHandler):
    def do_POST(self):
        content = self.rfile.read(int(self.headers['Content-Length']))
        event = json.loads(content.decode())
        state = load_json(STATE_FILE, {})
        now_ts = int(time.time())

        logging.info("Получено событие: %s", event)

        if event.get("type") == "to_reserve":
            state["start_ts"] = now_ts
            save_json(STATE_FILE, state)
            send_message(f"[MWAN3] Переключение на резервный канал: {event.get('interface')}")
        elif event.get("type") == "to_main":
            start_ts = state.get("start_ts")
            if start_ts:
                duration = now_ts - start_ts
                mins = duration / 60
                update_stats(duration)
                send_message(f"[MWAN3] Возврат на основной канал.\nДлительность отключения: {format_duration(duration)}.")
                state.pop("start_ts", None)
                save_json(STATE_FILE, state)
        self.send_response(200)
        self.end_headers()

def start_bot_server():
    try:
        httpd = HTTPServer(("", PORT), Handler)
        logging.info(f"HTTP-сервер запущен на порту {PORT}")
        httpd.serve_forever()
    except OSError as e:
        logging.error(f"Ошибка запуска HTTP-сервера: {e}")

# === POLLING TELEGRAM ===
def poll_telegram():
    offset = None
    logging.info("Начат опрос Telegram на наличие сообщений")
    while True:
        try:
            url = f"https://api.telegram.org/bot{TOKEN}/getUpdates"
            params = {"timeout": 30, "offset": offset}
            resp = requests.get(url, params=params, timeout=35)
            updates = resp.json().get("result", [])
            for update in updates:
                offset = update["update_id"] + 1
                msg = update.get("message", {})
                text = msg.get("text", "")
                chat_id = str(msg.get("chat", {}).get("id", ""))
                if chat_id != CHAT_ID:
                    continue
                if text.strip() == "/status":
                    handle_status()
        except Exception as e:
            logging.error("Polling error: %s", e)
        time.sleep(1)

# === START ===
if __name__ == "__main__":
    # Инициализация файлов при первом запуске
    for file, default_data in [(STATS_FILE, {}), (STATE_FILE, {})]:
        if not os.path.exists(file):
            with open(file, "w") as f:
                json.dump(default_data, f, indent=2)
            logging.info(f"Создан файл: {file}")

    threading.Thread(target=start_bot_server, daemon=True).start()
    threading.Thread(target=daily_reset, daemon=True).start()
    threading.Thread(target=poll_telegram, daemon=True).start()
    while True:
        time.sleep(1)