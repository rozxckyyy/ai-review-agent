import os

from dotenv import load_dotenv


load_dotenv()

GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
GEMINI_MODEL = os.getenv("GEMINI_MODEL")
GITHUB_TOKEN = os.getenv("GITHUB_TOKEN")

if not GEMINI_API_KEY:
    raise RuntimeError("Не найден GEMINI_API_KEY. Проверь файл .env.")