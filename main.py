import os
import asyncio
from dotenv import load_dotenv
from telegram.ext import Application, CommandHandler, MessageHandler, filters
from handlers.commands import start_command, help_command
from handlers.messages import handle_normal_message

# 🔥 បន្ថែមបណ្ណាល័យ aiohttp ដើម្បីបង្កើត Web Server សម្រាប់បោក Render
from aiohttp import web

load_dotenv()
BOT_TOKEN = os.getenv("BOT_TOKEN")

# មុខងារស្វាគមន៍ពេល Render មកពិនិត្យមើល Port (Health Check)
async def handle_health_check(request):
    return web.Response(text="Bot is running successfully!")

async def main():
    # ----------------------------------------------------
    # ១. បង្កើត និងរត់ Web Server ស្ងាត់ៗនៅពីក្រោយខ្នង
    # ----------------------------------------------------
    app_web = web.Application()
    app_web.router.add_get('/', handle_health_check)
    
    # ចាប់យក Port ពី Render (Render ផ្តល់ឱ្យតាមរយៈ Environment Variable ឈ្មោះ PORT)
    port = int(os.environ.get("PORT", 8080))
    runner = web.AppRunner(app_web)
    await runner.setup()
    site = web.TCPSite(runner, '0.0.0.0', port)
    
    # បើកដំណើរការ Web Server ចោល
    asyncio.create_task(site.start())
    print(f"📡 Fake Web Server started on port {port}")

    # ----------------------------------------------------
    # ២. បើកដំណើរការ Telegram Bot ទម្រង់ Polling ធម្មតា
    # ----------------------------------------------------
    print("🤖 Telegram Bot is starting...")
    application = Application.builder().token(BOT_TOKEN).build()

    # បន្ថែម Handlers ដូចមុន
    application.add_handler(CommandHandler("start", start_command))
    application.add_handler(CommandHandler("help", help_command))
    application.add_handler(MessageHandler(filters.TEXT | filters.CONTACT | filters.LOCATION, handle_normal_message))

    # រត់ Bot រហូត
    async with application:
        await application.initialize()
        await application.start()
        await application.updater.start_polling()
        
        # រក្សាឱ្យកម្មវិធីរត់ទាំងពីរព្រមគ្នាដោយមិនបិទ
        while True:
            await asyncio.sleep(3600)

if __name__ == "__main__":
    # រត់មុខងារ main តាមទម្រង់ Asyncio
    asyncio.run(main())