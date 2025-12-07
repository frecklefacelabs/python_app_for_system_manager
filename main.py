from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from contextlib import asynccontextmanager, contextmanager
import os
import psycopg2
from psycopg2.extras import RealDictCursor

DATABASE_URL = os.getenv("DATABASE_URL", "postgresql://myapp@localhost/myapp")
ENVIRONMENT = os.getenv("ENVIRONMENT", "development")

@contextmanager
def get_db_connection():
    conn = psycopg2.connect(DATABASE_URL)
    try:
        yield conn
    finally:
        conn.close()

# Initialize database table
def init_db():
    with get_db_connection() as conn:
        with conn.cursor() as cur:
            cur.execute("""
                CREATE TABLE IF NOT EXISTS messages (
                    id SERIAL PRIMARY KEY,
                    content TEXT NOT NULL,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)
            conn.commit()

# Modern lifespan event handler
@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup
    init_db()
    print(f"🚀 Application started in {ENVIRONMENT} mode!")
    yield
    # Shutdown (if you need cleanup)
    print("👋 Application shutting down...")

app = FastAPI(
    title="My Awesome API",
    description="Managed by System Manager!",
    version="1.0.0",
    lifespan=lifespan  # Add the lifespan here
)

@app.get("/")
async def root():
    return {
        "message": "Hello from System Manager!",
        "environment": ENVIRONMENT,
        "status": "running"
    }

@app.get("/health")
async def health_check():
    try:
        with get_db_connection() as conn:
            with conn.cursor() as cur:
                cur.execute("SELECT 1")
        return {"status": "healthy", "database": "connected"}
    except Exception as e:
        raise HTTPException(status_code=503, detail=f"Database error: {str(e)}")

class Message(BaseModel):
    content: str

@app.post("/messages")
async def create_message(message: Message):
    with get_db_connection() as conn:
        with conn.cursor(cursor_factory=RealDictCursor) as cur:
            cur.execute(
                "INSERT INTO messages (content) VALUES (%s) RETURNING id, content, created_at",
                (message.content,)
            )
            result = cur.fetchone()
            conn.commit()
            return result

@app.get("/messages")
async def get_messages():
    with get_db_connection() as conn:
        with conn.cursor(cursor_factory=RealDictCursor) as cur:
            cur.execute("SELECT id, content, created_at FROM messages ORDER BY created_at DESC LIMIT 10")
            results = cur.fetchall()
            return {"messages": results}
