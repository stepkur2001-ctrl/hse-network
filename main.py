from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel
import asyncpg
import os
from dotenv import load_dotenv

load_dotenv()

DATABASE_URL = os.getenv("DATABASE_URL")

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

async def get_db():
    return await asyncpg.connect(DATABASE_URL)

async def init_db():
    conn = await get_db()
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
            description TEXT
        )
    """)
    try:
        await conn.execute("ALTER TABLE users ADD COLUMN description TEXT")
    except:
        pass
    await conn.close()

@app.on_event("startup")
async def startup():
    await init_db()

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

@app.post("/api/users")
async def save_user(user: User):
    conn = await get_db()
    await conn.execute("""
        INSERT INTO users (user_id, name, university, faculty, year, skills, looking_for, contact, description)
        VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9)
        ON CONFLICT (user_id) DO UPDATE SET
            name=EXCLUDED.name,
            university=EXCLUDED.university,
            faculty=EXCLUDED.faculty,
            year=EXCLUDED.year,
            skills=EXCLUDED.skills,
            looking_for=EXCLUDED.looking_for,
            contact=EXCLUDED.contact,
            description=EXCLUDED.description
    """, user.user_id, user.name, user.university, user.faculty, user.year, user.skills, user.looking_for, user.contact, user.description)
    await conn.close()
    return {"status": "ok"}

@app.get("/api/users")
async def get_users(looking_for: str = None):
    conn = await get_db()
    if looking_for:
        rows = await conn.fetch("SELECT * FROM users WHERE looking_for = $1", looking_for)
    else:
        rows = await conn.fetch("SELECT * FROM users")
    await conn.close()
    return [dict(row) for row in rows]

@app.get("/api/users/{user_id}")
async def get_user(user_id: int):
    conn = await get_db()
    row = await conn.fetchrow("SELECT * FROM users WHERE user_id = $1", user_id)
    await conn.close()
    if row:
        return dict(row)
    return None

app.mount("/", StaticFiles(directory="static", html=True), name="static")