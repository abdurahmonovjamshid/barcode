
import json
import traceback
import telebot
from django.http import HttpResponse
from django.views.decorators.csrf import csrf_exempt
from conf.settings import HOST, TELEGRAM_BOT_TOKEN

from .models import TgUser
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
        response_message = f"Salom, {message.from_user.full_name}!😊 \nSalid cable barkodlarni qayta chiqarish botiga xush kelibbsiz"
        bot.send_photo(chat_id=message.chat.id, photo='https://avatars.mds.yandex.net/get-altay/13322921/2a000001939a62b04c38cd1dea61ddc772ef/XXL_height',
                       caption=response_message)
    except Exception as e:
        print(e)

bot.set_webhook(url="https://"+HOST+"/webhook/")
