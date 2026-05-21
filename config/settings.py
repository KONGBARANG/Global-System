import os
from dotenv import load_dotenv

# ផ្ទុកទិន្នន័យពី .env ចូលទៅក្នុង System Environment
load_dotenv()

# ទាញយក Token មកប្រើ
BOT_TOKEN = os.getenv("BOT_TOKEN")
ADMIN_IDS = [int(x.strip()) for x in os.getenv("ADMIN_IDS", "").split(",") if x.strip().isdigit()]

if not BOT_TOKEN:
    raise ValueError("សូមពិនិត្យមើល! អ្នកមិនទាន់បានដាក់ BOT_TOKEN នៅក្នុង .env ទេ ឬរកវាលែងឃើញ។")