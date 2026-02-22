# Manual Start Guide

Since the automatic script has issues, let's start manually:

## Step 1: Start Backend

Open Command Prompt and run:

```bash
cd D:\linkdin_verison_2\linkdin_scrapper_with_python_angular\backend
venv\Scripts\activate
uvicorn app.main:app --reload
```

Keep this window open. You should see:
```
INFO:     Uvicorn running on http://127.0.0.1:8000
```

## Step 2: Start Frontend

Open a NEW Command Prompt and run:

```bash
cd D:\linkdin_verison_2\linkdin_scrapper_with_python_angular\frontend
npm start
```

Keep this window open. You should see:
```
** Angular Live Development Server is listening on localhost:4200 **
```

## Step 3: Open Browser

Go to: http://localhost:4200

## Quick Commands

**Backend:**
```bash
cd backend
venv\Scripts\activate
python -m app.main
```

**Frontend:**
```bash
cd frontend
npm start
```

## If Frontend Fails

Try:
```bash
cd frontend
npm install --legacy-peer-deps
npm start
```

## Check if Running

**Backend:**
```bash
curl http://localhost:8000/api/health
```

**Frontend:**
```bash
curl http://localhost:4200
```
