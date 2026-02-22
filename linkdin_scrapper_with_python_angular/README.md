# LinkedIn Profile Scraper v2.0

Modern LinkedIn profile scraper with Python FastAPI backend and Angular frontend.

## 🚀 Quick Start

### Windows

```bash
# Option 1: Full install (first time)
start.bat

# Option 2: Quick run (after install)
RUN.bat
```

### Linux/macOS

```bash
./start.sh
```

## 📋 First Time Setup

1. **Install Prerequisites:**
   - Python 3.11+ (not 3.13)
   - Node.js 18+
   - MongoDB 4.4+

2. **Configure Credentials:**
   - Edit `backend/.env` with your LinkedIn email/password
   - Script will create this file automatically

3. **Wait for Installation:**
   - Backend: 2-3 minutes
   - Frontend: 3-5 minutes
   - One-time only

## ✨ Features

- Single & bulk profile scraping
- Name, headline, about, experience, education
- Projects, licenses, certifications, courses, awards
- MongoDB storage
- Excel export (grouped/flat)
- Search & filtering
- Analytics dashboard

## 🐛 Troubleshooting

### MongoDB Not Running

```bash
# Windows (as Administrator)
net start MongoDB

# Linux
sudo systemctl start mongodb

# macOS
brew services start mongodb-community
```

### Frontend Installation Failed

```bash
cd frontend
rmdir /s /q node_modules  # Windows
rm -rf node_modules       # Linux/macOS
npm install
```

### Backend Installation Failed

```bash
cd backend
rmdir /s /q venv  # Windows
rm -rf venv       # Linux/macOS
python -m venv venv
venv\Scripts\activate  # Windows
source venv/bin/activate  # Linux/macOS
pip install -r requirements.txt
```

### Port Already in Use

```bash
# Windows
netstat -ano | findstr :8000
taskkill /PID <PID> /F

# Linux/macOS
lsof -ti:8000 | xargs kill -9
```

## 📖 Usage

1. **Open Application:**
   - http://localhost:4200

2. **Scrape Profile:**
   - Go to "Scraper" page
   - Enter LinkedIn URL
   - Click "Scrape Profile"
   - Wait 30-60 seconds

3. **View Results:**
   - Go to "Profiles" page
   - Click "View" for details
   - Use search to filter

4. **Export Data:**
   - Click "Export to Excel"
   - Choose format (grouped/flat)

## 📁 Project Structure

```
linkdin_scrapper_with_python_angular/
├── start.bat / start.sh       # Start scripts
├── README.md                  # This file
├── SIMPLIFIED_GUIDE.md        # Quick reference
├── TEST_WITH_PROFILES.md      # Testing guide
├── MONGODB_SETUP.md           # MongoDB help
├── backend/
│   ├── app/                   # FastAPI application
│   ├── .env.example           # Configuration template
│   ├── requirements.txt       # Python dependencies
│   └── install_windows.bat    # Windows installer
└── frontend/
    ├── src/app/               # Angular application
    └── package.json           # Node dependencies
```

## 🔧 Configuration

Edit `backend/.env`:

```env
MONGO_URI=mongodb://localhost:27017/
DATABASE_NAME=Linkedin
COLLECTION_NAME=profile_data
LINKEDIN_EMAIL=your_email@example.com
LINKEDIN_PASSWORD=your_password
SECRET_KEY=your-random-secret-key
CORS_ORIGINS=http://localhost:4200
```

## 🧪 Testing

Test with real profiles:
- https://www.linkedin.com/in/vraj-maheshwari-6537ba278/
- https://www.linkedin.com/in/dhruvi-lad-7a900b352/

See `TEST_WITH_PROFILES.md` for detailed testing guide.

## 📊 API Documentation

Once running, visit:
- **API Docs:** http://localhost:8000/docs
- **Health Check:** http://localhost:8000/api/health

## 🛑 Stopping

Close the Backend and Frontend command windows, or press Ctrl+C in each.

## ⚠️ Important Notes

- **CAPTCHA:** LinkedIn may show CAPTCHA - solve it manually
- **Rate Limiting:** Don't scrape too many profiles at once
- **Private Profiles:** Cannot scrape private profiles
- **Terms of Service:** Respect LinkedIn's terms of service

## 📞 Support

For issues:
1. Check `SIMPLIFIED_GUIDE.md` for quick fixes
2. Check `MONGODB_SETUP.md` for MongoDB issues
3. Check `TEST_WITH_PROFILES.md` for testing help

## 📄 License

For educational purposes only. Respect LinkedIn's terms of service.

---

**Version:** 2.0.0  
**Last Updated:** 2025
