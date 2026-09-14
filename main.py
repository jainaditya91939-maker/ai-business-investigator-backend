from fastapi.middleware.cors import CORSMiddleware
from fastapi import FastAPI
from sqlalchemy import text

from database import engine

from routes.suppliers import router as suppliers_router
from routes.transactions import router as transactions_router
from routes.dashboard import router as dashboard_router
from routes.product import router as products_router

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:5173",
        "http://127.0.0.1:5173",
        "https://ai-business-investigator-frontend.vercel.app"
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(suppliers_router)
app.include_router(transactions_router)
app.include_router(dashboard_router)
app.include_router(products_router)


@app.get("/")
def home():
    return {
        "message": "AI Business Investigator Backend is running!"
    }


@app.get("/test-db")
def test_database():
    with engine.connect() as connection:
        result = connection.execute(
            text("SELECT current_database();")
        )
        database_name = result.scalar()

    return {
        "message": "Database connected successfully!",
        "database": database_name
    }