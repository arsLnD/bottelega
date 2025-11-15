import os
from typing import List
import pytz
from dotenv import load_dotenv
from texts import PARTICIPATION_KEYWORD, START_TEXT

load_dotenv()

OWNERS: List[int] = []
if os.getenv("OWNERS"):
    OWNERS = [int(x.strip()) for x in os.getenv("OWNERS", "").split(",") if x.strip()]

bot_token = os.getenv("BOT_TOKEN", "")

database_url = os.getenv("DATABASE_URL", "sqlite://db.sqlite3")

timezone_info = pytz.timezone(os.getenv("TIMEZONE", "Europe/Moscow"))

start_text = START_TEXT
text_for_participation_in_comments_giveaways = PARTICIPATION_KEYWORD

DEBUG = os.getenv("DEBUG", "False").lower() == "true"