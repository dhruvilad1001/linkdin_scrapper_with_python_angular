"""
LinkedIn CAPTCHA Handler - Complete Profile Scraper
This script handles CAPTCHA by pausing and waiting for manual solving
Scrapes: Name, Headline, About, Experience, Education

USAGE:
    python linkedin_captcha_handler.py

FEATURES:
    ✅ Anti-detection browser setup
    ✅ Automatic CAPTCHA detection and waiting
    ✅ Complete profile scraping (name, headline, about, experience, education)
    ✅ Beautiful table output for easy reading
    ✅ Saves individual JSON files per profile
    ✅ Saves combined JSON file with all profiles
    ✅ Human-like delays between requests

REQUIREMENTS:
    - .env file with Email and Password
    - pip install selenium beautifulsoup4 lxml python-dotenv tabulate

TO SCRAPE MULTIPLE PROFILES:
    Edit the profile_urls list at the bottom of this file
"""

import os
import re
import json
from time import sleep
from bs4 import BeautifulSoup
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException, NoSuchElementException
from dotenv import load_dotenv
from tabulate import tabulate

load_dotenv()

def setup_driver():
    """Setup Chrome driver with anti-detection options"""
    chrome_options = Options()
    chrome_options.add_argument('--disable-blink-features=AutomationControlled')
    chrome_options.add_experimental_option("excludeSwitches", ["enable-automation"])
    chrome_options.add_experimental_option('useAutomationExtension', False)
    
    driver = webdriver.Chrome(options=chrome_options)
    driver.execute_script("Object.defineProperty(navigator, 'webdriver', {get: () => undefined})")
    return driver

def wait_for_captcha_solve(driver, timeout=120):
    """
    Wait for user to manually solve CAPTCHA
    Returns True if solved, False if timeout
    """
    print("\n⚠️ CAPTCHA DETECTED!")
    print("Please solve the CAPTCHA in the browser window.")
    print(f"Waiting up to {timeout} seconds...\n")
    
    start_time = 0
    while start_time < timeout:
        current_url = driver.current_url
        
        # Check if we're past the CAPTCHA page
        if "checkpoint" not in current_url and "challenge" not in current_url:
            # Also check if we can find the feed or profile elements
            try:
                # Wait a bit to ensure page loaded
                sleep(2)
                if "feed" in current_url or "in/" in current_url:
                    print("✅ CAPTCHA solved! Continuing...")
                    return True
            except:
                pass
        
        # Show countdown
        remaining = timeout - start_time
        print(f"⏳ Waiting... {remaining} seconds remaining", end='\r')
        sleep(5)
        start_time += 5
    
    print("\n⏰ Timeout reached. CAPTCHA may not be solved.")
    return False

def login_to_linkedin(driver):
    """Login to LinkedIn with CAPTCHA handling"""
    driver.get('https://www.linkedin.com/login')
    sleep(2)
    
    # Enter credentials
    email = driver.find_element(By.ID, 'username')
    email.send_keys(os.environ['Email'])
    sleep(1)
    
    password = driver.find_element(By.ID, 'password')
    password.send_keys(os.environ['Password'])
    sleep(1)
    
    password.submit()
    sleep(5)
    
    # Check for CAPTCHA
    if "checkpoint" in driver.current_url or "challenge" in driver.current_url:
        if not wait_for_captcha_solve(driver):
            print("❌ Failed to solve CAPTCHA in time")
            return False
    
    print("✅ Successfully logged in!")
    return True

def get_experience_tokens(driver, timeout=15):
    """Scroll and fetch all hidden text tokens from the Experience section.
    Returns [] if section not found."""
    driver.execute_script("window.scrollTo(0, document.body.scrollHeight * 0.35);")
    sleep(2)

    try:
        exp_section = WebDriverWait(driver, timeout).until(
            EC.presence_of_element_located(
                (By.XPATH, "//section[.//span[text()='Experience']]")
            )
        )
    except TimeoutException:
        print("ℹ️ No 'Experience' section found on this profile.")
        return []

    exp_html = exp_section.get_attribute("outerHTML")
    exp_soup = BeautifulSoup(exp_html, "lxml")

    tokens = [
        s.get_text(strip=True)
        for s in exp_soup.select("span.visually-hidden")
        if s.get_text(strip=True)
    ]
    return tokens


def parse_experience_tokens(tokens):
    """Parse tokens into clean company_name, designation, duration, location"""
    if tokens and tokens[0].strip().lower() == "experience":
        tokens = tokens[1:]

    roles_set = {
        "Full-time", "Part-time", "Internship", "Contract", "Self-employed",
        "Freelance", "Apprenticeship", "Volunteer", "Temporary", "Seasonal"
    }

    def is_duration(s: str) -> bool:
        s2 = s.lower()
        return (" to " in s2 and ("present" in s2 or "mo" in s2 or "yr" in s2)) or (" yr" in s2) or (" mo" in s2)

    def is_location(s: str) -> bool:
        if is_duration(s): return False
        if s in roles_set: return False
        loc_keywords = ["india", "remote", "on-site", "hybrid", "onsite", "work from home"]
        if any(k in s.lower() for k in loc_keywords):
            return True
        return ("," in s and len(s.split()) >= 2)

    def clean_company(s: str) -> str:
        """Remove role-type suffixes but keep the company name"""
        if not s:
            return ""
        for r in roles_set:
            s = s.replace("· " + r, "").replace(r, "")
        return s.strip()

    def looks_like_description(s: str, is_company=False) -> bool:
        if is_company:
            return False
        return (len(s.split()) > 15 or len(s) > 120 or s.lower().endswith((".png", ".jpg", ".jpeg")))

    result = []
    i, n = 0, len(tokens)

    while i < n:
        designation, company, dur, loc = "", "", "", ""

        if i < n:
            designation = tokens[i]; i += 1

        if i < n:
            if tokens[i] not in roles_set and not is_duration(tokens[i]) and not is_location(tokens[i]):
                company = tokens[i]; i += 1

        if i < n and is_duration(tokens[i]):
            dur = tokens[i]; i += 1

        if i < n and is_location(tokens[i]):
            loc = tokens[i]; i += 1

        # Fix: swap if designation looks like duration
        if is_duration(designation):
            dur, designation = designation, ""

        # Skip junk designations
        if looks_like_description(designation):
            designation = ""

        # Ensure company is kept if it contains company-like keywords
        if company and any(kw in company.lower() for kw in ["pvt", "inc", "solutions", "system", "hr", "ltd"]):
            pass
        elif looks_like_description(company, is_company=True):
            company = ""

        # Skip completely empty
        if not designation and not company:
            continue

        result.append({
            "company_name": clean_company(company),
            "designation": designation,
            "duration": dur,
            "location": loc
        })

    # Final filter: drop junk durations
    clean_result = [
        r for r in result
        if not looks_like_description(r["duration"])
    ]

    return clean_result


def scrape_experience(driver):
    """Scrape experience section"""
    tokens = get_experience_tokens(driver)
    if tokens:
        experience_struct = parse_experience_tokens(tokens)
        print(f"✅ Found {len(experience_struct)} experience entries")
        return experience_struct
    else:
        return []


def scrape_education(driver):
    """Scrape education section"""
    try:
        driver.execute_script("window.scrollTo(0, document.body.scrollHeight * 0.5);")
        sleep(2)

        clicked_see_all_education = False

        # Try clicking "See all education" if it exists
        try:
            see_all_education_btn = WebDriverWait(driver, 5).until(
                EC.element_to_be_clickable((By.ID, "navigation-index-see-all-education"))
            )
            driver.execute_script("arguments[0].scrollIntoView({block: 'center'});", see_all_education_btn)
            sleep(1)
            try:
                see_all_education_btn.click()
            except:
                driver.execute_script("arguments[0].click();", see_all_education_btn)

            sleep(3)
            print("✅ Clicked 'See all education' button")
            clicked_see_all_education = True
        except Exception:
            print("ℹ️ No 'See all education' button, scraping from main profile page")

        page_source = driver.page_source
        soup = BeautifulSoup(page_source, "lxml")

        education_data = []

        if clicked_see_all_education:
            edu_section = soup.find("section", {"class": "artdeco-card pb3"})
            if edu_section:
                edu_blocks = edu_section.find_all("li", {"class": "pvs-list__paged-list-item"})
            else:
                edu_blocks = soup.find_all("li", {"class": "pvs-list__paged-list-item"})
        else:
            edu_sections = driver.find_elements(By.XPATH, "//section[.//span[text()='Education']]")
            if edu_sections:
                edu_html = edu_sections[0].get_attribute("outerHTML")
                edu_soup = BeautifulSoup(edu_html, "lxml")
                edu_blocks = edu_soup.find_all("li", {"class": "artdeco-list__item"})
                if not edu_blocks:
                    edu_blocks = edu_soup.find_all("li", {"class": "pvs-list__paged-list-item"})
            else:
                edu_blocks = []

        for block in edu_blocks:
            spans = block.find_all("span", {"class": "visually-hidden"})
            if not spans:
                continue

            edu_dict = {}
            if len(spans) >= 1:
                edu_dict["college"] = spans[0].get_text(strip=True)
            if len(spans) >= 2:
                edu_dict["degree"] = spans[1].get_text(strip=True)
            if len(spans) >= 3:
                edu_dict["duration"] = spans[2].get_text(strip=True)
            if len(spans) >= 4:
                edu_dict["grade"] = spans[3].get_text(strip=True)

            if edu_dict.get("college"):
                education_data.append(edu_dict)

        print(f"✅ Found {len(education_data)} education entries")

        if clicked_see_all_education:
            driver.back()
            sleep(2)

        return education_data

    except Exception as e:
        print(f"❌ Error in education section: {e}")
        return []


def scrape_profile(driver, profile_url):
    """Scrape complete LinkedIn profile"""
    print(f"\n{'='*60}")
    print(f"📄 Scraping: {profile_url}")
    print(f"{'='*60}")
    
    driver.get(profile_url)
    sleep(3)
    
    page_source = driver.page_source
    soup = BeautifulSoup(page_source, 'lxml')
    
    profile_data = {'url': profile_url}
    
    # ===== NAME =====
    name = soup.find("h1")
    name_text = name.get_text().strip() if name else None
    
    # Check if we got blocked
    if name_text and ("Join LinkedIn" in name_text or "Sign in" in name_text or "LinkedIn" == name_text):
        print("⚠️ WARNING: Got login page instead of profile!")
        print("  Possible reasons:")
        print("  1. Session expired or CAPTCHA required")
        print("  2. LinkedIn detected bot activity")
        print("  3. Need to manually solve CAPTCHA in the browser")
        print(f"\nCurrent page title: {driver.title}")
        return None
    
    if not name_text:
        print("❌ Name not found - check if you need to solve CAPTCHA")
        return None
    
    profile_data['name'] = name_text
    print(f"✅ Name: {name_text}")
    
    # ===== HEADLINE =====
    headline = soup.find('div', {'class': 'text-body-medium break-words'})
    if headline:
        profile_data['headline'] = headline.get_text().strip()
        print(f"✅ Headline: {profile_data['headline'][:60]}...")
    else:
        profile_data['headline'] = None
    
    # ===== ABOUT =====
    try:
        driver.find_element(By.CLASS_NAME, "inline-show-more-text__button").click()
        sleep(1)
    except NoSuchElementException:
        pass

    page_source = driver.page_source
    soup = BeautifulSoup(page_source, 'lxml')

    about_div = soup.find('div', {'class': 'display-flex ph5 pv3'})
    if not about_div:
        about_div = soup.find('section', {'id': 'about'})

    if about_div:
        about = about_div.get_text().strip()
        profile_data['about'] = about if about else None
        if about:
            print(f"✅ About: {len(about)} characters")
    else:
        profile_data['about'] = None
    
    # ===== EXPERIENCE =====
    profile_data['experience'] = scrape_experience(driver)
    
    # ===== EDUCATION =====
    profile_data['education'] = scrape_education(driver)
    
    print(f"\n{'='*60}")
    print(f"✅ Profile scraping complete!")
    print(f"{'='*60}\n")
    
    return profile_data

def save_to_json(profile_data, filename=None):
    """Save profile data to JSON file"""
    if not filename:
        name = profile_data.get('name', 'unknown').replace(' ', '_')
        filename = f"{name}_profile_data.json"
    
    with open(filename, 'w', encoding='utf-8') as f:
        json.dump(profile_data, f, indent=2, ensure_ascii=False)
    
    print(f"💾 Saved to: {filename}")
    return filename


def print_profile_table(profile_data):
    """Print profile data in a nice table format with full details"""
    print(f"\n{'='*100}")
    print(f"📊 PROFILE SUMMARY - {profile_data.get('name', 'Unknown')}")
    print(f"{'='*100}\n")
    
    # Basic Info Table
    basic_info = [
        ["Name", profile_data.get('name', 'N/A')],
        ["Headline", profile_data.get('headline', 'N/A')],
        ["Profile URL", profile_data.get('url', 'N/A')],
    ]
    
    # Add About section if exists
    if profile_data.get('about'):
        about_text = profile_data['about']
        # Split long about text into multiple lines for better display
        if len(about_text) > 200:
            about_preview = about_text[:200] + "..."
            basic_info.append(["About (Preview)", about_preview])
            basic_info.append(["About (Full Length)", f"{len(about_text)} characters"])
        else:
            basic_info.append(["About", about_text])
    else:
        basic_info.append(["About", "N/A"])
    
    print("📋 BASIC INFORMATION")
    print(tabulate(basic_info, headers=["Field", "Value"], tablefmt="fancy_grid", maxcolwidths=[20, 80]))
    
    # Experience Table - FULL DETAILS
    if profile_data.get('experience'):
        print(f"\n💼 EXPERIENCE ({len(profile_data['experience'])} entries)")
        print("="*100)
        
        for i, exp in enumerate(profile_data['experience'], 1):
            exp_details = [
                ["#", i],
                ["Designation", exp.get('designation', 'N/A')],
                ["Company", exp.get('company_name', 'N/A')],
                ["Duration", exp.get('duration', 'N/A')],
                ["Location", exp.get('location', 'N/A')]
            ]
            print(f"\n🔹 Experience Entry {i}:")
            print(tabulate(exp_details, tablefmt="fancy_grid", maxcolwidths=[15, 80]))
    else:
        print(f"\n💼 EXPERIENCE: No experience data found")
    
    # Education Table - FULL DETAILS
    if profile_data.get('education'):
        print(f"\n🎓 EDUCATION ({len(profile_data['education'])} entries)")
        print("="*100)
        
        for i, edu in enumerate(profile_data['education'], 1):
            edu_details = [
                ["#", i],
                ["College/University", edu.get('college', 'N/A')],
                ["Degree", edu.get('degree', 'N/A')],
                ["Duration", edu.get('duration', 'N/A')],
                ["Grade", edu.get('grade', 'N/A')]
            ]
            print(f"\n🔹 Education Entry {i}:")
            print(tabulate(edu_details, tablefmt="fancy_grid", maxcolwidths=[20, 75]))
    else:
        print(f"\n🎓 EDUCATION: No education data found")
    
    print(f"\n{'='*100}\n")


if __name__ == "__main__":
    # Profile URLs to scrape
    profile_urls = [
        "https://www.linkedin.com/in/rohitdoshi9/",
        # Add more URLs here
    ]
    
    driver = setup_driver()
    
    try:
        # Login
        if login_to_linkedin(driver):
            all_profiles = []
            
            # Scrape each profile
            for url in profile_urls:
                profile = scrape_profile(driver, url)
                if profile:
                    all_profiles.append(profile)
                    # Print profile in table format
                    print_profile_table(profile)
                    # Save individual profile
                    save_to_json(profile)
                
                # Human-like delay between profiles
                if len(profile_urls) > 1:
                    delay = 5
                    print(f"⏳ Waiting {delay} seconds before next profile...")
                    sleep(delay)
            
            # Summary
            print(f"\n{'='*100}")
            print(f"🎉 SCRAPING COMPLETE!")
            print(f"{'='*100}")
            print(f"✅ Successfully scraped {len(all_profiles)} out of {len(profile_urls)} profiles\n")
            
            # Summary table
            if all_profiles:
                summary_table = []
                for i, p in enumerate(all_profiles, 1):
                    summary_table.append([
                        i,
                        p['name'],
                        p.get('headline', 'N/A')[:50] + "..." if p.get('headline') and len(p.get('headline', '')) > 50 else p.get('headline', 'N/A'),
                        len(p.get('experience', [])),
                        len(p.get('education', [])),
                        'Yes' if p.get('about') else 'No',
                        '✅'
                    ])
                
                print("📊 FINAL SUMMARY TABLE")
                print(tabulate(summary_table, 
                             headers=["#", "Name", "Headline", "Exp", "Edu", "About", "Status"], 
                             tablefmt="fancy_grid",
                             maxcolwidths=[5, 25, 50, 5, 5, 8, 8]))
                
                # Save all profiles to one file
                with open('all_profiles.json', 'w', encoding='utf-8') as f:
                    json.dump(all_profiles, f, indent=2, ensure_ascii=False)
                print(f"\n💾 All profiles saved to: all_profiles.json")
            else:
                print("❌ No profiles were successfully scraped")
        
        # Keep browser open for inspection
        input("\n\nPress Enter to close browser...")
        
    except KeyboardInterrupt:
        print("\n\n⚠️ Scraping interrupted by user")
    except Exception as e:
        print(f"\n\n❌ Error: {e}")
    finally:
        driver.quit()
        print("\n👋 Browser closed. Goodbye!")
