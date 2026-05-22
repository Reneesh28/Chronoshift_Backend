import os
from pathlib import Path
from dotenv import load_dotenv
from pymongo import MongoClient

# 1. Resolve shared env location (parent directory of flask_ai_engine)
SERVICE_DIR = Path(__file__).resolve().parent
ROOT_BACKEND_DIR = SERVICE_DIR.parent
ENV_PATH = ROOT_BACKEND_DIR / ".env"

if not ENV_PATH.exists():
    raise FileNotFoundError(f"Shared environment file not found at {ENV_PATH}")

# Load the root environment variables
load_dotenv(ENV_PATH)

# Read environment variables
MONGODB_URI = os.getenv("MONGODB_URI")
MONGO_DB_NAME = os.getenv("MONGO_DB_NAME", "Chronoshift")
HF_TOKEN = os.getenv("HF_TOKEN")
MODEL_NAME = os.getenv("MODEL_NAME", "microsoft/phi-2")

if not MONGODB_URI:
    raise ValueError("MONGODB_URI variable is missing in the env file")

if not HF_TOKEN:
    raise ValueError("HF_TOKEN variable is missing in the env file")

# 2. Establish MongoDB Client
client = MongoClient(MONGODB_URI)
db = client[MONGO_DB_NAME]

# 3. Mapped PyMongo Collections
users_collection = db["users"]
timelines_collection = db["timelines"]
branches_collection = db["branches"]
events_collection = db["events"]
simulations_collection = db["simulations"]
ai_summaries_collection = db["ai_summaries"]
replays_collection = db["replays"]

print(f"[CONFIG] Flask AI Engine config successfully loaded.")
print(f"[CONFIG] Target Model: '{MODEL_NAME}'")
print(f"[CONFIG] MongoDB database connected: '{MONGO_DB_NAME}'")
