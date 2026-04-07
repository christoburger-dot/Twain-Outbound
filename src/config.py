import os
from dotenv import load_dotenv

load_dotenv()

EMAILBISON_API_TOKEN = os.environ["EMAILBISON_API_TOKEN"]
EMAILBISON_BASE_URL = os.environ.get("EMAILBISON_BASE_URL", "https://dedi.emailbison.com")
