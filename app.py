import os
from telegram import Update
import logging
from datetime import datetime
from telegram.ext import Application, ApplicationBuilder, CommandHandler, ContextTypes, CallbackContext
from api import get_error_count, get_errors

count = 0
e2_count = 0

CHANNEL_ID =  os.environ.get('CHANNEL_ID')
BOT_TOKEN = os.environ.get('BOT_TOKEN')
WEBHOOK_URL= os.environ.get('WEBHOOK_URL')
PORT = int(os.environ.get('PORT', '8443'))
print(PORT)

# Enable logging
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', level=logging.INFO
)

logger = logging.getLogger(__name__)

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    template = f'Hola, {update.effective_user.first_name}\n'
    template+= "Escribe el comando: /set <minutos> para crear el recordatorio"
    await update.message.reply_text(template)

async def summary(context: ContextTypes.DEFAULT_TYPE) -> None:
    """Send the summary message."""
    global count

    job = context.job
    new_count = get_error_count().get('count') 
    if new_count != count:
        e1 = get_errors(1)
        e2 = get_errors(2)
        e3 = get_errors(3)
        template = f"⚠️ ¡Se han detectado {new_count} errores! ⚠️ Por favor revise \n\n"
        template+= f"{len(e1)} errores de conexión.\n\n"
        template+= f"{len(e2)} errores de envío.\n\n"
        template+= f"{len(e3)} super bancas con números negativos.\n\n"

        await context.bot.send_message(job.chat_id, text=template)
        count = new_count

async def errors(context: ContextTypes.DEFAULT_TYPE) -> None:
    """Nunca se envió (Error de la aplicación)"""
    global e2_count

    job = context.job
    count = len(get_errors(2))
    if (count > 0) and (count != e2_count):
        e2_count = count
        template = "¡Se han detectado {count} errores de envío! Por favor revise\n\n"
        for row in get_errors(2):
            template+=f"*{row}*\n\n"
        template = template.replace("-","\-").replace(".", "\.")
        await context.bot.send_message(job.chat_id, text=template, parse_mode='MarkdownV2')

async def reporte_negativos(context: ContextTypes.DEFAULT_TYPE) -> None:
    job = context.job

    template = "REPORTE DE NEGATIVOS\n\n"
    template+= datetime.today().strftime('%Y-%m-%d') + "\n"

    for row in get_errors(3):
        template+=f"*{row.get('nombre')}*\n"
        template+=f"*ID Super Banca*: {row.get('id_super_banca')}\n"
        template+=f"*Venta:* {row.get('venta')}\n"
        template+=f"*Total:* {row.get('total')}\n\n"
    template = template.replace("-","\-").replace(".", "\.")
    await context.bot.send_message(job.chat_id, text=template, parse_mode='MarkdownV2')

async def set_timer(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Add a job to the queue."""
    chat_id = update.effective_message.chat_id
    try:
        # args[0] should contain the time for the timer in minutes
        due = float(context.args[0]) * 60 
        if due < 0:
            await update.effective_message.reply_text("Sorry we can not go back to future!")
            return

        job_removed = remove_job_if_exists(str(chat_id), context)
        context.job_queue.run_repeating(summary, interval=due, chat_id=chat_id, name=str(chat_id), data=due)
        context.job_queue.run_repeating(errors, interval=due, chat_id=chat_id, name=str(chat_id), data=due)
        context.job_queue.run_repeating(reporte_negativos, interval=600, chat_id=chat_id, name=str(chat_id))

        text = "Timer successfully set!"
        if job_removed:
            text += " Old one was removed."
        await update.effective_message.reply_text(text)

    except (IndexError, ValueError):
        await update.effective_message.reply_text("Escribe el comando: /set <minutos>")

async def unset(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Remove the job if the user changed their mind."""
    chat_id = update.message.chat_id
    update.message.reply_text("Stopping automatic messages...")
    job_removed = remove_job_if_exists(str(chat_id), context)
    text = "Timer successfully cancelled!" if job_removed else "You have no active timer."
    await update.message.reply_text(text)

def remove_job_if_exists(name: str, context: ContextTypes.DEFAULT_TYPE) -> bool:
    """Remove job with given name. Returns whether job was removed."""
    current_jobs = context.job_queue.get_jobs_by_name(name)
    if not current_jobs:
        return False
    for job in current_jobs:
        job.schedule_removal()
    return True

def main():
    app = Application.builder().token(BOT_TOKEN).build()

    app.add_handler(CommandHandler(["start", "help"], start))
    app.add_handler(CommandHandler("set", set_timer))
    app.add_handler(CommandHandler("stop", unset))

    # Run the bot until the user presses Ctrl-C
    app.run_polling(allowed_updates=Update.ALL_TYPES)

if __name__ == '__main__':
    main()