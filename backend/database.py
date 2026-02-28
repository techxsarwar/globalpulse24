import os
from motor.motor_asyncio import AsyncIOMotorClient

# Get the secret URL from Railway's environment
MONGO_URL = os.getenv("MONGO_URL")

# Initialize the MongoDB client
client = AsyncIOMotorClient(MONGO_URL)
db = client.GlobalPulse24
news_collection = db.get_collection("articles")

def get_database():
    return db
