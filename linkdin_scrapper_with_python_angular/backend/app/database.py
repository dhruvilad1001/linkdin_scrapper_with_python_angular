from motor.motor_asyncio import AsyncIOMotorClient
from pymongo import MongoClient
from app.config import settings
import logging

logger = logging.getLogger(__name__)

class Database:
    client: AsyncIOMotorClient = None
    
    @classmethod
    async def connect_db(cls):
        """Connect to MongoDB"""
        try:
            cls.client = AsyncIOMotorClient(settings.MONGO_URI)
            await cls.client.admin.command('ping')
            logger.info("✅ MongoDB connection established")
        except Exception as e:
            logger.error(f"❌ MongoDB connection failed: {e}")
            raise
    
    @classmethod
    async def close_db(cls):
        """Close MongoDB connection"""
        if cls.client:
            cls.client.close()
            logger.info("MongoDB connection closed")
    
    @classmethod
    def get_database(cls):
        """Get database instance"""
        return cls.client[settings.DATABASE_NAME]
    
    @classmethod
    def get_collection(cls):
        """Get profiles collection"""
        db = cls.get_database()
        return db[settings.COLLECTION_NAME]

# Synchronous client for scraper (Selenium runs in threads)
def get_sync_collection():
    """Get synchronous MongoDB collection for scraper"""
    client = MongoClient(settings.MONGO_URI)
    db = client[settings.DATABASE_NAME]
    return db[settings.COLLECTION_NAME]
