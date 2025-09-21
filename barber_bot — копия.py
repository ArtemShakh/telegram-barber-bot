import google.generativeai as genai
from telegram import Update, InlineKeyboardMarkup, InlineKeyboardButton
from telegram.ext import ApplicationBuilder, CommandHandler, MessageHandler, CallbackQueryHandler, filters, ContextTypes
import os
from datetime import datetime, timedelta

# ТВОЙ API-КЛЮЧ GEMINI (для этого бота не нужен, но пусть будет)
genai.configure(api_key="")

# ТВОЙ ТОКЕН БОТА ИЗ BOTFATHER
BOT_TOKEN = ""

# ID ВЛАДЕЛЬЦА ДЛЯ АДМИН-ПАНЕЛИ. Узнать можно через @userinfobot
OWNER_ID = 

# Список доступного времени для бронирования
AVAILABLE_TIMES = ["10:00", "10:20", "10:40", "11:00", "11:20", "11:40"]

# Создаем словарь для хранения состояния каждого пользователя
user_state = {}

# Команда /start - запускает процесс записи
async def start_booking(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    user_state[user_id] = {"step": "name"}
    await update.message.reply_text("Привет! Я бот для записи в парикмахерскую. Как тебя зовут?")

# Обработчик ответов пользователя
async def handle_booking_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    message_text = update.message.text
    
    if user_id not in user_state:
        await update.message.reply_text("Чтобы записаться, отправь команду /start")
        return

    current_state = user_state[user_id]

    if current_state["step"] == "name":
        current_state["name"] = message_text
        current_state["step"] = "service"
        keyboard = [
            [InlineKeyboardButton("Стрижка", callback_data="Стрижка")],
            [InlineKeyboardButton("Окрашивание", callback_data="Окрашивание")],
            [InlineKeyboardButton("Маникюр", callback_data="Маникюр")]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        await update.message.reply_text("Отлично, теперь выбери услугу:", reply_markup=reply_markup)

    elif current_state["step"] == "date":
        current_state["date"] = message_text
        current_state["step"] = "time"
        
        keyboard = [[InlineKeyboardButton(time, callback_data=time)] for time in AVAILABLE_TIMES]
        reply_markup = InlineKeyboardMarkup(keyboard)
        await update.message.reply_text("Теперь выбери удобное время:", reply_markup=reply_markup)

# Обработчик нажатия на кнопки
async def button_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    # ИСПРАВЛЕНИЕ: Мы берем ID пользователя из query.from_user, а не effective_user
    user_id = query.from_user.id
    
    if user_id not in user_state:
        await query.edit_message_text("Чтобы записаться, отправь команду /start")
        return

    current_state = user_state[user_id]

    if current_state["step"] == "service":
        current_state["service"] = query.data
        current_state["step"] = "date"
        await query.edit_message_text(f"Ты выбрал: {query.data}. Теперь введи дату записи в формате ГГГГ-ММ-ДД, например, 2025-09-25.")

    elif current_state["step"] == "time":
        current_state["time"] = query.data
        
        with open("records.txt", "a") as file:
            record_line = f"Имя: {current_state['name']}, Услуга: {current_state['service']}, Дата: {current_state['date']}, Время: {current_state['time']}\n"
            file.write(record_line)

        await query.edit_message_text("Готово! Ты успешно записан. Чтобы начать новую запись, отправь /start.")
        
        del user_state[user_id]

# Команда для админа, чтобы посмотреть записи
async def show_records(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id != OWNER_ID:
        await update.message.reply_text("У тебя нет прав для использования этой команды.")
        return
        
    try:
        with open("records.txt", "r") as file:
            records = file.read()
        await update.message.reply_text("Список записей:\n" + records)
    except FileNotFoundError:
        await update.message.reply_text("Файл записей не найден.")

# Команда для удаления старых записей
async def clean_records(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id != OWNER_ID:
        await update.message.reply_text("У тебя нет прав для использования этой команды.")
        return

    today = datetime.now()
    ten_days_ago = today - timedelta(days=10)
    
    kept_records = []
    try:
        with open("records.txt", "r") as file:
            for line in file:
                try:
                    date_str = line.split(", Дата: ")[1].split(",")[0].strip()
                    record_date = datetime.strptime(date_str, "%Y-%m-%d")
                    if record_date >= ten_days_ago:
                        kept_records.append(line)
                except (IndexError, ValueError):
                    kept_records.append(line)

        with open("records.txt", "w") as file:
            file.writelines(kept_records)
            
        await update.message.reply_text("Старые записи успешно удалены.")

    except FileNotFoundError:
        await update.message.reply_text("Файл записей не найден.")

def main():
    print("Бот для парикмахерской запущен...")
    app = ApplicationBuilder().token(BOT_TOKEN).build()
    
    app.add_handler(CommandHandler("start", start_booking))
    app.add_handler(CommandHandler("records", show_records)) 
    app.add_handler(CommandHandler("clean", clean_records)) 
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_booking_message))
    app.add_handler(CallbackQueryHandler(button_handler))
    
    app.run_polling()

if __name__ == "__main__":
    main()