from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel
import aiosqlite
import os

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

DB_PATH = "hse_network.db"

async def init_db():
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute("""
            CREATE TABLE IF NOT EXISTS users (
                user_id INTEGER PRIMARY KEY,
                name TEXT,
                faculty TEXT,
                year INTEGER,
                skills TEXT,
                looking_for TEXT,
                contact TEXT
            )
        """)
        await db.commit()

@app.on_event("startup")
async def startup():
    await init_db()

class User(BaseModel):
    user_id: int
    name: str
    faculty: str
    year: int
    skills: str
    looking_for: str
    contact: str

@app.post("/api/users")
async def save_user(user: User):
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute("""
            INSERT OR REPLACE INTO users 
            (user_id, name, faculty, year, skills, looking_for, contact)
            VALUES (?, ?, ?, ?, ?, ?, ?)
        """, (user.user_id, user.name, user.faculty, user.year, user.skills, user.looking_for, user.contact))
        await db.commit()
    return {"status": "ok"}

@app.get("/api/users")
async def get_users(looking_for: str = None):
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        if looking_for:
            cursor = await db.execute(
                "SELECT * FROM users WHERE looking_for = ?", (looking_for,)
            )
        else:
            cursor = await db.execute("SELECT * FROM users")
        rows = await cursor.fetchall()
        return [dict(row) for row in rows]

app.mount("/", StaticFiles(directory="static", html=True), name="static")
