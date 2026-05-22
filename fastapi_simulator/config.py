import os
from pathlib import Path
from dotenv import load_dotenv
from pymongo import MongoClient

# 1. Resolve shared env location (parent directory of fastapi_simulator)
SERVICE_DIR = Path(__file__).resolve().parent
ROOT_BACKEND_DIR = SERVICE_DIR.parent
ENV_PATH = ROOT_BACKEND_DIR / ".env"

if not ENV_PATH.exists():
    raise FileNotFoundError(f"Shared environment file not found at {ENV_PATH}")

# Load the root environment variables
load_dotenv(ENV_PATH)

MONGODB_URI = os.getenv("MONGODB_URI")
MONGO_DB_NAME = os.getenv("MONGO_DB_NAME", "Chronoshift")

if not MONGODB_URI:
    raise ValueError("MONGODB_URI variable is missing in the env file")

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
