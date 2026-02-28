from motor.motor_asyncio import AsyncIOMotorClient
import os

# Default local MongoDB connection if URI is not provided in env
MONGO_DETAILS = os.getenv("MONGO_DETAILS", "mongodb://mongo:YNRDRPcciIxZlVZJYVTMaeMwbXZYGqBj@mongodb.railway.internal:27017")
DATABASE_NAME = os.getenv("DATABASE_NAME", "globalpulse24")

client = AsyncIOMotorClient(MONGO_DETAILS)
database = client[DATABASE_NAME]

def get_database():
    return database
