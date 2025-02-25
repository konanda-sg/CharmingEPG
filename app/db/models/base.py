# app/db/models/base.py
import os

from dotenv import load_dotenv
from tortoise import Tortoise

load_dotenv(verbose=True, override=True)
POSTGRES_USER = os.getenv("POSTGRES_USER", None)
POSTGRES_PASSWORD = os.getenv("POSTGRES_PASSWORD", None)
POSTGRES_DB = os.getenv("POSTGRES_DB", None)
POSTGRES_HOST = os.getenv("POSTGRES_HOST", None)

DATABASE_URL = f'postgres://{POSTGRES_USER}:{POSTGRES_PASSWORD}@{POSTGRES_HOST}/{POSTGRES_DB}'


async def init_database():
    await Tortoise.init(
        db_url=DATABASE_URL,
        modules={'models': ['app.db.models.epg']}
    )
    await Tortoise.generate_schemas()
