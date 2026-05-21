import re
import sqlite3
from telegram import Update
from telegram.ext import ContextTypes
from config import settings as SETTINGS

def normalize_phone_number(phone: str) -> str:
    # Remove common separators and keep only digits
    normalized = re.sub(r"[^0-9]", "", phone or "")
    return normalized

async def send_admin_notification(context: ContextTypes.DEFAULT_TYPE, text: str):
    if not SETTINGS.ADMIN_IDS:
        return
    for admin_id in SETTINGS.ADMIN_IDS:
        try:
            await context.bot.send_message(chat_id=admin_id, text=text)
        except Exception:
            pass

def get_customer_summary(cursor, customer_id, customer_phone):
    customer_name = "អតិថិជន"
    customer_phone = customer_phone or "មិនមានលេខ"
    if customer_id:
        cursor.execute("SELECT first_name, username, phone FROM users WHERE user_id = ?", (customer_id,))
        user_row = cursor.fetchone()
        if user_row:
            customer_name = user_row[0] or user_row[1] or "អតិថិជន"
            customer_phone = user_row[2] or customer_phone
    return customer_name, customer_phone

async def handle_normal_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    message = update.message
    user_id = message.from_user.id
    
    # ========================================================
    # ១. ករណីអតិថិជនចុចប៊ូតុង 📍 ផ្ញើទីតាំង (Smart Location)
    # ========================================================
    if message.location:
        lat = message.location.latitude
        lng = message.location.longitude
        google_map_url = f"https://www.google.com/maps?q={lat},{lng}"
        
        conn = sqlite3.connect("delivery_bot.db")
        cursor = conn.cursor()
        
        # ស្វែងរកការដឹកជញ្ជូនចុងក្រោយរបស់អតិថិជនម្នាក់នេះ ដើម្បីរកមើលថា Driver ណាជាអ្នកដឹក
        cursor.execute(
            "SELECT dispatch_id, driver_id, item_details, customer_phone, customer_id FROM dispatches WHERE customer_id = ? ORDER BY dispatch_id DESC LIMIT 1", 
            (user_id,)
        )
        delivery_data = cursor.fetchone()
        
        if delivery_data:
            dispatch_id, driver_id, item_details, customer_phone, customer_id = delivery_data
            customer_name, customer_phone = get_customer_summary(cursor, customer_id, customer_phone)
            
            # រក្សាទុកលីងទីតាំងចូល Database
            cursor.execute("UPDATE dispatches SET customer_location = ? WHERE dispatch_id = ?", (google_map_url, dispatch_id))
            conn.commit()
            
            # ផ្ញើសារទៅប្រាប់អតិថិជនវិញ
            await message.reply_text("📍 ✅ ទីតាំងរបស់អ្នកត្រូវបានបញ្ជូនទៅកាន់អ្នកដឹកជញ្ជូនរួចរាល់ហើយ! សូមរង់ចាំបន្តិចណា។")
            
            # 🔥 ផ្ញើទីតាំង និងលីង Map ទៅកាន់ Telegram របស់អ្នកដឹកជញ្ជូន (Driver) ភ្លាមៗអូតូ
            try:
                driver_text = (
                    f"🔔 ⚡ Driver! អតិថិជន `{customer_name}` បានផ្ញើទីតាំងមកហើយ៖\n"
                    f"📞 លេខទូរសព្ទ៖ {customer_phone}\n"
                    f"📦 អីវ៉ាន់៖ `{item_details}`\n"
                    f"📍 ផែនទី៖ {google_map_url}"
                )
                await context.bot.send_message(chat_id=driver_id, text=driver_text)
                await context.bot.send_location(chat_id=driver_id, latitude=lat, longitude=lng)
            except Exception:
                pass

            admin_text = (
                f"📍 ការផ្ញើទីតាំងថ្មីពីអតិថិជន\n"
                f"Dispatch ID: {dispatch_id}\n"
                f"Driver ID: {driver_id}\n"
                f"Customer: {customer_name}\n"
                f"Phone: {customer_phone}\n"
                f"Item: {item_details}\n"
                f"Map: {google_map_url}"
            )
            await send_admin_notification(context, admin_text)
        else:
            await message.reply_text("❌ មិនអាចផ្ញើទីតាំងបានទេ ព្រោះប្រព័ន្ធរកមិនឃើញទិន្នន័យដឹកជញ្ជូនរបស់អ្នកឡើយ។")
            admin_text = (
                f"⚠️ អតិថិជន ID {user_id} បានផ្ញើទីតាំងមក ប៉ុន្តែមិនអាចរក dispatch បាន។\n"
                f"Map: {google_map_url}"
            )
            await send_admin_notification(context, admin_text)
        
        conn.close()
        return

    # ========================================================
    # ២. ករណីអតិថិជនចុចប៊ូតុងចែករំលែកលេខទូរសព្ទ (Contact)
    # ========================================================
    if message.contact:
        contact_user_id = message.contact.user_id
        phone_number = normalize_phone_number(message.contact.phone_number)
        
        conn = sqlite3.connect("delivery_bot.db")
        cursor = conn.cursor()
        cursor.execute("UPDATE users SET phone = ? WHERE user_id = ?", (phone_number, contact_user_id))
        conn.commit()
        conn.close()
        
        await message.reply_text(
            f"✅ ជោគជ័យ! បានកត់ត្រាលេខទូរសព្ទ `{phone_number}` រួចរាល់។\n"
            "👉 សូមចុចបញ្ជា `/start` ម្តងទៀតដើម្បីចូលទៅកាន់ទំព័រដើម។"
        )
        return

    # ========================================================
    # ៣. ករណីចុចប៊ូតុងអត្ថបទនៅលើ Keyboard
    # ========================================================
    text_received = message.text.strip()
    
    # 🌟 មុខងារឆ្លាតវ័យ៖ ឆែកមើលអីវ៉ាន់បច្ចុប្បន្នសម្រាប់អតិថិជន
    if text_received == "📦 ពិនិត្យមើលអីវ៉ាន់បច្ចុប្បន្ន":
        conn = sqlite3.connect("delivery_bot.db")
        cursor = conn.cursor()
        cursor.execute("SELECT item_details, status, dispatch_date FROM dispatches WHERE customer_id = ? ORDER BY dispatch_id DESC LIMIT 1", (user_id,))
        active_delivery = cursor.fetchone()
        conn.close()
        
        if active_delivery:
            status_emoji = "🚴" if active_delivery[1] == "កំពុងដឹកជញ្ជូន" else "✅"
            await message.reply_text(
                f"📦 **ព័ត៌មានអីវ៉ាន់របស់អ្នក៖**\n"
                f" ឈ្មោះអីវ៉ាន់៖ `{active_delivery[0]}`\n"
                f" ស្ថានភាព៖ {status_emoji} `{active_delivery[1]}`\n"
                f"📅 កាលបរិច្ឆេទ៖ {active_delivery[2]}"
            )
        else:
            await message.reply_text("📦 ស្ថានភាព៖ មិនទាន់មានអីវ៉ាន់កំពុងដឹកមកជូនអ្នកឡើយទេបាទ។")
        return

    if text_received == "📞 ទាក់ទងភ្នាក់ងារផ្ទាល់":
        await message.reply_text("📞 លោកអ្នកអាចធ្វើការទាក់ទងទៅកាន់ផ្នែកសេវាអតិថិជនតាមរយៈលេខទូរសព្ទ៖ `012 345 678` ឬតេតាម Telegram @GS_Support បាទ។")
        return

    # ========================================================
    # ៤. ករណី Driver បញ្ចូលទិន្នន័យ (Format: លេខទូរសព្ទ - ឈ្មោះអីវ៉ាន់)
    # ========================================================
    if "-" in text_received:
        parts = text_received.split("-", 1)
        raw_phone = parts[0].strip()
        customer_phone = normalize_phone_number(raw_phone)
        item_details = parts[1].strip()
        
        if not customer_phone or len(customer_phone) < 8 or len(customer_phone) > 15:
            await message.reply_text(
                "❌ ទម្រង់លេខទូរសព្ទមិនត្រូវទេ! សូមវាយម្តងទៀតក្នុងទម្រង់ដូចជា: \n"
                "012345678 - ឈ្មោះអីវ៉ាន់ \n"
                "+855 71 448 4085 - ឈ្មោះអីវ៉ាន់ \n"
                "071448085 - ឈ្មោះអីវ៉ាន់"
            )
            return
            
        conn = sqlite3.connect("delivery_bot.db")
        cursor = conn.cursor()
        
        # 🌟 មុខងារឆ្លាតវ័យ៖ ស្វែងរកលេខទូរសព្ទបែបទំនើប (ឆែកទាំងទម្រង់មាន 0 និងមាន 855)
        phone_variant1 = customer_phone
        phone_variant2 = f"855{customer_phone[1:]}" if customer_phone.startswith("0") else customer_phone
        phone_variant3 = f"0{customer_phone[3:]}" if customer_phone.startswith("855") else customer_phone
        
        cursor.execute(
            "SELECT user_id, first_name FROM users WHERE phone IN (?, ?, ?)", 
            (phone_variant1, phone_variant2, phone_variant3)
        )
        customer_data = cursor.fetchone()
        
        if customer_data:
            cust_id, cust_name = customer_data
            cursor.execute(
                "INSERT INTO dispatches (driver_id, customer_phone, customer_id, item_details) VALUES (?, ?, ?, ?)",
                (user_id, customer_phone, cust_id, item_details)
            )
            conn.commit()
            
            await message.reply_text(f"✅ អតិថិជនចាស់ឈ្មោះ {cust_name} មានក្នុងប្រព័ន្ធ!\n🚀 ប្រព័ន្ធបានផ្ញើសារដំណឹងទៅគាត់អូតូហើយ។")
            
            try:
                notify_text = (
                    f"🔔 ជំរាបសួរ លោក/អ្នក {cust_name}!\n"
                    f"📦 អីវ៉ាន់របស់អ្នកគឺ `{item_details}` កំពុងត្រូវបានដឹកជញ្ជូនមកហើយ។\n\n"
                    f"👇 សូមចុចប៊ូតុងខាងក្រោមដើម្បីផ្ញើទីតាំង 📍 ទៅកាន់អ្នកដឹកជញ្ជូនបាទ។"
                )
                await context.bot.send_message(chat_id=cust_id, text=notify_text)
            except Exception:
                await message.reply_text("⚠️ ប្រព័ន្ធមិនអាចផ្ញើសារទៅកាន់អតិថិជនបានទេ ព្រោះគាត់អាចនឹងបិទ Bot ចោល។")

            admin_text = (
                f"✅ ការបង្កើត dispatch ថ្មី\n"
                f"Driver ID: {user_id}\n"
                f"Customer: {cust_name}\n"
                f"Phone: {customer_phone}\n"
                f"Item: {item_details}\n"
                f"Status: អតិថិជនចាស់"
            )
            await send_admin_notification(context, admin_text)
        else:
            cursor.execute(
                "INSERT INTO dispatches (driver_id, customer_phone, item_details) VALUES (?, ?, ?)",
                (user_id, customer_phone, item_details)
            )
            conn.commit()
            
            dispatch_id = cursor.lastrowid
            bot_username = (await context.bot.get_me()).username
            invite_link = f"https://t.me/{bot_username}?start=dispatch_{dispatch_id}"
            
            response_msg = (
                f"🔍 រកមិនឃើញលេខទូរសព្ទនេះទេ (អតិថិជនថ្មី)!\n\n"
                f"👉🔗 សូមផ្ញើ Link នេះទៅកាន់គាត់ ដើម្បីឱ្យគាត់ចុច Start និងមើលព័ត៌មាន៖\n\n"
                f"{invite_link}"
            )
            await message.reply_text(response_msg)

            admin_text = (
                f"✅ ការបង្កើត dispatch ថ្មី\n"
                f"Driver ID: {user_id}\n"
                f"Customer: អតិថិជនថ្មី\n"
                f"Phone: {customer_phone}\n"
                f"Item: {item_details}\n"
                f"Status: អតិថិជនថ្មី\n"
                f"Invite Link: {invite_link}"
            )
            await send_admin_notification(context, admin_text)
            
        conn.close()
        return

    # សារទូទៅ
    await message.reply_text("💡 ដើម្បីបញ្ចូលអីវ៉ាន់ថ្មី សូមវាយទម្រង់៖ `លេខទូរសព្ទ - ឈ្មោះអីវ៉ាន់`")