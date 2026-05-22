from pymongo import MongoClient
from dotenv import load_dotenv
import os

# --------------------------------------------------
# LOAD ENV VARIABLES
# --------------------------------------------------

load_dotenv()

MONGODB_URI = os.getenv("MONGODB_URI")
MONGO_DB_NAME = os.getenv("MONGO_DB_NAME")

# --------------------------------------------------
# CREATE CLIENT
# --------------------------------------------------

client = MongoClient(MONGODB_URI)

# --------------------------------------------------
# DATABASE
# --------------------------------------------------

db = client[MONGO_DB_NAME]

# --------------------------------------------------
# TEST CONNECTION
# --------------------------------------------------

try:
    client.admin.command("ping")

    print("\n✅ MongoDB Atlas Connection Successful\n")

except Exception as e:

    print("\n❌ MongoDB Connection Failed\n")
    print(e)

# --------------------------------------------------
# COLLECTIONS
# --------------------------------------------------

timelines_collection = db["timelines"]