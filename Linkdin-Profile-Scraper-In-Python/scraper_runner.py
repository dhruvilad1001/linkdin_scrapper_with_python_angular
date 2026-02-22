import os
import re
import requests
import hashlib
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import NoSuchElementException, TimeoutException, ElementClickInterceptedException
from time import sleep
from dotenv import load_dotenv
from pymongo import MongoClient
from datetime import datetime
from bs4 import BeautifulSoup
import logging

# Load environment variables
load_dotenv()

# Logger setup
logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")
logger = logging.getLogger(__name__)

def get_experience_tokens(driver, timeout=15):
    """Scroll and fetch all hidden text tokens from the Experience section.
    Returns [] if section not found."""
    driver.execute_script("window.scrollTo(0, document.body.scrollHeight * 0.35);")

    try:
        exp_section = WebDriverWait(driver, timeout).until(
            EC.presence_of_element_located(
                (By.XPATH, "//section[.//span[text()='Experience']]")
            )
        )
    except TimeoutException:
        logger.info("ℹ️ No 'Experience' section found on this profile.")
        return []  # ✅ return empty list safely

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
        # Company names are always preserved
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

        # Skip junk designations, but never skip companies
        if looks_like_description(designation):
            designation = ""

        # 🚨 Ensure company is always kept if it contains company-like keywords
        if company and any(kw in company.lower() for kw in ["pvt", "inc", "solutions", "system", "hr", "ltd"]):
            pass  # keep as company
        elif looks_like_description(company, is_company=True):
            company = ""

        # Skip completely empty
        if not designation and not company:
            continue

        # Append cleaned record
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

def scrape_education(driver):
    """Scrape education section"""
    try:
        # Try scrolling to education section
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
            logger.info("✅ Clicked 'See all education' button")
            clicked_see_all_education = True
        except Exception:
            logger.info("ℹ️ No 'See all education' button, scraping from main profile page")

        # Get page source and parse
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

        # Process each education block
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

        logger.info(f"✅ Found {len(education_data)} education entries")

        # Go back if we clicked see all education
        if clicked_see_all_education:
            driver.back()
            sleep(2)

        return education_data

    except Exception as e:
        logger.warning(f"❌ Error in education section: {e}")
        return []

def scrape_licenses_and_certifications(driver):
    """Scrape licenses and certifications"""
    try:
        driver.execute_script("window.scrollTo(0, document.body.scrollHeight * 0.7);")
        sleep(2)

        clicked_see_all_licenses = False
        item_list = []

        # Try clicking "See all licenses"
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
            logger.info("✅ Clicked 'see all licenses' button")
            clicked_see_all_licenses = True

        except (NoSuchElementException, TimeoutException):
            logger.info("ℹ️ 'See all licenses' button not found, scraping from main profile page")

        # Parse page source
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

        # Extract license data
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

        logger.info(f"✅ Found {len(item_list)} license/certification entries")

        # Go back if we navigated into the "see all" page
        if clicked_see_all_licenses:
            driver.back()
            sleep(2)

        return item_list

    except Exception as e:
        logger.warning(f"❌ Error in licenses section: {e}")
        return []

def scrape_projects(driver):
    """Scrape projects section"""
    try:
        # Try to find and click "see all projects" button
        clicked_see_all_projects = False
        try:
            see_all_projects_btn = driver.find_element(By.ID, "navigation-index-see-all-projects")
            see_all_projects_btn.click()
            sleep(3)
            logger.info("✅ Clicked 'see all projects' button")
            clicked_see_all_projects = True
        except NoSuchElementException:
            logger.info("ℹ️ 'See all projects' button not found, scraping from main profile page")

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

        logger.info(f"✅ Found {len(item_list)} project entries")
        
        # Go back if we clicked see all projects
        if clicked_see_all_projects:
            driver.back()
            sleep(2)

        return item_list

    except Exception as e:
        logger.warning(f"❌ Error in projects section: {e}")
        return []

def scrape_courses(driver):
    """Scrape courses section"""
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

        logger.info(f"✅ Found {len(courses_list)} course entries")
        return courses_list

    except Exception as e:
        logger.warning(f"❌ Error in courses section: {e}")
        return []

def scrape_honors_awards(driver):
    """Scrape honors and awards section"""
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
            logger.info("✅ Clicked 'see all honors & awards' button")
            clicked_see_all_awards = True
        except (NoSuchElementException, TimeoutException):
            logger.info("ℹ️ 'See all honors & awards' button not found, scraping from main profile page")

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

        logger.info(f"✅ Found {len(awards_list)} honors & awards entries")

        # Go back if we clicked "See all honors & awards"
        if clicked_see_all_awards:
            driver.back()
            sleep(2)

        return awards_list

    except Exception as e:
        logger.warning(f"❌ Error in honors & awards section: {e}")
        return []

def scrape_profile_picture(driver, name, profile_url):
    """Scrape profile picture"""
    try:
        # Find profile picture
        img_element = driver.find_element(By.CSS_SELECTOR, "img[alt*='profile photo']")
        img_url = img_element.get_attribute("src")
        
        if img_url:
            # Create directory if it doesn't exist
            os.makedirs("profile_pictures", exist_ok=True)
            
            # Generate filename
            safe_name = re.sub(r'[^a-zA-Z0-9_]', '_', name)
            filename = f"profile_pictures/{safe_name}_profile_picture.jpg"
            
            # Download image
            response = requests.get(img_url)
            if response.status_code == 200:
                with open(filename, 'wb') as f:
                    f.write(response.content)
                logger.info(f"✅ Profile picture saved: {filename}")
                return filename
            else:
                logger.warning(f"⚠️ Failed to download profile picture: {response.status_code}")
                return None
        else:
            logger.info("ℹ️ No profile picture found")
            return None
            
    except Exception as e:
        logger.warning(f"⚠️ Error scraping profile picture: {e}")
        return None

def run_linkedin_scraper(profile_url):
    """
    Scrapes a LinkedIn profile and saves/updates it in MongoDB.
    If profile exists, it will be updated with new data.
    """
    try:
        # MongoDB connection
        client = MongoClient(os.getenv("MONGO_URI", "mongodb://localhost:27017/"))
        db = client[os.getenv("DATABASE_NAME", "Linkedin")]
        collection = db[os.getenv("COLLECTION_NAME", "profile_data")]

        # Check if profile already exists
        existing_profile = collection.find_one({"url": profile_url})
        is_update = existing_profile is not None
        
        if is_update:
            logger.info(f"🔄 Profile exists, will update: {profile_url}")
        else:
            logger.info(f"🆕 New profile, will create: {profile_url}")

        # Chrome options
        chrome_options = Options()
        chrome_options.add_argument("--headless=new")
        chrome_options.add_argument("--no-sandbox")
        chrome_options.add_argument("--disable-dev-shm-usage")
        chrome_options.add_argument("--disable-blink-features=AutomationControlled")
        chrome_options.add_argument("--window-size=1920,1080")

        driver = webdriver.Chrome(options=chrome_options)
        wait = WebDriverWait(driver, 20)

        try:
            # --- LOGIN ---
            logger.info("🔐 Logging into LinkedIn...")
            driver.get("https://www.linkedin.com/login")
            sleep(2)

            email = os.getenv("Email")
            password = os.getenv("Password")

            if not email or not password:
                raise ValueError("LinkedIn Email or Password not found in .env file")

            driver.find_element(By.ID, "username").send_keys(email)
            driver.find_element(By.ID, "password").send_keys(password, Keys.RETURN)
            sleep(5)

            # --- PROFILE LOAD ---
            logger.info(f"📄 Loading profile: {profile_url}")
            driver.get(profile_url)
            wait.until(EC.presence_of_element_located((By.TAG_NAME, "body")))
            sleep(3)

            # Scroll to load dynamic content
            for _ in range(5):
                driver.execute_script("window.scrollBy(0, 800);")
                sleep(1)

            page_source = driver.page_source
            soup = BeautifulSoup(page_source, "lxml")

            # --- NAME ---
            logger.info("👤 Extracting name...")
            try:
                name_elem = soup.find("h1", class_="text-heading-xlarge")
                if not name_elem:
                    name_elem = soup.find("h1")
                name = name_elem.get_text(strip=True) if name_elem else "N/A"
            except:
                name = "N/A"

            # --- HEADLINE ---
            logger.info("💼 Extracting headline...")
            try:
                headline = soup.find("div", class_="text-body-medium").get_text(strip=True)
            except:
                headline = "N/A"

            # --- ABOUT ---
            logger.info("📝 Extracting about section...")
            try:
                # Try clicking show more for about
                try:
                    driver.find_element(By.CLASS_NAME, "inline-show-more-text__button").click()
                    sleep(1)
                    page_source = driver.page_source
                    soup = BeautifulSoup(page_source, "lxml")
                except:
                    pass

                about_div = soup.find('div', {'class': 'display-flex ph5 pv3'})
                if not about_div:
                    about_div = soup.find('section', {'id': 'about'})
                about = about_div.get_text(strip=True) if about_div else "N/A"
            except:
                about = "N/A"

            # --- EXPERIENCE ---
            logger.info("💼 Extracting experience...")
            tokens = get_experience_tokens(driver)
            if tokens:
                experience = parse_experience_tokens(tokens)
            else:
                experience = []

            # --- EDUCATION ---
            logger.info("🎓 Extracting education...")
            education = scrape_education(driver)

            # --- PROJECTS ---
            logger.info("🚀 Extracting projects...")
            projects = scrape_projects(driver)

            # --- LICENSES/CERTIFICATIONS ---
            logger.info("📜 Extracting licenses & certifications...")
            licenses = scrape_licenses_and_certifications(driver)

            # --- COURSES ---
            logger.info("📚 Extracting courses...")
            courses = scrape_courses(driver)

            # --- HONORS & AWARDS ---
            logger.info("🏆 Extracting honors & awards...")
            honors_awards = scrape_honors_awards(driver)

            # --- PROFILE PICTURE ---
            logger.info("📸 Extracting profile picture...")
            profile_picture_path = scrape_profile_picture(driver, name, profile_url)

            # --- PREPARE PROFILE DATA ---
            logger.info("💾 Preparing profile data...")
            profile_data = {
                "name": name,
                "url": profile_url,
                "headline": headline,
                "about": about,
                "experience": experience,
                "education": education,
                "projects": projects,
                "licenses": licenses,
                "courses": courses,
                "honors_awards": honors_awards,
                "profile_picture": profile_picture_path,
                "last_updated": datetime.now()
            }
            
            # Add scraped_at only for new profiles
            if not is_update:
                profile_data["scraped_at"] = datetime.now()

            # --- SAVE OR UPDATE TO MONGODB ---
            logger.info("💾 Saving to database...")
            if is_update:
                # Update existing profile
                collection.update_one(
                    {"url": profile_url},
                    {"$set": profile_data}
                )
                logger.info(f"✅ Profile updated successfully: {name}")
            else:
                # Insert new profile
                collection.insert_one(profile_data)
                logger.info(f"✅ New profile saved successfully: {name}")

            return True, f"Successfully scraped profile: {name}"

        finally:
            driver.quit()

    except Exception as e:
        logger.error(f"❌ Scraping failed for {profile_url}: {str(e)}")
        return False, f"Scraping failed: {str(e)}"

    finally:
        if 'client' in locals():
            client.close()

if __name__ == "__main__":
    # Test with a profile URL
    test_url = "https://www.linkedin.com/in/rohitdoshi9/"
    success, message = run_linkedin_scraper(test_url)
    print(f"Result: {success}, Message: {message}")