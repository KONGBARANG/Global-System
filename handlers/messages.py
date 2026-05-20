import sqlite3
from telegram import Update
from telegram.ext import ContextTypes

async def handle_normal_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    message = update.message
    user_id = message.from_user.id
    
    # ========================================================
    # ករណីទី ១៖ អតិថិជនចុចប៊ូតុងចែករំលែកលេខទូរសព្ទ (Contact)
    # ========================================================
    if message.contact:
        contact_user_id = message.contact.user_id
        phone_number = message.contact.phone_number
        
        # សម្អាតលេខទូរសព្ទឱ្យមានទម្រង់ស្អាត (លុបសញ្ញា + បើមាន)
        phone_number = phone_number.replace("+", "")
        
        conn = sqlite3.connect("delivery_bot.db")
        cursor = conn.cursor()
        cursor.execute("UPDATE users SET phone = ? WHERE user_id = ?", (phone_number, contact_user_id))
        conn.commit()
        conn.close()
        
        await message.reply_text(
            f"✅ ជោគជ័យ! ប្រព័ន្ធបានកត់ត្រាលេខទូរសព្ទ `{phone_number}` របស់អ្នករួចរាល់ហើយ។\n"
            "👉 សូមចុចចុចបញ្ជា `/start` ម្តងទៀតដើម្បីចូលទៅកាន់ទំព័រដើម។"
        )
        return

    # ========================================================
    # ករណីទី ២៖ សារជាអក្សរធម្មតា (រួមទាំងការបញ្ចូលអីវ៉ាន់ពី Driver)
    # ========================================================
    text_received = message.text.strip()
    
    # ឆែកមើលថាតើសារនោះមានសញ្ញាដក " - " សម្រាប់បញ្ចូលអីវ៉ាន់មែនឬទេ (ឧទាហរណ៍៖ 012345678 - ខោអាវ)
    if "-" in text_received:
        # បំបែកលេខទូរសព្ទ និងឈ្មោះអីវ៉ាន់ដាច់ពីគ្នា
        parts = text_received.split("-", 1)
        customer_phone = parts[0].strip().replace("+", "") # លុបចោលចន្លោះទទេ និងសញ្ញាបូក
        item_details = parts[1].strip()
        
        # ឆែកមើលថាលេខទូរសព្ទដែល Driver វាយបញ្ចូល មានលេខត្រឹមត្រូវទេ (ការពារវាយខុស)
        if not customer_phone.isdigit() or len(customer_phone) < 8:
            await message.reply_text("❌ ទម្រង់លេខទូរសព្ទមិនត្រឹមត្រូវទេ! សូមវាយម្តងទៀត (ឧទាហរណ៍៖ 012345678 - ឈ្មោះអីវ៉ាន់)")
            return
            
        conn = sqlite3.connect("delivery_bot.db")
        cursor = conn.cursor()
        
        # ១. ឆែកមើលក្នុង Database ថាតើលេខទូរសព្ទនេះជាអតិថិជនចាស់ (Old User) មែនឬទេ
        cursor.execute("SELECT user_id, first_name FROM users WHERE phone = ? OR phone = ?", (customer_phone, f"855{customer_phone[1:]}" if customer_phone.startswith("0") else customer_phone))
        customer_data = cursor.fetchone()
        
        if customer_data:
            # --------------------------------------------------------
            # 🎉 ករណីអតិថិជនចាស់ (Old User) -> រកឃើញ Telegram ID
            # --------------------------------------------------------
            cust_id = customer_data[0]
            cust_name = customer_data[1]
            
            # កត់ត្រាចូលក្នុងប្រព័ន្ធដឹកជញ្ជូន (Dispatches Table)
            cursor.execute(
                "INSERT INTO dispatches (driver_id, customer_phone, customer_id, item_details) VALUES (?, ?, ?, ?)",
                (user_id, customer_phone, cust_id, item_details)
            )
            conn.commit()
            
            # ផ្ញើសារទៅប្រាប់ Driver វិញ
            await message.reply_text(f"✅ អតិថិជនចាស់ឈ្មោះ {cust_name} មានក្នុងប្រព័ន្ធស្រាប់!\n🚀 ប្រព័ន្ធបានផ្ញើសារដំណឹងទៅកាន់ Telegram របស់គាត់អូតូភ្លាមៗហើយ។")
            
            # 🔥 ផ្ញើសារអូតូទៅកាន់ Telegram របស់អតិថិជនម្នាក់នោះដោយផ្ទាល់ (Direct Notification)
            try:
                bot_username = (await context.bot.get_me()).username
                notify_text = (
                    f"🔔 ជំរាបសួរ លោក/អ្នក {cust_name}!\n"
                    f"📦 អីវ៉ាន់របស់អ្នកគឺ `{item_details}` កំពុងត្រូវបានដឹកជញ្ជូនមកហើយ។\n\n"
                    f"👉 សូមចុចចុចបញ្ជា `/start` ដើម្បីពិនិត្យមើលព័ត៌មានលម្អិត ឬបោះទីតាំង (Location) ទៅកាន់អ្នកដឹកជញ្ជូនបាទ។"
                )
                await context.bot.send_message(chat_id=cust_id, text=notify_text)
            except Exception as e:
                # ករណីផ្ញើទៅមិនចូល (ក្រែងលោគាត់ Block Bot ចោលវិញ)
                await message.reply_text("⚠️ ប្រព័ន្ធមិនអាចផ្ញើសារទៅកាន់អតិថិជនបានទេ ព្រោះគាត់អាចនឹងបិទ (Block) Bot ចោល។")
                
        else:
            # --------------------------------------------------------
            # 🔍 ករណីអតិថិជនថ្មី (New User) -> មិនទាន់មាន Telegram ID
            # --------------------------------------------------------
            # កត់ត្រាទុកក្នុងប្រព័ន្ធដឹកជញ្ជូនមុន (customer_id នៅឡើយជា NULL)
            cursor.execute(
                "INSERT INTO dispatches (driver_id, customer_phone, item_details) VALUES (?, ?, ?)",
                (user_id, customer_phone, item_details)
            )
            conn.commit()
            
            # យក ID ចុងក្រោយនៃការដឹកជញ្ជូននេះ ដើម្បីធ្វើជា Link ពិសេស
            dispatch_id = cursor.lastrowid
            bot_username = (await context.bot.get_me()).username
            
            # បង្កើតលីងផ្ដាច់មុខសម្រាប់អីវ៉ាន់មួយនេះ (Deep Linking)
            invite_link = f"https://t.me/{bot_username}?start=dispatch_{dispatch_id}"
            
            response_msg = (
                f"🔍 រកមិនឃើញលេខទូរសព្ទអតិថិជននេះក្នុងប្រព័ន្ធទេ (អតិថិជនថ្មី)!\n\n"
                f"📋 ព័ត៌មានអីវ៉ាន់ត្រូវបានកត់ត្រាទុកក្នុងប្រព័ន្ធរួចរាល់។\n"
                f"💬 លោកគ្រាន់តែផ្ញើ Link ខាងក្រោមនេះទៅកាន់អតិថិជន (តាមរយៈ SMS, Messenger, ឬ Telegram របស់គាត់) "
                f"ដើម្បីឱ្យគាត់ចុច Start ចុះឈ្មោះ និងមើលព័ត៌មានដឹកជញ្ជូន៖\n\n"
                f"👉🔗 {invite_link}"
            )
            await message.reply_text(response_msg)
            
        conn.close()
        return

    # សារសាកសួរធម្មតា
    text_clean = text_received.lower()
    if "សួស្តី" in text_clean or "hello" in text_clean:
        await message.reply_text("សួស្តីបាទ! ខ្ញុំជា Bot ជំនួយការដឹកជញ្ជូន GS មានអ្វីឱ្យខ្ញុំជួយដែរទេ? 😊")
    else:
        await message.reply_text("💡 ដើម្បីបញ្ចូលអីវ៉ាន់ថ្មី សូមវាយទម្រង់៖ `លេខទូរសព្ទ - ឈ្មោះអីវ៉ាន់`")