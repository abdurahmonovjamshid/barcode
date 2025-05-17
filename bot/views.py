
import json
import traceback
import telebot
import re
import os

from django.http import HttpResponse
from django.views.decorators.csrf import csrf_exempt
from conf.settings import HOST, TELEGRAM_BOT_TOKEN
from PyPDF2 import PdfMerger
from openpyxl import Workbook

from .models import TgUser
from bot.tools import generate_pdf, generate_custom_label, generate_custom_label_page
from conf.settings import ADMINS, GROUPS, BASE_DIR

from reportlab.pdfgen import canvas
from reportlab.lib.units import cm
from io import BytesIO

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
# Store temporary uploaded PDFs per user ID
user_pdf_queue = {}

COMBINE_DIR = os.path.join(BASE_DIR, "bot", "combine_temp")
os.makedirs(COMBINE_DIR, exist_ok=True)
@bot.message_handler(commands=['combine'])
def start_combine(message):
    user_id = message.from_user.id
    user_pdf_queue[user_id] = []
    bot.reply_to(message, "PDF birlashtirish boshlandi. PDF fayllarni yuboring. Yakunlash uchun /finish yuboring.")

@bot.message_handler(commands=['finish'])
def finish_combine(message):
    user_id = message.from_user.id
    if user_id not in user_pdf_queue or not user_pdf_queue[user_id]:
        bot.reply_to(message, "Hech qanday PDF topilmadi. Avval /combine yuboring va PDF fayllarni yuboring.")
        return

    combined_pdf_path = os.path.join(COMBINE_DIR, f"combined_{user_id}.pdf")

    try:
        merger = PdfMerger()
        for file_path in user_pdf_queue[user_id]:
            merger.append(file_path)
        merger.write(combined_pdf_path)
        merger.close()

        with open(combined_pdf_path, "rb") as f:
            bot.send_document(message.chat.id, f, visible_file_name="combined.pdf")
    except Exception as e:
        bot.reply_to(message, "❌ PDF birlashtirishda xatolik yuz berdi.")
        print("Merge error:", e)
    finally:
        # Clean up
        for path in user_pdf_queue[user_id]:
            os.remove(path)
        if os.path.exists(combined_pdf_path):
            os.remove(combined_pdf_path)
        user_pdf_queue.pop(user_id, None)

@bot.message_handler(content_types=['document'])
def handle_pdf_upload(message):
    user_id = message.from_user.id
    file_info = bot.get_file(message.document.file_id)

    if message.document.mime_type != 'application/pdf':
        bot.reply_to(message, "Faqat PDF fayllarni yuboring.")
        return

    if user_id not in user_pdf_queue:
        return  # ignore unless user is in combine mode

    file = bot.download_file(file_info.file_path)
    local_path = os.path.join(COMBINE_DIR, f"{user_id}_{len(user_pdf_queue[user_id])}.pdf")

    with open(local_path, 'wb') as f:
        f.write(file)

    user_pdf_queue[user_id].append(local_path)
    bot.reply_to(message, f"✅ Fayl qabul qilindi. Hozircha: {len(user_pdf_queue[user_id])} ta fayl.")


from collections import defaultdict

custom_label_texts = defaultdict(list)

@bot.message_handler(commands=['boshlash'])
def start_custom_label_collect(message):
    user_id = message.from_user.id
    custom_label_texts[user_id] = []
    bot.reply_to(message, "✅ Yig‘ish boshlandi! Format: `1234-56`\nYakunlash uchun /tugatish yuboring.")


@bot.message_handler(commands=['tugatish'])
def finish_custom_label_pdf_and_excel(message):
    user_id = message.from_user.id
    texts = custom_label_texts.get(user_id)

    if not texts:
        bot.reply_to(message, "🚫 Hech narsa topilmadi. Avval /boshlash yuboring.")
        return

    try:
        # ✅ 1. Generate multi-page PDF
        label_width = 6 * cm
        label_height = 2.8 * cm
        pdf_output = BytesIO()
        c = canvas.Canvas(pdf_output, pagesize=(label_width, label_height))

        for label_text in texts:
            generate_custom_label_page(c, label_text)
            c.showPage()
        c.save()
        pdf_output.seek(0)

        # ✅ 2. Generate Excel
        wb = Workbook()
        ws = wb.active
        ws.title = "Etiketlar"
        ws.append(["Code", "Razmer"])  # Header row

        for item in texts:
            if "-" in item:
                left, right = item.strip().split("-")
                if left.isdigit() and right.isdigit():
                    ws.append([left, right])

        excel_output = BytesIO()
        wb.save(excel_output)
        excel_output.seek(0)

        # ✅ 3. Send both files
        bot.send_document(message.chat.id, pdf_output, visible_file_name="combined_labels.pdf", caption="✅ PDF tayyor!")
        bot.send_document(message.chat.id, excel_output, visible_file_name="etiketlar.xlsx", caption="📄 Excel tayyor!")

    except Exception as e:
        bot.reply_to(message, "🚫 PDF yoki Excel yaratishda xatolik yuz berdi.")
        print("❌ Error in /tugatish:", e)
    finally:
        custom_label_texts.pop(user_id, None)


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
                user_id = message.from_user.id
                if user_id in custom_label_texts:
                    custom_label_texts[user_id].append(content.strip())
                    bot.reply_to(message, f"✅ Qabul qilindi. Jami: {len(custom_label_texts[user_id])} ta.")
                else:
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
