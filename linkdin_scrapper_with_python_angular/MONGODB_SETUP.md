# MongoDB Setup Guide for Windows

## 📊 Current Status

Your MongoDB is **INSTALLED** but **NOT RUNNING**.

```
Status: Stopped
Service Name: MongoDB
Display Name: MongoDB Server (MongoDB)
Start Type: Automatic
```

## 🚀 Quick Fix - Start MongoDB

### Option 1: Use the Script (Easiest)
```bash
# Double-click this file:
start_mongodb.bat

# Or run from command prompt:
start_mongodb.bat
```

### Option 2: Command Line
```bash
# Open Command Prompt as Administrator
# Right-click Command Prompt -> Run as administrator

net start MongoDB
```

### Option 3: Windows Services
1. Press `Win + R`
2. Type: `services.msc`
3. Press Enter
4. Find "MongoDB Server (MongoDB)"
5. Right-click -> Start

## ✅ Verify MongoDB is Running

### Method 1: Check Service Status
```bash
# Run this script:
check_mongodb.bat

# Or use PowerShell:
Get-Service MongoDB
```

### Method 2: Test Connection
```bash
# If you have mongosh installed:
mongosh --eval "db.adminCommand('ping')"

# Should output: { ok: 1 }
```

### Method 3: Check Process
```bash
# Open Task Manager (Ctrl + Shift + Esc)
# Look for "mongod.exe" in Processes tab
```

## 🔧 Common Issues & Solutions

### Issue 1: "Access Denied" Error
```
Problem: Cannot start MongoDB service
Solution: Run Command Prompt as Administrator
```

**Steps:**
1. Search for "Command Prompt" in Start Menu
2. Right-click -> "Run as administrator"
3. Run: `net start MongoDB`

### Issue 2: MongoDB Not Installed
```
Problem: Service not found
Solution: Install MongoDB
```

**Installation Steps:**
1. Download MongoDB Community Server:
   - URL: https://www.mongodb.com/try/download/community
   - Version: Latest (7.0+)
   - Package: MSI installer

2. Run the installer:
   - Choose "Complete" installation
   - Check "Install MongoDB as a Service"
   - Check "Install MongoDB Compass" (optional GUI)

3. Verify installation:
   ```bash
   mongod --version
   ```

### Issue 3: Port 27017 Already in Use
```
Problem: Another process using MongoDB port
Solution: Stop the conflicting process or change port
```

**Check what's using port 27017:**
```bash
netstat -ano | findstr :27017
```

**Stop MongoDB if running:**
```bash
net stop MongoDB
```

### Issue 4: MongoDB Starts but Stops Immediately
```
Problem: Configuration or data directory issue
Solution: Check MongoDB logs
```

**Log location:**
```
C:\Program Files\MongoDB\Server\7.0\log\mongod.log
```

**Common fixes:**
1. Check disk space
2. Verify data directory exists: `C:\data\db\`
3. Check file permissions

## 📁 MongoDB File Locations

### Installation Directory
```
C:\Program Files\MongoDB\Server\7.0\
```

### Data Directory
```
C:\data\db\
```

### Configuration File
```
C:\Program Files\MongoDB\Server\7.0\bin\mongod.cfg
```

### Log File
```
C:\Program Files\MongoDB\Server\7.0\log\mongod.log
```

## 🔌 Connection Information

### For Your LinkedIn Scraper

**Connection String:**
```
mongodb://localhost:27017/
```

**Database Name:**
```
Linkedin
```

**Collection Name:**
```
profile_data
```

**In your .env file:**
```env
MONGO_URI=mongodb://localhost:27017/
DATABASE_NAME=Linkedin
COLLECTION_NAME=profile_data
```

## 🛠️ MongoDB Management Commands

### Start/Stop/Restart
```bash
# Start
net start MongoDB

# Stop
net stop MongoDB

# Restart
net stop MongoDB & net start MongoDB
```

### Check Status
```bash
# PowerShell
Get-Service MongoDB

# Command Prompt
sc query MongoDB
```

### Connect to MongoDB
```bash
# Using mongosh (MongoDB Shell)
mongosh

# Connect to specific database
mongosh mongodb://localhost:27017/Linkedin
```

## 📊 MongoDB Shell Commands

Once connected with `mongosh`:

```javascript
// Show all databases
show dbs

// Use Linkedin database
use Linkedin

// Show collections
show collections

// Count profiles
db.profile_data.countDocuments()

// View profiles
db.profile_data.find().limit(5)

// Find specific profile
db.profile_data.findOne({name: "Vraj Maheshwari"})

// Delete all profiles (careful!)
db.profile_data.deleteMany({})

// Exit
exit
```

## 🔐 Security (Optional)

### Enable Authentication (Production)

1. **Create admin user:**
```javascript
mongosh
use admin
db.createUser({
  user: "admin",
  pwd: "your_password",
  roles: ["root"]
})
```

2. **Update connection string:**
```
mongodb://admin:your_password@localhost:27017/
```

3. **Update .env file:**
```env
MONGO_URI=mongodb://admin:your_password@localhost:27017/
```

## 🎯 Quick Start Checklist

- [ ] MongoDB service is installed
- [ ] MongoDB service is running
- [ ] Can connect with mongosh
- [ ] Database "Linkedin" exists (will be created automatically)
- [ ] Connection string in .env is correct
- [ ] Backend can connect to MongoDB

## 🧪 Test MongoDB Connection

### Test Script
Create a file `test_mongodb.py` in backend folder:

```python
from pymongo import MongoClient

try:
    client = MongoClient("mongodb://localhost:27017/")
    client.admin.command('ping')
    print("✅ MongoDB connection successful!")
    
    # List databases
    print("\nDatabases:")
    for db in client.list_database_names():
        print(f"  - {db}")
    
    # Check Linkedin database
    db = client["Linkedin"]
    print(f"\nLinkedin database collections:")
    for coll in db.list_collection_names():
        print(f"  - {coll}")
    
    client.close()
except Exception as e:
    print(f"❌ MongoDB connection failed: {e}")
```

Run it:
```bash
cd backend
python test_mongodb.py
```

## 📱 MongoDB Compass (GUI)

If you installed MongoDB Compass:

1. Open MongoDB Compass
2. Connection string: `mongodb://localhost:27017`
3. Click "Connect"
4. Browse databases and collections visually

## 🆘 Still Having Issues?

### Check MongoDB Logs
```bash
# Open log file
notepad "C:\Program Files\MongoDB\Server\7.0\log\mongod.log"

# Or view last 50 lines in PowerShell
Get-Content "C:\Program Files\MongoDB\Server\7.0\log\mongod.log" -Tail 50
```

### Reinstall MongoDB
1. Uninstall current MongoDB
2. Delete data directory: `C:\data\db\`
3. Download fresh installer
4. Install with "Complete" option
5. Check "Install as Service"

### Alternative: MongoDB Atlas (Cloud)
If local MongoDB is problematic, use MongoDB Atlas (free tier):

1. Sign up: https://www.mongodb.com/cloud/atlas
2. Create free cluster
3. Get connection string
4. Update .env with Atlas connection string

## ✅ Success Indicators

MongoDB is working correctly when:

1. ✅ Service status shows "Running"
2. ✅ `mongosh` connects without errors
3. ✅ Backend starts without MongoDB errors
4. ✅ Can scrape and save profiles
5. ✅ Profiles appear in frontend

## 🎉 Next Steps

Once MongoDB is running:

1. Start MongoDB: `start_mongodb.bat`
2. Verify status: `check_mongodb.bat`
3. Start your app: `start.bat`
4. Test scraping: Follow TEST_WITH_PROFILES.md

---

**Quick Commands:**
```bash
# Start MongoDB
start_mongodb.bat

# Check status
check_mongodb.bat

# Start app (after MongoDB is running)
start.bat
```

**Need help?** Check the log file or run `check_mongodb.bat` for diagnostics.
