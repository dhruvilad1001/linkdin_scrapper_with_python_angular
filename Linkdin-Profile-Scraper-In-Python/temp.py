#------------------------------ 7th code (updated & stable version) ------------------------------
import os
import pandas as pd
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import NoSuchElementException
from selenium.common.exceptions import TimeoutException
from time import sleep
from dotenv import load_dotenv
from pymongo import MongoClient
from datetime import datetime
from bs4 import BeautifulSoup
import logging

# ===============================
# Load environment variables
# ===============================
load_dotenv()
print("hello")
# ===============================
logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")
logger = logging.getLogger(__name__)

print("hello 2")

def run_linkedin_scraper(profile_url):
    """
    Scrapes a LinkedIn profile (Name, Headline, About, Experience, Education, Projects)
    Saves to MongoDB and exports to Excel.
    """
    print("hello 3")
    try:
        # --- MongoDB Connection ---
        client = MongoClient(os.getenv("MONGO_URI", "mongodb://localhost:27017/"))
        db = client[os.getenv("DATABASE_NAME", "Linkedin")]
        collection = db[os.getenv("COLLECTION_NAME", "profile_data")]

        # --- Chrome Options ---
        chrome_options = Options()
        chrome_options.add_argument("--headless=new")
        chrome_options.add_argument("--no-sandbox")
        chrome_options.add_argument("--disable-dev-shm-usage")
        chrome_options.add_argument("--disable-blink-features=AutomationControlled")
        chrome_options.add_argument("--window-size=1920,1080")

        driver = webdriver.Chrome(options=chrome_options)
        wait = WebDriverWait(driver, 15)

        try:
            # --- Login Phase ---
            driver.get("https://www.linkedin.com/login")
            sleep(2)

            email = os.getenv("Email")
            password = os.getenv("Password")

            if not email or not password:
                raise ValueError("LinkedIn Email or Password not found in .env file")

            driver.find_element(By.ID, "username").send_keys(email)
            driver.find_element(By.ID, "password").send_keys(password, Keys.RETURN)
            sleep(5)

            # --- Scrape Target Profile ---
            driver.get(profile_url)
            wait.until(EC.presence_of_element_located((By.TAG_NAME, "body")))
            sleep(3)

            driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
            sleep(2)

            # Parse HTML with BeautifulSoup for easier extraction
            soup = BeautifulSoup(driver.page_source, "html.parser")

            # --- Name ---
            try:
                name = soup.find("h1").get_text(strip=True)
            except:
                name = "N/A"
            print("DEBUG: Name =", name)

            # --- Headline ---
            try:
                headline = soup.find("div", class_="text-body-medium").get_text(strip=True)
            except:
                headline = "N/A"
            print("DEBUG: Headline =", headline)

            # --- About Section ---
            try:
                try:
                    driver.find_element(By.CLASS_NAME, "inline-show-more-text__button").click()
                    print("DEBUG: Clicked 'See more' button in About section.")
                    sleep(2)
                except NoSuchElementException:
                    print("DEBUG: No 'See more' button found for About section.")
                    pass

                page_source = driver.page_source
                soup = BeautifulSoup(page_source, "lxml")

                about_div = soup.find("div", {"class": "display-flex ph5 pv3"})
                if not about_div:
                    about_div = soup.find("section", {"id": "about"})

                if about_div:
                    about = about_div.get_text().strip()
                    about = about if about else "N/A"
                    print("DEBUG: Extracted About =", about[:120], "...")
                else:
                    about = "N/A"
                    print("DEBUG: About section not found.")
            except Exception as e:
                about = "N/A"
                print(f"DEBUG: Error while extracting About: {e}")

            # --- Experience Section ---

           # --- Experience Section (Improved Token-Based Logic) ---
            experience = []
            try:
                # Scroll near Experience section
                driver.execute_script("window.scrollTo(0, document.body.scrollHeight * 0.35);")
                sleep(2)

                try:
                    exp_section = WebDriverWait(driver, 15).until(
                        EC.presence_of_element_located(
                            (By.XPATH, "//section[.//span[text()='Experience']]")
                        )
                    )
                except TimeoutException:
                    print("ℹ️ No 'Experience' section found on this profile.")
                    exp_section = None

                if exp_section:
                    exp_html = exp_section.get_attribute("outerHTML")
                    exp_soup = BeautifulSoup(exp_html, "lxml")

                    # Extract hidden tokens
                    tokens = [
                        s.get_text(strip=True)
                        for s in exp_soup.select("span.visually-hidden")
                        if s.get_text(strip=True)
                    ]

                    print("DEBUG: Experience Tokens =", tokens[:20])

                    # Parse tokens inline (without external function)
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
                        if not s:
                            return ""
                        for r in roles_set:
                            s = s.replace("· " + r, "").replace(r, "")
                        return s.strip()

                    def looks_like_description(s: str, is_company=False) -> bool:
                        if is_company:
                            return False
                        return (len(s.split()) > 15 or len(s) > 120 or s.lower().endswith((".png", ".jpg", ".jpeg")))

                    # --- Parse structured data ---
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

                        # Handle misclassified tokens
                        if is_duration(designation):
                            dur, designation = designation, ""

                        if looks_like_description(designation):
                            designation = ""

                        if company and any(kw in company.lower() for kw in ["pvt", "inc", "solutions", "system", "hr", "ltd"]):
                            pass
                        elif looks_like_description(company, is_company=True):
                            company = ""

                        if not designation and not company:
                            continue

                        result.append({
                            "company_name": clean_company(company),
                            "designation": designation,
                            "duration": dur,
                            "location": loc
                        })

                    # Filter junk durations
                    experience = [
                        r for r in result
                        if not looks_like_description(r["duration"])
                    ]

                    print("DEBUG: Final Parsed Experience =", experience)
                else:
                    experience = []

            except Exception as e:
                logging.warning(f"⚠️ Experience extraction error: {e}")
                experience = []




            # --- Education Section (Final Fixed Version) ---
            education = []
            try:
                # --- Scroll to bring the Education section into view ---
                try:
                    edu_header = WebDriverWait(driver, 10).until(
                        EC.presence_of_element_located((By.XPATH, "//span[contains(text(),'Education')]"))
                    )
                    driver.execute_script("arguments[0].scrollIntoView(true);", edu_header)
                    sleep(2)
                except:
                    pass

                # --- Scroll multiple times to load lazy-loaded entries ---
                for i in range(3):
                    driver.execute_script("window.scrollBy(0, document.body.scrollHeight / 3);")
                    sleep(2)

                edu_elements = driver.find_elements(
                    By.XPATH,
                    "//section[contains(@id,'education')]//li"
                    " | //*[@id='education']//li"
                    " | //div[@data-section='education']//li"
                    " | //*[@id='profile-content']//section[.//span[contains(text(),'Education')]]//ul/li"
                )
                print("DEBUG: Education elements found:", len(edu_elements))

                for edu in edu_elements[:7]:
                    # --- College / School name ---
                    try:
                        college = edu.find_element(
                            By.XPATH, ".//div/div[2]/div[1]/a/div/div/div/div/span[1]"
                        ).text
                    except:
                        try:
                            college = edu.find_element(
                                By.XPATH, ".//div/div[2]/div[1]/div/div/div/div/span[1]"
                            ).text
                        except:
                            try:
                                college = edu.find_element(
                                    By.XPATH, ".//div/div[2]/div[1]//span[1]"
                                ).text
                            except:
                                try:
                                    college = edu.find_element(
                                        By.XPATH, ".//span[contains(@class,'hoverable-link-text')]/span[1]"
                                    ).text
                                except:
                                    college = "N/A"

                    # --- Degree / Course ---
                    try:
                        degree = edu.find_element(
                            By.XPATH, ".//div/div[2]/div[1]/a/span[1]/span[1]"
                        ).text
                    except:
                        try:
                            degree = edu.find_element(
                                By.XPATH, ".//div/div[2]/div[1]/div/span[1]/span[1]"
                            ).text
                        except:
                            degree = "N/A"

                    # --- Duration (years) ---
                    try:
                        duration = edu.find_element(
                            By.XPATH, ".//span[contains(@class,'t-14 t-normal t-black--light')]"
                        ).text
                    except:
                        duration = "N/A"

                    # --- Grade (optional) ---
                    try:
                        grade = edu.find_element(
                            By.XPATH, ".//span[contains(text(),'Grade') or contains(text(),'grade')]"
                        ).text
                    except:
                        grade = "N/A"

                    # --- Clean up ---
                    college = college.strip().replace("\n", " ")
                    degree = degree.strip().replace("\n", " ")
                    duration = duration.strip().replace("\n", " ")
                    grade = grade.strip().replace("\n", " ")

                    education.append({
                        "college": college,
                        "degree": degree,
                        "duration": duration,
                        "grade": grade
                    })

                print("DEBUG: Extracted Education =", education)

            except Exception as e:
                logger.warning(f"⚠️ Education not extracted properly: {e}")



            # --- Projects Section ---
            projects = []
            try:
                proj_sections = soup.select("section[id*='projects'] li, div[data-section='projects'] li")
                print("DEBUG: proj_sections count =", len(proj_sections))
                for proj in proj_sections[:3]:
                    title = proj.find("span", class_="mr1 t-bold")
                    desc = proj.find("span", class_="t-14 t-normal")
                    projects.append({
                        "project_title": title.get_text(strip=True) if title else "",
                        "project_desc": desc.get_text(strip=True) if desc else ""
                    })
                print("DEBUG: Extracted Projects =", projects)
            except Exception as e:
                logger.warning(f"⚠️ Projects not extracted: {e}")

            # --- Prepare and Save Data ---
            profile_data = {
                "name": name,
                "url": profile_url,
                "headline": headline,
                "about": about,
                "experience": experience,
                "education": education,
                "projects": projects,
                "last_updated": datetime.now(),
                "scraped_at": datetime.now()
            }

            print("DEBUG: Final Profile Data =", profile_data)

            # --- Save or Update in MongoDB (avoid duplicates) ---
            collection.update_one({"url": profile_url}, {"$set": profile_data}, upsert=True)

            # --- Save to Excel ---
            excel_file = "linkedin_profiles_data.xlsx"
            df = pd.DataFrame([{
                "Name": name,
                "URL": profile_url,
                "Headline": headline,
                "About": about,
                "Experience": str(experience),
                "Education": str(education),
                "Projects": str(projects),
                "Last Updated": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            }])

            if not os.path.exists(excel_file):
                df.to_excel(excel_file, index=False)
            else:
                existing_df = pd.read_excel(excel_file)
                combined = pd.concat([existing_df, df], ignore_index=True)
                combined.to_excel(excel_file, index=False)

            logger.info(f"✅ Profile scraped and exported: {profile_url}")
            return True, "Profile scraped successfully"

        finally:
            driver.quit()

    except Exception as e:
        logger.error(f"❌ Error scraping {profile_url}: {e}")
        return False, str(e)

    finally:
        if "client" in locals():
            client.close()


if __name__ == "__main__":
    # url = "https://www.linkedin.com/in/vraj-maheshwari-6537ba278/"
    url = "https://www.linkedin.com/in/abhishek-kurle15/"
    success, message = run_linkedin_scraper(url)
    print("Result:", success, "| Message:", message)
