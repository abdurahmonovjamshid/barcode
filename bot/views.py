
import json
import traceback
import telebot
import re

from django.http import HttpResponse
from django.views.decorators.csrf import csrf_exempt
from conf.settings import HOST, TELEGRAM_BOT_TOKEN

from .models import TgUser
from bot.tools import generate_pdf, generate_custom_label
from conf.settings import ADMINS, GROUPS

bot = telebot.TeleBot(TELEGRAM_BOT_TOKEN, threaded=False)

@csrf_exempt
def telegram_webhook(request):
    try:
        if request.method == 'POST':
            update_data = request.body.decode('utf-8')
            update_json = json.loads(update_data)
            update = telebot.types.Update.de_json(update_json)

            if update.message:
                tg_user = update.message.from_user
                telegram_id = tg_user.id
                first_name = tg_user.first_name
                last_name = tg_user.last_name
                username = tg_user.username
                is_bot = tg_user.is_bot
                language_code = tg_user.language_code

                deleted = False

                tg_user_instance, _ = TgUser.objects.update_or_create(
                    telegram_id=telegram_id,
                    defaults={
                        'first_name': first_name,
                        'last_name': last_name,
                        'username': username,
                        'is_bot': is_bot,
                        'language_code': language_code,
                        'deleted': deleted,
                    }
                )

            try:
                if update.my_chat_member.new_chat_member.status == 'kicked':
                    telegram_id = update.my_chat_member.from_user.id
                    user = TgUser.objects.get(telegram_id=telegram_id)
                    user.deleted = True
                    user.save()
            except:
                pass

            bot.process_new_updates(
                [telebot.types.Update.de_json(request.body.decode("utf-8"))])

        return HttpResponse("ok")
    except Exception as e:
        traceback.print_tb(e.__traceback__)
        return HttpResponse("error")


@bot.message_handler(commands=['start'])
def start_handler(message):
    try:
        response_message = f"Salom, {message.from_user.full_name}! 😊\nSalid kabel barkodlarini qayta chiqarish botiga xush kelibsiz."

        if message.chat.type == 'private':
            # Send welcome message in private
            bot.send_photo(
                chat_id=message.chat.id,
                photo='https://avatars.mds.yandex.net/get-altay/13322921/2a000001939a62b04c38cd1dea61ddc772ef/XXL_height',
                caption=response_message
            )
        else:
            # Send to group: mention user and group name
            group_message = (
                f"👤 User: {message.from_user.full_name} (ID: {message.from_user.id})\n"
                f"💬 Guruh: {message.chat.title} (ID: {message.chat.id})"
            )
            bot.send_message(chat_id=message.chat.id, text=group_message)
    except Exception as e:
        print("⚠️ Error in /start handler:")
        print(e)

# First pattern (full product info)
pattern = r'code\s*:\s*(\S+)\s+metr\s*:\s*(\S+)\s+kg\s*:\s*(\S+)\s+barkod\s*:\s*(\S+)'

# Second pattern (short code format like 1234-56)
pattern2 = r'^\d{4}-\d{2}$'  # matches exactly 4 digits, dash, 2 digits

@bot.message_handler(content_types=['text', 'media', 'photo'])
def handle_message(message):
    try:
        if str(message.from_user.id) in ADMINS or str(message.chat.id) in GROUPS:
            content = message.caption if message.caption else message.text
            if not content:
                return

            match = re.search(pattern, content, re.IGNORECASE)
            match2 = re.search(pattern2, content.strip())

            if match:
                code, metr, kg, barkod = match.groups()
                pdf = generate_pdf(code, metr, kg, barkod)
                bot.send_document(message.chat.id, pdf, visible_file_name=f"{code}_etiket.pdf")

            elif match2:
                pdf = generate_custom_label(content.strip())
                bot.send_document(message.chat.id, pdf, visible_file_name="label.pdf")

            else:
                if message.chat.type == 'private':
                    bot.reply_to(
                        message,
                        "Format noto‘g‘ri. Iltimos, quyidagicha yuboring:\n\n"
                        "code : GPC1569\nmetr : 150\nkg : 7.00\nbarkod : 100016689\n\n"
                        "yoki\n\n1234-56"
                    )
        else:
            bot.reply_to(message, "Admin emassiz")

    except Exception as e:
        print("⚠️ Exception occurred in handle_message:")
        import traceback
        traceback.print_exc()


bot.set_webhook(url="https://"+HOST+"/webhook/")
