# LinkedIn Scraper - CAPTCHA Solutions

## 🎯 Quick Answer
**You CANNOT fully automate CAPTCHA solving.** But I've created 2 solutions for you:

---

## Solution 1: Cookie-Based (BEST - Fewer CAPTCHAs) ⭐

**File:** `linkedin_with_cookies.py`

### How it works:
1. First time: You login manually (solve CAPTCHA once)
2. Script saves your session cookies
3. Next times: Reuses cookies, no login needed!
4. Only shows CAPTCHA when cookies expire (every few days)

### Usage:
```bash
python linkedin_with_cookies.py
```

**First run:**
- Browser opens to LinkedIn login
- Login manually and solve CAPTCHA
- Script saves your session
- Starts scraping

**Subsequent runs:**
- Automatically logs in using saved cookies
- No CAPTCHA (usually)
- Starts scraping immediately

---

## Solution 2: Semi-Automated (Simple)

**File:** `linkedin_captcha_handler.py`

### How it works:
- Script pauses when CAPTCHA appears
- You solve it manually
- Script automatically continues

### Usage:
```bash
python linkedin_captcha_handler.py
```

---

## Which One Should You Use?

### Use `linkedin_with_cookies.py` if:
- ✅ You scrape regularly (daily/weekly)
- ✅ You want fewer CAPTCHAs
- ✅ You're okay with manual login once every few days

### Use `linkedin_captcha_handler.py` if:
- ✅ You scrape occasionally
- ✅ You want simpler code
- ✅ You don't mind solving CAPTCHA each time

---

## Tips to Avoid CAPTCHA

### 1. Add delays between profiles:
```python
import random
sleep(random.uniform(10, 20))  # 10-20 seconds
```

### 2. Limit daily scraping:
- Max 20-30 profiles per session
- Don't scrape 24/7

### 3. Use during business hours:
- Scrape 9 AM - 5 PM (your timezone)
- Looks more human

### 4. Don't use VPN:
- LinkedIn flags VPN/datacenter IPs
- Use your regular home internet

---

## Updating Your Notebook

If you want to keep using the Jupyter notebook, add this cell after login:

```python
import pickle

# After successful login, save cookies
pickle.dump(driver.get_cookies(), open("linkedin_cookies.pkl", "wb"))
print("✅ Cookies saved!")
```

Then add this cell at the start (before login):

```python
import pickle
from pathlib import Path

# Try to load cookies
if Path("linkedin_cookies.pkl").exists():
    driver.get("https://www.linkedin.com")
    cookies = pickle.load(open("linkedin_cookies.pkl", "rb"))
    for cookie in cookies:
        driver.add_cookie(cookie)
    driver.refresh()
    sleep(3)
    
    if "feed" in driver.current_url:
        print("✅ Logged in using cookies!")
    else:
        print("⚠️ Cookies expired, login manually")
```

---

## The Reality

LinkedIn **actively fights** web scraping:
- They detect Selenium
- They rate-limit requests
- They require CAPTCHA for suspicious activity
- They can ban accounts

### Your options:
1. ✅ Use my cookie-based script (best balance)
2. ✅ Scrape slowly and carefully
3. ✅ Use LinkedIn's official API (for production)
4. ❌ Try to bypass CAPTCHA (will fail and get banned)

---

## Need More Help?

Read `CAPTCHA_SOLUTIONS.md` for detailed explanations of all options.

---

## Quick Start (Right Now)

```bash
# Install dependencies (if needed)
pip install selenium beautifulsoup4 lxml python-dotenv

# Run the cookie-based scraper
python linkedin_with_cookies.py
```

1. Browser opens
2. Login manually (solve CAPTCHA)
3. Script takes over and scrapes
4. Next time: no CAPTCHA needed!
