"""MongoDB client connection management."""
import os
from pymongo import MongoClient
from pymongo.errors import ConnectionFailure
from django.conf import settings


_mongo_client = None


def get_mongo_client():
    """
    Get or create MongoDB client connection.
    
    Returns:
        MongoClient: MongoDB client instance
    """
    global _mongo_client
    
    if _mongo_client is None:
        mongo_settings = getattr(settings, 'MONGODB_SETTINGS', {})
        
        host = mongo_settings.get('host', os.environ.get('MONGO_HOST', 'localhost'))
        port = mongo_settings.get('port', int(os.environ.get('MONGO_PORT', 27017)))
        username = mongo_settings.get('username', os.environ.get('MONGO_USER'))
        password = mongo_settings.get('password', os.environ.get('MONGO_PASSWORD'))
        database = mongo_settings.get('database', os.environ.get('MONGO_DB_NAME', 'startup_gateway'))
        
        
        if username and password:
            connection_string = f"mongodb://{username}:{password}@{host}:{port}/{database}"
        else:
            connection_string = f"mongodb://{host}:{port}/{database}"
        
        try:
            _mongo_client = MongoClient(
                connection_string,
                serverSelectionTimeoutMS=5000,
                connectTimeoutMS=10000,
            )
            
            _mongo_client.admin.command('ping')
        except ConnectionFailure as e:
            raise ConnectionError(f"Failed to connect to MongoDB: {e}")
    
    return _mongo_client


def get_mongo_db():
    """
    Get MongoDB database instance.
    
    Returns:
        Database: MongoDB database
    """
    client = get_mongo_client()
    mongo_settings = getattr(settings, 'MONGODB_SETTINGS', {})
    db_name = mongo_settings.get('database', os.environ.get('MONGO_DB_NAME', 'startup_gateway'))
    return client[db_name]


def close_mongo_connection():
    """Close MongoDB connection."""
    global _mongo_client
    if _mongo_client:
        _mongo_client.close()
        _mongo_client = None
