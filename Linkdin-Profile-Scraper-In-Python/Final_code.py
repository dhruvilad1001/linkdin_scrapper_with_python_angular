#-------------------------Basic_Info

import warnings
warnings.filterwarnings("ignore")

import os 
from bs4 import BeautifulSoup
from selenium import webdriver
from selenium.webdriver.common.by import By

from time import sleep

from dotenv import load_dotenv
load_dotenv()

os.environ['Email'],os.environ['Password']

driver = webdriver.Chrome()

driver.get('https://www.linkedin.com/login')

email = driver.find_element(By.ID,'username')
email.send_keys(os.environ['Email'])

password = driver.find_element(By.ID,'password')
password.send_keys(os.environ['Password'])

password.submit()

# url = "https://www.linkedin.com/in/savaliya-mukund27/"
# url = "https://www.linkedin.com/in/mitkumar-patel-031917266/"
# url = "https://www.linkedin.com/in/dhruvi-lad-7a900b352/"
# url = "https://www.linkedin.com/in/yoganshijadav/"
# url = "https://www.linkedin.com/in/shahanavaz-diwan/"
# url = "https://www.linkedin.com/in/daksha-thakkar-79a98577/"
# url = "https://www.linkedin.com/in/pankaj-sonagara/"
url = "https://www.linkedin.com/in/sonagara-alpaben2411/"
driver.get(url)

profile_data = {}

page_source = driver.page_source
soup = BeautifulSoup(page_source,'lxml')

name = soup.find("h1")
if name:
    print(name.get_text().strip())
else:
    print("Name not found")

profile_data['name'] = name.get_text(strip=True) if name else None
profile_data['url'] = url

profile_data

headline = soup.find('div',{'class': 'text-body-medium break-words'})
headline = headline.get_text().strip()

profile_data['headline'] = headline

profile_data

#-------------------------About

from selenium.common.exceptions import NoSuchElementException

try:
    driver.find_element(By.CLASS_NAME,"inline-show-more-text__button").click()
except NoSuchElementException:
    pass  # Button not present → ignore

page_source = driver.page_source
soup = BeautifulSoup(page_source, 'lxml')

about_div = soup.find('div', {'class': 'display-flex ph5 pv3'})
if not about_div:  # fallback: sometimes it's in a <section>
    about_div = soup.find('section', {'id': 'about'})

if about_div:
    about = about_div.get_text().strip()
    profile_data['about'] = about if about else None
else:
    profile_data['about'] = None

profile_data

#-------------------------Experience

import re, json
from bs4 import BeautifulSoup
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.common.by import By


def get_experience_structured(driver, timeout=15):
    """Scrape experience section with proper company grouping."""
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

    # Expand any "Show more experiences" buttons
    try:
        show_more_btns = driver.find_elements(By.XPATH, 
            "//button[contains(@aria-label, 'Show more experiences at') or contains(., 'Show more experience')]")
        for btn in show_more_btns:
            try:
                driver.execute_script("arguments[0].click();", btn)
                sleep(0.5)
            except:
                pass
    except:
        pass

    exp_html = exp_section.get_attribute("outerHTML")
    exp_soup = BeautifulSoup(exp_html, "lxml")

    # Find all experience blocks
    exp_blocks = exp_soup.find_all("li", {"class": ["artdeco-list__item", "pvs-list__paged-list-item"]})
    
    if not exp_blocks:
        print("ℹ️ No experience blocks found")
        return []

    roles_set = {
        "Full-time", "Part-time", "Internship", "Contract", "Self-employed",
        "Freelance", "Apprenticeship", "Volunteer", "Temporary", "Seasonal"
    }
    skip_tokens = ("connection", "connections", "mutual", "profile", "view profile", "followers", "follow", "connect")

    def is_duration(s: str) -> bool:
        if not s: return False
        s2 = s.lower()
        return (" to " in s2 and ("present" in s2 or "mo" in s2 or "yr" in s2)) or (" yr" in s2) or (" mo" in s2)

    def is_location(s: str) -> bool:
        if not s or is_duration(s) or s in roles_set: return False
        loc_keywords = ["india", "remote", "on-site", "hybrid", "onsite", "work from home"]
        return any(k in s.lower() for k in loc_keywords) or ("," in s and len(s.split()) >= 2)

    def clean_company(s: str) -> str:
        if not s: return ""
        result = s
        for r in roles_set:
            result = result.replace(f"· {r}", "").replace(r, "")
        return result.strip("· ").strip()

    def extract_tokens(block):
        spans = block.find_all("span", {"class": "visually-hidden"})
        tokens = []
        for span in spans:
            text = span.get_text(strip=True)
            if not text: continue
            lower = text.lower()
            if any(bad in lower for bad in skip_tokens): continue
            tokens.append(text)
        # Remove duplicates while preserving order
        deduped = []
        for token in tokens:
            if deduped and deduped[-1] == token: continue
            deduped.append(token)
        return deduped

    companies = {}  # company_name -> {company_info, designations: []}

    for block in exp_blocks:
        # Skip suggestion blocks
        block_text = block.get_text(" ", strip=True).lower()
        if any(keyword in block_text for keyword in ["connect", "message", "follow", "view profile"]):
            continue

        # Check if this block has nested roles (sub-list)
        nested_list = block.find("ul")
        if nested_list:
            # This is a company block with multiple roles
            tokens = extract_tokens(block)
            company_name = ""
            total_duration = ""
            
            # Extract company name and total duration from parent block
            for token in tokens:
                if not company_name and not is_duration(token) and not is_location(token) and token not in roles_set:
                    company_name = clean_company(token)
                elif is_duration(token) and not total_duration:
                    total_duration = token
                    break  # Stop after finding first duration (total company duration)
                    
            if not company_name:
                continue
                
            # Initialize company entry
            if company_name not in companies:
                companies[company_name] = {
                    "company_name": company_name,
                    "duration": total_duration,
                    "designations": []
                }
            
            # Process each role within this company
            nested_items = nested_list.find_all("li", {"class": ["artdeco-list__item", "pvs-list__paged-list-item"]}, recursive=False)
            for nested_item in nested_items:
                role_tokens = extract_tokens(nested_item)
                role_info = {
                    "designation": "",
                    "duration": "",
                    "location": "",
                    "role": ""
                }
                
                for token in role_tokens:
                    stripped = token.strip()
                    
                    # Skip parent company name
                    if company_name and stripped.lower() == company_name.lower():
                        continue
                        
                    if stripped in roles_set and not role_info["role"]:
                        role_info["role"] = stripped
                    elif not role_info["designation"] and not is_duration(stripped) and not is_location(stripped):
                        role_info["designation"] = stripped
                    elif is_duration(stripped) and not role_info["duration"]:
                        role_info["duration"] = stripped
                    elif is_location(stripped) and not role_info["location"]:
                        role_info["location"] = stripped
                        
                if role_info["designation"]:  # Only add if we have a valid designation
                    companies[company_name]["designations"].append(role_info)
        else:
            # This is a single role block (no nested structure)
            tokens = extract_tokens(block)
            if not tokens:
                continue
                
            # Try to extract company and role from the same block
            company_name = ""
            role_info = {
                "designation": "",
                "duration": "",
                "location": "",
                "role": ""
            }
            
            for token in tokens:
                stripped = token.strip()
                
                if stripped in roles_set and not role_info["role"]:
                    role_info["role"] = stripped
                elif not role_info["designation"] and not is_duration(stripped) and not is_location(stripped):
                    if not company_name:
                        company_name = clean_company(stripped)
                    else:
                        role_info["designation"] = stripped
                elif is_duration(stripped) and not role_info["duration"]:
                    role_info["duration"] = stripped
                elif is_location(stripped) and not role_info["location"]:
                    role_info["location"] = stripped
            
            if company_name and role_info["designation"]:
                if company_name not in companies:
                    companies[company_name] = {
                        "company_name": company_name,
                        "duration": role_info["duration"],  # Use role duration as company duration for single roles
                        "designations": []
                    }
                companies[company_name]["designations"].append(role_info)

    # Convert to list format
    experiences = list(companies.values())
    
    print(f"✅ Found {len(experiences)} companies with {sum(len(exp['designations']) for exp in experiences)} total roles")
    return experiences

# ---------- Usage ----------
if __name__ == "__main__":
    # Get structured experience data with proper company grouping
    experience_struct = get_experience_structured(driver)
    
    # Store into profile_data
    profile_data["experience"] = experience_struct

profile_data

#-------------------------Education

try:
    # -------------------------
    # Try scrolling to education section
    # -------------------------
    driver.execute_script("window.scrollTo(0, document.body.scrollHeight * 0.5);")
    sleep(2)

    clicked_see_all_education = False

    # -------------------------
    # Try clicking "See all education" if it exists
    # -------------------------
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

    # -------------------------
    # Get page source and parse
    # -------------------------
    page_source = driver.page_source
    soup = BeautifulSoup(page_source, "lxml")

    education_data = []

    if clicked_see_all_education:
        # We're on dedicated education page
        edu_section = soup.find("section", {"class": "artdeco-card pb3"})
        if edu_section:
            edu_blocks = edu_section.find_all("li", {"class": "pvs-list__paged-list-item"})
        else:
            edu_blocks = soup.find_all("li", {"class": "pvs-list__paged-list-item"})
    else:
        # We're on main profile page
        edu_sections = driver.find_elements(By.XPATH, "//section[.//span[text()='Education']]")
        if edu_sections:
            edu_html = edu_sections[0].get_attribute("outerHTML")
            edu_soup = BeautifulSoup(edu_html, "lxml")
            edu_blocks = edu_soup.find_all("li", {"class": "artdeco-list__item"})
            if not edu_blocks:
                edu_blocks = edu_soup.find_all("li", {"class": "pvs-list__paged-list-item"})
        else:
            edu_blocks = []

    # -------------------------
    # Process each education block
    # -------------------------
    for block in edu_blocks:
        spans = block.find_all("span", {"class": "visually-hidden"})
        if not spans:
            continue

        edu_dict = {}
        # Map spans safely
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

    profile_data["education"] = education_data
    print(f"✅ Found {len(education_data)} education entries")

    # -------------------------
    # Go back if we clicked see all education
    # -------------------------
    if clicked_see_all_education:
        driver.back()
        sleep(2)

except Exception as e:
    print(f"❌ Error in education section: {e}")
    profile_data["education"] = []

profile_data

#-------------------------Certificate

from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import NoSuchElementException, TimeoutException, ElementClickInterceptedException
from time import sleep
from bs4 import BeautifulSoup

try:
    driver.execute_script("window.scrollTo(0, document.body.scrollHeight * 0.7);")
    sleep(2)

    clicked_see_all_licenses = False
    item_list = []

    # --- Try clicking "See all licenses" ---
    try:
        see_all_btn = WebDriverWait(driver, 5).until(
            EC.presence_of_element_located((By.ID, "navigation-index-see-all-licenses-and-certifications"))
        )
        driver.execute_script("arguments[0].scrollIntoView({block: 'center'});", see_all_btn)
        sleep(1)
        try:
            see_all_btn.click()
        except ElementClickInterceptedException:
            driver.execute_script("arguments[0].click();", see_all_btn)

        sleep(3)
        print("✅ Clicked 'see all licenses' button")
        clicked_see_all_licenses = True

    except (NoSuchElementException, TimeoutException):
        print("ℹ️ 'See all licenses' button not found, scraping from main profile page")

    # --- Parse page source ---
    page_source = driver.page_source
    soup = BeautifulSoup(page_source, 'lxml')

    items = []

    if clicked_see_all_licenses:
        # Dedicated "see all" licenses page
        licenses_section = soup.find('section', {'class': 'artdeco-card pb3'})
        if licenses_section:
            items = licenses_section.find_all('li', {'class': 'pvs-list__paged-list-item'})
    else:
        # Try finding licenses on the main profile page
        licenses_section = soup.find("section", {"class": "artdeco-card"}, 
                                     string=lambda t: t and ("Licenses" in t or "Certifications" in t))
        if not licenses_section:
            # Another fallback → find any <section> with heading span
            for sec in soup.find_all("section", {"class": "artdeco-card"}):
                header = sec.find("h2")
                if header and any("License" in s.get_text() or "Certification" in s.get_text() 
                                  for s in header.find_all("span")):
                    licenses_section = sec
                    break

        if licenses_section:
            items = licenses_section.find_all("li", {"class": ["artdeco-list__item", "pvs-list__paged-list-item"]})

    # --- Extract license data ---
    def get_license(item):
        spans = item.find_all('span', {'class': 'visually-hidden'})
        filtered = [s.get_text(strip=True) for s in spans
                    if not any(k in s.get_text(strip=True).lower()
                               for k in ['connection', 'mutual', 'profile', 'view', 'connect'])]
        return {
            "name": filtered[0] if len(filtered) > 0 else None,
            "institute": filtered[1] if len(filtered) > 1 else None,
            "issued_date": filtered[2] if len(filtered) > 2 else None,
        }

    for item in items:
        license_data = get_license(item)
        if license_data["name"]:  # Only keep valid entries
            item_list.append(license_data)

    profile_data['licenses'] = item_list
    print(f"✅ Found {len(item_list)} license/certification entries")

    # Go back if we navigated into the "see all" page
    if clicked_see_all_licenses:
        driver.back()
        sleep(2)

except Exception as e:
    print(f"❌ Error in licenses section: {e}")
    profile_data['licenses'] = []

profile_data


#-------------------------Project

try:
    # Try to find and click "see all projects" button
    try:
        see_all_projects_btn = driver.find_element(By.ID, "navigation-index-see-all-projects")
        see_all_projects_btn.click()
        sleep(3)
        print("✅ Clicked 'see all projects' button")
        clicked_see_all_projects = True
    except NoSuchElementException:
        print("ℹ️ 'See all projects' button not found, scraping from main profile page")
        clicked_see_all_projects = False

    page_source = driver.page_source
    soup = BeautifulSoup(page_source, 'lxml')

    if clicked_see_all_projects:
        # We're on the dedicated projects page
        projects_section = soup.find('section', {'class': 'artdeco-card pb3'})
        if projects_section:
            items = projects_section.find_all('li', {'class': 'pvs-list__paged-list-item'})
        else:
            items = soup.find_all('li', {'class': 'pvs-list__paged-list-item'})
    else:
        # Try to find projects on main profile page
        try:
            projects_section = WebDriverWait(driver, 10).until(
                EC.presence_of_element_located((By.XPATH, "//section[.//span[text()='Projects']]"))
            )
            projects_html = projects_section.get_attribute("outerHTML")
            projects_soup = BeautifulSoup(projects_html, "lxml")
            items = projects_soup.find_all("li", {"class": "artdeco-list__item"})
            if not items:
                items = projects_soup.find_all("li", {"class": "pvs-list__paged-list-item"})
        except:
            items = []

    def get_project(item): 
        spans = item.find_all('span', {'class': 'visually-hidden'})
        item_dict = {}

        # Filter out connection/profile related spans
        filtered_spans = []
        for span in spans:
            text = span.get_text().strip().lower()
            if not any(keyword in text for keyword in ['connection', 'mutual', 'profile', 'view']):
                filtered_spans.append(span.get_text().strip())

        if len(filtered_spans) > 0:
            item_dict['project_name'] = filtered_spans[0]
        if len(filtered_spans) > 1:
            item_dict['duration'] = filtered_spans[1]
        if len(filtered_spans) > 2:
            item_dict['description'] = filtered_spans[2]
        if len(filtered_spans) > 3:
            item_dict['skills'] = filtered_spans[3]

        return item_dict

    item_list = []
    for item in items:
        project_data = get_project(item)
        if project_data.get('project_name'):
            item_list.append(project_data)

    profile_data['projects'] = item_list
    print(f"✅ Found {len(item_list)} project entries")
    
    # Go back if we clicked see all projects
    if clicked_see_all_projects:
        driver.back()
        sleep(2)

except Exception as e:
    print(f"❌ Error in projects section: {e}")
    profile_data['projects'] = []
profile_data['projects'] = item_list

profile_data


#-------------------------courses

try:
    # Scroll to find courses section
    driver.execute_script("window.scrollTo(0, document.body.scrollHeight * 0.8);")
    sleep(2)

    page_source = driver.page_source
    soup = BeautifulSoup(page_source, 'lxml')

    # Try to find courses section
    courses_list = []
    
    try:
        # Look for courses in the main profile
        courses_section = WebDriverWait(driver, 5).until(
            EC.presence_of_element_located((By.XPATH, "//section[.//span[contains(text(), 'Course')]]"))
        )
        courses_html = courses_section.get_attribute("outerHTML")
        courses_soup = BeautifulSoup(courses_html, "lxml")
        items = courses_soup.find_all("li", {"class": "artdeco-list__item"})
        if not items:
            items = courses_soup.find_all("li", {"class": "pvs-list__paged-list-item"})
    except:
        # Fallback - search for any course-like items
        items = soup.find_all('li', {'class': 'pvs-list__paged-list-item'})

    for item in items:
        # Skip items that are clearly "more profiles for you" recommendations
        item_text_lower = item.get_text(" ", strip=True).lower()
        if any(keyword in item_text_lower for keyword in [
            'more profiles for you', 
            'people also viewed', 
            'people you may know',
            'view profile',
            'connect',
            'message',
            'follow'
        ]):
            continue
        
        spans = item.find_all('span', {'class': 'visually-hidden'})
        
        # Filter relevant spans
        filtered_spans = []
        for span in spans:
            text = span.get_text().strip().lower()
            if not any(keyword in text for keyword in ['connection', 'mutual', 'profile', 'view']):
                filtered_spans.append(span.get_text().strip())
        
        if len(filtered_spans) >= 2:  # At least course name and associated with
            item_dict = {}
            item_dict['course_name'] = filtered_spans[0] if len(filtered_spans) > 0 else ""
            item_dict['associated_with'] = filtered_spans[1] if len(filtered_spans) > 1 else ""
            courses_list.append(item_dict)

    profile_data["courses"] = courses_list
    print(f"✅ Found {len(courses_list)} course entries")

except Exception as e:
    print(f"❌ Error in courses section: {e}")
    profile_data["courses"] = []

profile_data


#-------------------------Awards

try:
    # Scroll near the honors section
    driver.execute_script("window.scrollTo(0, document.body.scrollHeight * 0.7);")
    sleep(2)

    clicked_see_all_awards = False

    # Try clicking "See all honors and awards"
    try:
        see_all_awards_btn = WebDriverWait(driver, 5).until(
            EC.presence_of_element_located((By.ID, "navigation-index-see-all-honorsandawards"))
        )
        driver.execute_script("arguments[0].scrollIntoView({block: 'center'});", see_all_awards_btn)
        sleep(1)
        try:
            see_all_awards_btn.click()
        except ElementClickInterceptedException:
            driver.execute_script("arguments[0].click();", see_all_awards_btn)

        sleep(3)
        print("✅ Clicked 'see all honors & awards' button")
        clicked_see_all_awards = True
    except (NoSuchElementException, TimeoutException):
        print("ℹ️ 'See all honors & awards' button not found, scraping from main profile page")

    # Get current page source after possible navigation
    page_source = driver.page_source
    soup = BeautifulSoup(page_source, 'lxml')

    awards_list = []

    if clicked_see_all_awards:
        # Dedicated awards page
        awards_section = soup.find("section", {"class": "artdeco-card pb3"})
        if awards_section:
            award_cards = awards_section.find_all("li", {"class": "pvs-list__paged-list-item"})
        else:
            award_cards = soup.find_all("li", {"class": "pvs-list__paged-list-item"})
    else:
        # Main profile page
        potential_awards_sections = soup.find_all("section", {"class": "artdeco-card pv-profile-card break-words mt2"})
        awards_section = None
        for section in potential_awards_sections:
            header = section.find("h2", class_="pvs-header__title")
            if header and any("Honors & awards" in span.get_text(strip=True) for span in header.find_all("span")):
                awards_section = section
                break
        if awards_section:
            award_cards = awards_section.find_all("li", {"class": "artdeco-list__item"})
        else:
            award_cards = []

    # Extract award info
    for card in award_cards:
        spans = [s.get_text(strip=True) for s in card.find_all("span", {"class": "visually-hidden"})]
        filtered_spans = [
            span for span in spans
            if not any(x in span.lower() for x in ["connection", "studied at", "view profile"])
        ]

        if filtered_spans:
            award_dict = {}
            if len(filtered_spans) >= 1:
                award_dict['award_name'] = filtered_spans[0]
            if len(filtered_spans) >= 2:
                parts = filtered_spans[1].split('·')
                award_dict['issued_by'] = parts[0].replace('Issued by', '').strip()
                if len(parts) > 1:
                    award_dict['issued_date'] = parts[1].strip()
            if len(filtered_spans) >= 3:
                award_dict['associated_with'] = filtered_spans[2].replace('Associated with', '').strip()

            awards_list.append(award_dict)

    profile_data['honors_awards'] = awards_list
    print(f"✅ Found {len(awards_list)} honors & awards entries")

    # Go back if we clicked "See all honors & awards"
    if clicked_see_all_awards:
        driver.back()
        sleep(2)

except Exception as e:
    print(f"❌ Error in honors & awards section: {e}")
    profile_data['honors_awards'] = []

profile_data

#------------------------- name.json file

import json
import re

user_name = profile_data.get("name", "default_user")

safe_name = re.sub(r'[^a-zA-Z0-9_]', '_', user_name)

file_name = f"{safe_name}_profile_data.json"

with open(file_name, 'w') as f:
    json.dump(profile_data, f, indent=4)

print(f"JSON file created: {file_name}")


#-------------------------save data mongodb

import json
import glob
import os
from pymongo import MongoClient
from datetime import datetime

# MongoDB connection details
MONGO_URI = "mongodb://localhost:27017/"
DATABASE_NAME = "Linkedin"
COLLECTION_NAME = "profile_data"

# Folder where all JSON profile files are stored
JSON_FOLDER_PATH = r"D:\Linkdin-Profile-Scraper-In-Python"

try:
    client = MongoClient(MONGO_URI)
    db = client[DATABASE_NAME]
    collection = db[COLLECTION_NAME]

    # Step 0: Remove existing duplicates (keep one document per URL)
    pipeline = [
        {"$group": {"_id": "$url", "ids": {"$addToSet": "$_id"}, "count": {"$sum": 1}}},
        {"$match": {"count": {"$gt": 1}}}
    ]
    duplicates = list(collection.aggregate(pipeline))
    for doc in duplicates:
        ids = doc["ids"]
        ids.pop(0)  # Keep one, delete the rest
        collection.delete_many({"_id": {"$in": ids}})
    print(f"✅ Removed {len(duplicates)} duplicate URLs (if any)")

    # Step 1: Ensure unique index on URL
    collection.create_index("url", unique=True)
    print("✅ Unique index created successfully")

    # Step 2: Process JSON files
    json_files = glob.glob(os.path.join(JSON_FOLDER_PATH, "*.json"))

    def save_profile(profile):
        profile["last_updated"] = datetime.utcnow()
        collection.update_one(
            {"url": profile.get("url")},
            {"$set": profile},
            upsert=True
        )

    total = 0
    for file_path in json_files:
        with open(file_path, "r", encoding="utf-8") as file:
            file_data = json.load(file)

            if isinstance(file_data, list):
                for profile in file_data:
                    save_profile(profile)
                    total += 1
            else:
                save_profile(file_data)
                total += 1

        print(f"✅ Processed file: {os.path.basename(file_path)}")

    print(f"🎯 Total profiles processed: {total}")

except Exception as e:
    print(f"Error: {e}")
finally:
    if 'client' in locals() and client:
        client.close()

#-------------------------insert JSON → clean → export to Excel

import os
import re
import pandas as pd
from typing import Dict, List, Any
from pymongo import MongoClient

# ---------- CONFIG ----------
MONGO_URI = "mongodb://localhost:27017/"
DATABASE_NAME = "Linkedin"
COLLECTION_NAME = "profile_data"
OUTPUT_EXCEL_PATH = "grouped_profile_data.xlsx"
# ----------------------------


# ---------- Cleaning helpers ----------
def clean_text_data(text: Any, aggressive_remove_symbols: bool = False) -> str:
    if text is None:
        return ""
    s = str(text)
    replacements = {
        'Ã¢â‚¬Â¢': '•', 'Ã‚Â·': '·', 'Ã¢â‚¬â„¢': "'", 'Ã¢â‚¬Å"': '"', 'Ã¢â‚¬': '"',
        '\u2022': '•', '\xa0': ' ', '\u200b': ''
    }
    for k, v in replacements.items():
        s = s.replace(k, v)
    s = re.sub(r'[\x00-\x1F\x7F]+', ' ', s)
    s = re.sub(r'\r\n|\r|\n', ' | ', s)
    s = re.sub(r'\s+', ' ', s).strip()
    if aggressive_remove_symbols:
        s = re.sub(r"[^0-9A-Za-z\s\.,@:/\-\(\)\|%'\"]+", '', s)
    return s


def recursive_clean(obj: Any, aggressive_remove_symbols: bool = False) -> Any:
    if isinstance(obj, str):
        return clean_text_data(obj, aggressive_remove_symbols)
    elif isinstance(obj, dict):
        return {k: recursive_clean(v, aggressive_remove_symbols) for k, v in obj.items()}
    elif isinstance(obj, list):
        return [recursive_clean(v, aggressive_remove_symbols) for v in obj]
    else:
        return obj
# --------------------------------------


# ---------- Duration / location extraction ----------
def extract_duration_info(duration_str: str) -> Dict[str, str]:
    if not duration_str:
        return {"duration": "", "start_date": "", "end_date": ""}
    s = duration_str.strip()
    pattern1 = r'(\w{3}\s\d{4})\s+to\s+(\w{3}\s\d{4}|\w+)\s+·\s+(.+)'
    m1 = re.search(pattern1, s)
    if m1:
        return {"duration": clean_text_data(m1.group(3)), "start_date": m1.group(1), "end_date": m1.group(2)}
    pattern2 = r'(\d+\s+(?:yr|mo)s?(?:\s+\d+\s+(?:yr|mo)s?)?)'
    m2 = re.search(pattern2, s)
    if m2:
        return {"duration": m2.group(1), "start_date": "", "end_date": ""}
    return {"duration": clean_text_data(s), "start_date": "", "end_date": ""}


def extract_location_info(location_str: str) -> Dict[str, str]:
    if not location_str:
        return {"city": "", "state": "", "country": "", "work_mode": ""}
    s = clean_text_data(location_str)
    work_mode_pattern = r'\b(Remote|On-site|Hybrid|Onsite)\b'
    wm = re.search(work_mode_pattern, s, re.IGNORECASE)
    work_mode = wm.group(1) if wm else ""
    s_clean = re.sub(work_mode_pattern, '', s, flags=re.IGNORECASE).strip()
    s_clean = re.sub(r'\s*·\s*', '', s_clean)

    parts = [p.strip() for p in s_clean.split(',') if p.strip()]
    city = parts[0] if len(parts) > 0 else ""
    state = parts[1] if len(parts) > 1 else ""
    country = parts[2] if len(parts) > 2 else (parts[-1] if parts else "")
    return {"city": city, "state": state, "country": country, "work_mode": work_mode}
# ------------------------------------------------------------------------


# ---------- Section processors ----------
def process_experience_data(experience_list: List[Dict]) -> List[Dict]:
    processed_experiences = []
    if not experience_list:
        return processed_experiences
    for exp in experience_list:
        company_name = clean_text_data(exp.get('company_name', ''))
        company_duration = clean_text_data(exp.get('duration', ''))

        designations = exp.get('designations')
        if not designations:
            designations = [{
                "designation": exp.get("designation", ""),
                "duration": exp.get("duration", ""),
                "location": exp.get("location", ""),
                "role": exp.get("role", ""),
                "projects": exp.get("projects", "")
            }]

        for designation in designations:
            duration_info = extract_duration_info(designation.get('duration', ''))
            location_info = extract_location_info(designation.get('location', ''))
            processed_experiences.append({
                'company_name': company_name,
                'designation': clean_text_data(designation.get('designation', '')),
                'employment_type': clean_text_data(designation.get('role', '')),
                'duration': duration_info['duration'],
                'start_date': duration_info['start_date'],
                'end_date': duration_info['end_date'],
                'city': location_info['city'],
                'state': location_info['state'],
                'country': location_info['country'],
                'work_mode': location_info['work_mode'],
                'company_duration': company_duration,
                'projects': clean_text_data(designation.get('projects', ''))
            })
    return processed_experiences


def process_education_data(education_list: List[Dict]) -> List[Dict]:
    processed = []
    for edu in education_list or []:
        d = extract_duration_info(edu.get('duration', ''))
        processed.append({
            'college': clean_text_data(edu.get('college', '')),
            'degree': clean_text_data(edu.get('degree', '')),
            'duration': d['duration'],
            'start_date': d['start_date'],
            'end_date': d['end_date'],
            'grade': clean_text_data(edu.get('grade', ''))
        })
    return processed


def process_projects_data(projects_list: List[Dict]) -> List[Dict]:
    processed = []
    for p in projects_list or []:
        d = extract_duration_info(p.get('duration', ''))
        skills_text = p.get('skills', '') or p.get('description', '')
        skills_match = re.search(r'Skills?:\s*([^·]+)', skills_text or '')
        skills = clean_text_data(skills_match.group(1)) if skills_match else clean_text_data(p.get('skills', ''))
        processed.append({
            'project_name': clean_text_data(p.get('project_name', '')),
            'duration': d['duration'],
            'start_date': d['start_date'],
            'end_date': d['end_date'],
            'description': clean_text_data(p.get('description', '')),
            'skills': skills
        })
    return processed


def process_licenses_data(licenses_list: List[Dict]) -> List[Dict]:
    processed = []
    for lic in licenses_list or []:
        issued = lic.get('issued_date', '')
        m = re.search(r'Issued\s+(\w{3}\s+\d{4})', issued or '')
        issued_clean = m.group(1) if m else clean_text_data(issued)
        processed.append({
            'certification_name': clean_text_data(lic.get('name', '')),
            'issuing_organization': clean_text_data(lic.get('institute', '')),
            'issue_date': issued_clean
        })
    return processed


def process_courses_data(courses_list: List[Dict]) -> List[Dict]:
    processed = []
    for c in courses_list or []:
        processed.append({
            'course_name': clean_text_data(c.get('course_name', '')),
            'associated_with': clean_text_data(c.get('associated_with', ''))
        })
    return processed
# ------------------------------------------------------------------


# ---------- Grouped rows helper ----------
def make_grouped_rows(user_name: str, records: List[Dict]) -> pd.DataFrame:
    if not records:
        return pd.DataFrame()
    df = pd.DataFrame(records)
    df.insert(0, "name", "")
    df.at[0, "name"] = user_name
    return df
# ------------------------------------------------------------------


# ---------- Process profile ----------
def process_profile_data(profile_data: Dict[str, Any]) -> Dict[str, pd.DataFrame]:
    df_map = {}
    user_name = clean_text_data(profile_data.get('name', ''))
    profile_url = clean_text_data(profile_data.get('url', ''))

    # Basic Info
    basic = {
        'name': user_name,
        'url': profile_url,
        'headline': clean_text_data(profile_data.get('headline', '')),
        'about': clean_text_data(profile_data.get('about', '')),
    }
    df_map['Basic_Info'] = pd.DataFrame([basic])

    # Sections
    if profile_data.get('experience'):
        df_map['Experience'] = make_grouped_rows(user_name, process_experience_data(profile_data['experience']))

    if profile_data.get('education'):
        df_map['Education'] = make_grouped_rows(user_name, process_education_data(profile_data['education']))

    if profile_data.get('projects'):
        df_map['Projects'] = make_grouped_rows(user_name, process_projects_data(profile_data['projects']))

    if profile_data.get('licenses'):
        df_map['Certifications'] = make_grouped_rows(user_name, process_licenses_data(profile_data['licenses']))

    if profile_data.get('honors_awards'):
        awards = []
        for a in profile_data['honors_awards']:
            awards.append({
                'award_name': clean_text_data(a.get('award_name', '')),
                'issued_by': clean_text_data(a.get('issued_by', '')),
                'issue_date': clean_text_data(a.get('issued_date', '')),
                'associated_with': clean_text_data(a.get('associated_with', ''))
            })
        df_map['Awards'] = make_grouped_rows(user_name, awards)

    if profile_data.get('courses'):
        df_map['Courses'] = make_grouped_rows(user_name, process_courses_data(profile_data['courses']))

    return df_map
# ------------------------------------------------------------------


# ---------- Export to Excel ----------
def export_collection_to_excel(output_path: str, aggressive_remove_symbols: bool = False):
    try:
        import xlsxwriter
        engine = 'xlsxwriter'
    except Exception:
        try:
            import openpyxl
            engine = 'openpyxl'
        except Exception:
            raise RuntimeError("Install xlsxwriter or openpyxl")

    client = MongoClient(MONGO_URI)
    try:
        db = client[DATABASE_NAME]
        collection = db[COLLECTION_NAME]
        documents = list(collection.find({}))
        if not documents:
            print(f"No documents found in collection '{COLLECTION_NAME}'.")
            return

        combined_data = {
            "Basic_Info": [],
            "Experience": [],
            "Education": [],
            "Projects": [],
            "Certifications": [],
            "Awards": [],
            "Courses": []
        }

        for doc in documents:
            doc_clean = recursive_clean(doc, aggressive_remove_symbols)
            doc_clean.pop('_id', None)
            dfs = process_profile_data(doc_clean)
            for section, df in dfs.items():
                if not df.empty:
                    combined_data[section].append(df)

        with pd.ExcelWriter(output_path, engine=engine) as writer:
            for section, df_list in combined_data.items():
                if df_list:
                    combined_df = pd.concat(df_list, ignore_index=True)
                    combined_df.to_excel(writer, sheet_name=section[:31], index=False)

        print(f"✅ Exported {len(documents)} profiles into grouped sheets at '{output_path}'.")
    finally:
        client.close()
# -------------------------------------------------------------------


if __name__ == "__main__":
    export_collection_to_excel(OUTPUT_EXCEL_PATH, aggressive_remove_symbols=False)

    
