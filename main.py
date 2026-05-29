from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel
import asyncpg
import os
import asyncio
from dotenv import load_dotenv
from aiogram import Bot, Dispatcher, types
from aiogram.filters import Command

load_dotenv()

DATABASE_URL = os.getenv("DATABASE_URL")
BOT_TOKEN = os.getenv("BOT_TOKEN")

app = FastAPI()
bot = Bot(token=BOT_TOKEN)
dp = Dispatcher()
pool = None

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

async def init_db():
    global pool
    pool = await asyncpg.create_pool(DATABASE_URL, min_size=1, max_size=5)
    async with pool.acquire() as conn:
        await conn.execute("""
            CREATE TABLE IF NOT EXISTS users (
                user_id BIGINT PRIMARY KEY,
                name TEXT,
                university TEXT,
                faculty TEXT,
                year INTEGER,
                skills TEXT,
                looking_for TEXT,
                contact TEXT,
                description TEXT,
                photo_url TEXT,
                role TEXT
            )
        """)
        await conn.execute("""
            CREATE TABLE IF NOT EXISTS likes (
                id SERIAL PRIMARY KEY,
                from_user_id BIGINT,
                to_user_id BIGINT,
                UNIQUE(from_user_id, to_user_id)
            )
        """)
        for col in ["description", "photo_url", "role"]:
            try:
                await conn.execute(f"ALTER TABLE users ADD COLUMN {col} TEXT")
            except:
                pass

@app.on_event("startup")
async def startup():
    await init_db()
    asyncio.create_task(dp.start_polling(bot))

@app.on_event("shutdown")
async def shutdown():
    await pool.close()

@dp.message(Command("start"))
async def cmd_start(message: types.Message):
    await message.answer(
        "👋 Привет! Я Network — платформа для студентов, выпускников и работодателей!\n\n"
        "🔍 Найди тиммейта, проект или стажировку прямо сейчас 👇",
        reply_markup=types.InlineKeyboardMarkup(inline_keyboard=[
            [types.InlineKeyboardButton(
                text="🚀 Открыть Network",
                web_app=types.WebAppInfo(url="https://hse-network.onrender.com")
            )]
        ])
    )

class User(BaseModel):
    user_id: int
    name: str
    university: str
    faculty: str
    year: int
    skills: str
    looking_for: str
    contact: str
    description: str = ""
    photo_url: str = ""
    role: str = ""

class Like(BaseModel):
    from_user_id: int
    to_user_id: int

@app.post("/api/users")
async def save_user(user: User):
    async with pool.acquire() as conn:
        await conn.execute("""
            INSERT INTO users (user_id, name, university, faculty, year, skills, looking_for, contact, description, photo_url, role)
            VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9, $10, $11)
            ON CONFLICT (user_id) DO UPDATE SET
                name=EXCLUDED.name,
                university=EXCLUDED.university,
                faculty=EXCLUDED.faculty,
                year=EXCLUDED.year,
                skills=EXCLUDED.skills,
                looking_for=EXCLUDED.looking_for,
                contact=EXCLUDED.contact,
                description=EXCLUDED.description,
                photo_url=EXCLUDED.photo_url,
                role=EXCLUDED.role
        """, user.user_id, user.name, user.university, user.faculty, user.year, user.skills, user.looking_for, user.contact, user.description, user.photo_url, user.role)
    return {"status": "ok"}

@app.post("/api/likes")
async def add_like(like: Like):
    async with pool.acquire() as conn:
        from_user = await conn.fetchrow("SELECT * FROM users WHERE user_id = $1", like.from_user_id)
        if not from_user:
            return {"status": "no_profile"}
        try:
            await conn.execute("""
                INSERT INTO likes (from_user_id, to_user_id) VALUES ($1, $2)
            """, like.from_user_id, like.to_user_id)
            if like.from_user_id != like.to_user_id:
                to_user = await conn.fetchrow("SELECT * FROM users WHERE user_id = $1", like.to_user_id)
                if to_user:
                    try:
                        await bot.send_message(
                            like.to_user_id,
                            f"❤️ {from_user['name']} лайкнул твою анкету!\n\nПосмотри профиль: @{from_user['contact'].replace('@', '')}"
                        )
                    except:
                        pass
            return {"status": "ok"}
        except:
            return {"status": "already_liked"}

@app.delete("/api/likes")
async def remove_like(like: Like):
    async with pool.acquire() as conn:
        await conn.execute("DELETE FROM likes WHERE from_user_id = $1 AND to_user_id = $2", like.from_user_id, like.to_user_id)
    return {"status": "ok"}

@app.get("/api/likes/{user_id}")
async def get_likes(user_id: int):
    async with pool.acquire() as conn:
        count = await conn.fetchval("SELECT COUNT(*) FROM likes WHERE to_user_id = $1", user_id)
        liked_by_me = await conn.fetch("SELECT to_user_id FROM likes WHERE from_user_id = $1", user_id)
    return {"count": count, "liked_by_me": [r["to_user_id"] for r in liked_by_me]}

@app.get("/api/users")
async def get_users(looking_for: str = None):
    async with pool.acquire() as conn:
        if looking_for:
            rows = await conn.fetch("SELECT * FROM users WHERE looking_for = $1", looking_for)
        else:
            rows = await conn.fetch("SELECT * FROM users")
    return [dict(row) for row in rows]

@app.get("/api/users/{user_id}")
async def get_user(user_id: int):
    async with pool.acquire() as conn:
        row = await conn.fetchrow("SELECT * FROM users WHERE user_id = $1", user_id)
    if row:
        return dict(row)
    return None

app.mount("/", StaticFiles(directory="static", html=True), name="static")