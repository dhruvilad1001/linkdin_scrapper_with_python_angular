#!/usr/bin/env python3
"""
MongoDB Connection Test Script
Tests if MongoDB is accessible and ready for the LinkedIn Scraper
"""

import sys
from pymongo import MongoClient
from pymongo.errors import ConnectionFailure, ServerSelectionTimeoutError

def print_header(text):
    print("\n" + "="*60)
    print(f"  {text}")
    print("="*60 + "\n")

def test_mongodb_connection():
    """Test MongoDB connection and display information"""
    
    print_header("MongoDB Connection Test")
    
    connection_string = "mongodb://localhost:27017/"
    print(f"Testing connection to: {connection_string}")
    
    try:
        # Create client with short timeout
        print("Connecting to MongoDB...")
        client = MongoClient(connection_string, serverSelectionTimeoutMS=5000)
        
        # Test connection
        client.admin.command('ping')
        print("✅ MongoDB connection successful!\n")
        
        # Get server info
        server_info = client.server_info()
        print(f"MongoDB Version: {server_info['version']}")
        print(f"Server: {connection_string}")
        
        # List databases
        print("\n📊 Available Databases:")
        databases = client.list_database_names()
        if databases:
            for db_name in databases:
                db = client[db_name]
                collections = db.list_collection_names()
                print(f"  - {db_name} ({len(collections)} collections)")
        else:
            print("  (No databases yet)")
        
        # Check Linkedin database
        print("\n🔍 Checking LinkedIn Scraper Database:")
        db = client["Linkedin"]
        collections = db.list_collection_names()
        
        if "profile_data" in collections:
            count = db.profile_data.count_documents({})
            print(f"  ✅ Database: Linkedin")
            print(f"  ✅ Collection: profile_data")
            print(f"  ✅ Profiles: {count}")
            
            if count > 0:
                # Show sample profile
                sample = db.profile_data.find_one()
                print(f"\n  Sample Profile:")
                print(f"    Name: {sample.get('name', 'N/A')}")
                print(f"    URL: {sample.get('url', 'N/A')}")
                print(f"    Last Updated: {sample.get('last_updated', 'N/A')}")
        else:
            print(f"  ℹ️  Database: Linkedin (will be created)")
            print(f"  ℹ️  Collection: profile_data (will be created)")
            print(f"  ℹ️  Profiles: 0 (database is empty)")
        
        # Connection details for app
        print("\n⚙️  Configuration for .env file:")
        print(f"  MONGO_URI={connection_string}")
        print(f"  DATABASE_NAME=Linkedin")
        print(f"  COLLECTION_NAME=profile_data")
        
        print("\n✅ MongoDB is ready for LinkedIn Scraper!")
        
        client.close()
        return True
        
    except ServerSelectionTimeoutError:
        print("❌ Connection timeout!")
        print("\nMongoDB is not responding. Possible reasons:")
        print("  1. MongoDB service is not running")
        print("  2. MongoDB is not installed")
        print("  3. Firewall is blocking connection")
        print("\n💡 Solutions:")
        print("  - Start MongoDB: net start MongoDB")
        print("  - Or run: start_mongodb.bat")
        print("  - Check status: check_mongodb.bat")
        return False
        
    except ConnectionFailure as e:
        print(f"❌ Connection failed: {e}")
        print("\n💡 Solutions:")
        print("  - Verify MongoDB is running: sc query MongoDB")
        print("  - Start MongoDB: net start MongoDB")
        print("  - Check MongoDB logs")
        return False
        
    except Exception as e:
        print(f"❌ Unexpected error: {e}")
        print("\n💡 Check:")
        print("  - MongoDB installation")
        print("  - Connection string")
        print("  - Network settings")
        return False

def main():
    """Main function"""
    print("\n🔍 MongoDB Connection Tester")
    print("For LinkedIn Profile Scraper v2.0")
    
    success = test_mongodb_connection()
    
    if success:
        print("\n" + "="*60)
        print("  🎉 All checks passed!")
        print("="*60)
        print("\nYou can now start the LinkedIn Scraper:")
        print("  1. Configure backend/.env file")
        print("  2. Run: start.bat")
        print("  3. Open: http://localhost:4200")
    else:
        print("\n" + "="*60)
        print("  ⚠️  MongoDB is not ready")
        print("="*60)
        print("\nPlease fix MongoDB connection before starting the app.")
        print("See MONGODB_SETUP.md for detailed instructions.")
    
    print("\n")
    return 0 if success else 1

if __name__ == "__main__":
    try:
        sys.exit(main())
    except KeyboardInterrupt:
        print("\n\nTest interrupted by user")
        sys.exit(1)
