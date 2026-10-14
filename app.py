"""Local uvicorn and Vercel FastAPI entry point."""
from src.pharmacy_web.app import create_app

app = create_app()
