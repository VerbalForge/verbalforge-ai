#!/usr/bin/env python3
"""
Clean MongoDB Database Script
Wipes all data from verbalforge collections
"""

import sys
from pymongo import MongoClient
from pymongo.errors import ConnectionFailure

# MongoDB configuration
MONGODB_URI = "mongodb://localhost:27017/"
DATABASE_NAME = "verbalforge"
COLLECTIONS = ["questions", "passages", "user_question","users"]


def clean_database():
    """Delete all documents from specified collections"""
    
    print("\n⚠️  WARNING: This will delete ALL data from MongoDB!")
    print(f"Database: {DATABASE_NAME}")
    print(f"Collections: {', '.join(COLLECTIONS)}")
    print()
    
    confirm = input("Are you sure? Type 'yes' to continue: ")
    
    if confirm.lower() != 'yes':
        print("Cancelled.")
        sys.exit(0)
    
    try:
        # Connect to MongoDB
        print("\nConnecting to MongoDB...")
        client = MongoClient(MONGODB_URI, serverSelectionTimeoutMS=5000)
        
        # Test connection
        client.admin.command('ping')
        print("✓ Connected to MongoDB")
        
        # Get database
        db = client[DATABASE_NAME]
        
        # Delete documents from each collection
        print(f"\nWiping collections from '{DATABASE_NAME}'...")
        
        total_deleted = 0
        for collection_name in COLLECTIONS:
            collection = db[collection_name]
            result = collection.delete_many({})
            count = result.deleted_count
            total_deleted += count
            print(f"  ✓ {collection_name}: {count} documents deleted")
        
        print(f"\n✓ Database cleaned successfully!")
        print(f"Total documents deleted: {total_deleted}")
        
        client.close()
        
    except ConnectionFailure as e:
        print(f"\n✗ Error: Could not connect to MongoDB")
        print(f"  Make sure MongoDB is running at {MONGODB_URI}")
        sys.exit(1)
    except Exception as e:
        print(f"\n✗ Error: {e}")
        sys.exit(1)


if __name__ == "__main__":
    clean_database()
