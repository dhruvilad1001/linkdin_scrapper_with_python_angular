# Quick Start Guide

## 🚀 Start (3 Steps)

### 1. Start MongoDB
```bash
net start MongoDB  # Windows (as Admin)
```

### 2. Start App
```bash
start.bat  # Windows
./start.sh # Linux/macOS
```

### 3. Configure (First Time)
Edit `backend/.env` when prompted:
```env
LINKEDIN_EMAIL=your_email@example.com
LINKEDIN_PASSWORD=your_password
```

Open: http://localhost:4200

## 🐛 Common Fixes

### Frontend Error
```bash
cd frontend
npm install
```

### Backend Error
```bash
cd backend
install_windows.bat  # Windows
pip install -r requirements.txt  # Linux/macOS
```

### MongoDB Error
```bash
net start MongoDB  # Windows (as Admin)
```

## 🧪 Test
1. Open http://localhost:4200
2. Click "Scraper"
3. Enter: `https://www.linkedin.com/in/vraj-maheshwari-6537ba278/`
4. Click "Scrape Profile"
5. Wait 30-60 seconds

## 🛑 Stop
Close the Backend and Frontend windows

---

**Need more help?** See README.md
