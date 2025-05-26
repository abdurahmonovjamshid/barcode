import os
import requests
from dotenv import load_dotenv

load_dotenv()

TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
GROUPS = os.getenv("NOTIFY", "").split(",")

# Define users to tag (user_id: display name)
TAGGED_USERS = {
    7757735418: "Jamshid",
    7782070732: "Qudratilla aka",
    475676143: "Elyor aka"
}

def format_mentions(user_map):
    return '\n'.join([f'<a href="tg://user?id={uid}">{name}</a>' for uid, name in user_map.items()])

MENTIONS = format_mentions(TAGGED_USERS)

MESSAGE = f"""{MENTIONS}

Sotuv bo'limi kunlik ishlari bajarildimi:?
- Mijozlar to'lagan pullarni SAP da ayirish;
- Kunlik Otgruzkalarni Prodajaga olish;
- Servreda ishni tugatgan barcha ochiq file lar va dasturlarni yopib ketish;
- Faktura guruhiga tushgan shot fakturalarni tekshirib like bosish."""

def send_message(chat_id, text):
    url = f"https://api.telegram.org/bot{TOKEN}/sendMessage"
    data = {
        "chat_id": chat_id,
        "text": text,
        "parse_mode": "HTML"
    }
    try:
        r = requests.post(url, data=data)
        if r.status_code != 200:
            print(f"Failed to send to {chat_id}: {r.text}")
    except Exception as e:
        print(f"Error sending to {chat_id}: {e}")

if __name__ == "__main__":
    for group_id in GROUPS:
        group_id = group_id.strip()
        if group_id:
            send_message(group_id, MESSAGE)
