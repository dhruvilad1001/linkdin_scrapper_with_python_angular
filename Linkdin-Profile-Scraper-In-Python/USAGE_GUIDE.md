# LinkedIn Scraper - Complete Usage Guide

## 🚀 Quick Start

### 1. Run the Complete Scraper
```bash
python linkedin_captcha_handler.py
```

This will:
1. Open Chrome browser
2. Navigate to LinkedIn login
3. Login with your credentials from `.env`
4. **Wait for you to solve CAPTCHA** (if it appears)
5. Scrape all profiles in the list
6. Save individual JSON files for each profile
7. Save a combined `all_profiles.json` file

---

## 📋 What Gets Scraped

For each profile, the script extracts:

### ✅ Basic Info
- Name
- Profile URL
- Headline

### ✅ About Section
- Full about/bio text

### ✅ Experience
- Company name
- Designation/Title
- Duration
- Location

### ✅ Education
- College/University
- Degree
- Duration
- Grade (if available)

---

## 🔧 Configuration

### Add Multiple Profiles to Scrape

Edit `linkedin_captcha_handler.py` at the bottom:

```python
profile_urls = [
    "https://www.linkedin.com/in/rohitdoshi9/",
    "https://www.linkedin.com/in/savaliya-mukund27/",
    "https://www.linkedin.com/in/mitkumar-patel-031917266/",
    # Add more URLs here
]
```

### Adjust Delays

To avoid detection, you can increase delays:

```python
# In the main section, change:
delay = 5  # seconds between profiles
# To:
delay = 10  # or more
```

---

## 📁 Output Files

### Individual Profile Files
Each profile is saved as: `{Name}_profile_data.json`

Example: `Rohit_Doshi_profile_data.json`

### Combined File
All profiles are saved together in: `all_profiles.json`

### Example Output Structure
```json
{
  "name": "Rohit Doshi",
  "url": "https://www.linkedin.com/in/rohitdoshi9/",
  "headline": "Sr. Software Engineer at Amazon",
  "about": "Hi, I'm Rohit...",
  "experience": [
    {
      "company_name": "Amazon",
      "designation": "Software Engineer(L5)",
      "duration": "Jul 2025 to Present · 5 mos",
      "location": "Pune, Maharashtra, India"
    }
  ],
  "education": [
    {
      "college": "BITS Pilani",
      "degree": "Master of Technology",
      "duration": "2017 - 2019"
    }
  ]
}
```

---

## 🛡️ CAPTCHA Handling

### When CAPTCHA Appears

The script will:
1. Detect the CAPTCHA page
2. Print a warning message
3. **Wait up to 120 seconds** for you to solve it
4. Show countdown timer
5. Automatically continue once solved

### What You Need to Do

1. Watch the browser window
2. When CAPTCHA appears, click the checkbox
3. Solve any image challenges
4. Script automatically detects when done
5. Scraping continues

### If Timeout Occurs

If you don't solve CAPTCHA in 120 seconds:
- Script will print timeout message
- You can manually solve it
- Script will retry on next profile

---

## ⚠️ Common Issues

### Issue: "Join LinkedIn" instead of name
**Cause:** Session expired or CAPTCHA not solved  
**Solution:** 
- Solve CAPTCHA in browser
- Check if you're logged in
- Restart script

### Issue: Empty experience/education
**Cause:** Profile is private or has no data  
**Solution:** This is normal, script will continue

### Issue: Script stops after login
**Cause:** CAPTCHA waiting for manual solve  
**Solution:** Check browser window and solve CAPTCHA

### Issue: Too many CAPTCHAs
**Cause:** LinkedIn detected bot activity  
**Solution:** 
- Increase delays between profiles
- Scrape fewer profiles per session
- Use `linkedin_with_cookies.py` instead

---

## 💡 Best Practices

### 1. Scrape Responsibly
- Max 20-30 profiles per session
- Add 10-15 second delays between profiles
- Don't run 24/7

### 2. Avoid Detection
- Use during business hours (9 AM - 5 PM)
- Don't use VPN
- Use your regular home internet
- Keep browser window visible

### 3. Handle Errors
- Script continues even if one profile fails
- Check output for error messages
- Review saved JSON files

---

## 🔄 Alternative: Cookie-Based Scraper

If you're getting too many CAPTCHAs, use the cookie-based version:

```bash
python linkedin_with_cookies.py
```

**Benefits:**
- Login once, save session
- Reuse session for days
- Fewer CAPTCHAs

---

## 📊 Bulk Scraping from File

Want to scrape URLs from a text file? Add this to the script:

```python
# Read URLs from file
with open('bulk_url.txt', 'r') as f:
    profile_urls = [line.strip() for line in f if line.strip()]
```

Then put your URLs in `bulk_url.txt` (one per line):
```
https://www.linkedin.com/in/profile1/
https://www.linkedin.com/in/profile2/
https://www.linkedin.com/in/profile3/
```

---

## 🆘 Need Help?

### Check These Files:
- `CAPTCHA_SOLUTIONS.md` - Detailed CAPTCHA solutions
- `HOW_TO_USE.md` - Quick reference guide

### Debug Mode:
Add this at the top of the script to see more details:
```python
import logging
logging.basicConfig(level=logging.DEBUG)
```

---

## ✅ Success Checklist

Before running:
- [ ] `.env` file exists with Email and Password
- [ ] Chrome browser installed
- [ ] Dependencies installed (`pip install -r requirements.txt`)
- [ ] Profile URLs added to the script
- [ ] Ready to solve CAPTCHA manually if needed

After running:
- [ ] Check console output for errors
- [ ] Verify JSON files were created
- [ ] Open JSON files to verify data quality
- [ ] Check `all_profiles.json` for combined data

---

## 🎯 Example Session

```
$ python linkedin_captcha_handler.py

✅ Successfully logged in!

============================================================
📄 Scraping: https://www.linkedin.com/in/rohitdoshi9/
============================================================
✅ Name: Rohit Doshi
✅ Headline: Sr. Software Engineer at Amazon...
✅ About: 1234 characters
✅ Found 10 experience entries
✅ Clicked 'See all education' button
✅ Found 3 education entries

============================================================
✅ Profile scraping complete!
============================================================

💾 Saved to: Rohit_Doshi_profile_data.json

============================================================
🎉 SCRAPING COMPLETE!
============================================================
✅ Successfully scraped 1 out of 1 profiles

Profiles scraped:
  • Rohit Doshi - https://www.linkedin.com/in/rohitdoshi9/

💾 All profiles saved to: all_profiles.json


Press Enter to close browser...
```

---

Happy scraping! 🚀
