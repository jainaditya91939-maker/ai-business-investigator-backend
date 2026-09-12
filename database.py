import os

from sqlalchemy import create_engine

DATABASE_URL = os.getenv(
	"DATABASE_URL",
	"postgresql+psycopg://postgres:postgres@localhost:5432/ai_business_investigator",
)

engine = create_engine(DATABASE_URL)