import os
from dotenv import load_dotenv

load_dotenv()

class Config:
    RAPIDAPI_KEY = os.getenv("RAPIDAPI_KEY")
    AVIATIONSTACK_KEY = os.getenv("AVIATIONSTACK_KEY")
