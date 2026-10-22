import os
import re
import requests
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import NoSuchElementException, TimeoutException
from time import sleep
from datetime import datetime
from bs4 import BeautifulSoup
import logging
from app.config import settings
from app.database import get_sync_collection

logger = logging.getLogger(__name__)

class LinkedInScraper:
    def __init__(self):
        self.collection = get_sync_collection()
    
    def setup_driver(self):
        """Setup Chrome driver with anti-detection options"""
        chrome_options = Options()
        # chrome_options.add_argument("--headless=new")  # DISABLED FOR DEBUGGING
        chrome_options.add_argument("--no-sandbox")
        chrome_options.add_argument("--disable-dev-shm-usage")
        chrome_options.add_argument("--disable-blink-features=AutomationControlled")
        chrome_options.add_argument("--window-size=1920,1080")
        chrome_options.add_experimental_option("excludeSwitches", ["enable-automation"])
        chrome_options.add_experimental_option('useAutomationExtension', False)
        
        driver = webdriver.Chrome(options=chrome_options)
        driver.execute_script("Object.defineProperty(navigator, 'webdriver', {get: () => undefined})")
        return driver
    
    def login(self, driver):
        """Login to LinkedIn"""
        try:
            logger.info("🔐 Logging into LinkedIn...")
            driver.get("https://www.linkedin.com/login")
            sleep(2)
            
            driver.find_element(By.ID, "username").send_keys(settings.LINKEDIN_EMAIL)
            driver.find_element(By.ID, "password").send_keys(settings.LINKEDIN_PASSWORD, Keys.RETURN)
            sleep(5)
            
            if "checkpoint" in driver.current_url or "challenge" in driver.current_url:
                logger.warning("⚠️ CAPTCHA detected - manual intervention required")
                return False
            
            logger.info("✅ Successfully logged in")
            return True
        except Exception as e:
            logger.error(f"❌ Login failed: {e}")
            return False

    
    def get_experience_tokens(self, driver, timeout=15):
        """Extract experience section - simple and robust approach"""
        try:
            # Scroll to experience section
            driver.execute_script("window.scrollTo(0, document.body.scrollHeight * 0.4);")
            sleep(3)
            
            # Try to find and click "Show all experiences" button
            try:
                show_all_buttons = driver.find_elements(By.XPATH, "//button[contains(text(), 'Show all') and contains(text(), 'experience')]")
                if show_all_buttons:
                    show_all_buttons[0].click()
                    sleep(2)
                    logger.info("✅ Clicked 'Show all experiences' button")
            except:
                pass
            
            # Find experience section
            try:
                exp_section = driver.find_element(By.XPATH, "//section[.//h2[contains(text(), 'Experience')] or .//span[text()='Experience']]")
                exp_html = exp_section.get_attribute("outerHTML")
                exp_soup = BeautifulSoup(exp_html, "html.parser")
                
                # Extract all text with separators
                all_text = exp_soup.get_text(separator="|", strip=True)
                tokens = [t.strip() for t in all_text.split("|") if t.strip()]
                
                logger.info(f"📊 Found {len(tokens)} experience tokens")
                return tokens
                
            except Exception as e:
                logger.debug(f"Experience extraction failed: {e}")
            
            return []
            
        except Exception as e:
            logger.error(f"❌ Error extracting experience: {e}")
            return []
    
    def parse_experience_tokens(self, tokens):
        """Parse experience tokens with smart filtering to remove descriptions"""
        if not tokens:
            return []
        
        # Remove "Experience" header if present
        if tokens and tokens[0].strip().lower() == "experience":
            tokens = tokens[1:]
        
        # Keywords that indicate a description (not a job title/company/duration/location)
        description_keywords = [
            'i have completed', 'selected as', 'responsible for', 'worked on',
            'developed', 'implemented', 'managed', 'created', 'designed',
            'collaborated', 'achieved', 'led', 'built', 'maintained',
            'machine learning', 'natural language processing', 'python programming',
            'skills:', 'technologies:', 'projects:'
        ]
        
        roles_set = {"Full-time", "Part-time", "Internship", "Contract", "Self-employed",
                     "Freelance", "Apprenticeship", "Volunteer", "Temporary", "Seasonal", "Trainee"}
        
        def is_duration(s):
            s2 = s.lower()
            return ((" to " in s2 or " - " in s2) and ("present" in s2 or "mo" in s2 or "yr" in s2)) or (" yr" in s2 and " mo" in s2)
        
        def is_location(s):
            if is_duration(s) or s in roles_set:
                return False
            loc_keywords = ["india", "remote", "on-site", "hybrid", "onsite", "anand", "ahmedabad", "gujarat", "mumbai", "delhi", "bangalore"]
            return any(k in s.lower() for k in loc_keywords) or ("," in s and len(s.split()) >= 2)
        
        def is_description(s):
            # Check if text is likely a description
            if len(s) > 100:  # Descriptions are usually long
                return True
            s_lower = s.lower()
            # Check for description keywords
            if any(keyword in s_lower for keyword in description_keywords):
                return True
            # Check if it starts with "and +" (skills list)
            if s_lower.startswith('and +') or 'and +' in s_lower:
                return True
            return False
        
        result = []
        i, n = 0, len(tokens)
        
        while i < n:
            # Skip descriptions
            if is_description(tokens[i]):
                i += 1
                continue
            
            designation, company, dur, loc = "", "", "", ""
            
            # Get designation (job title)
            if i < n and not is_description(tokens[i]):
                designation = tokens[i]
                i += 1
            
            # Get company (skip if it's a role type, duration, or location)
            if i < n and not is_description(tokens[i]) and tokens[i] not in roles_set and not is_duration(tokens[i]) and not is_location(tokens[i]):
                company = tokens[i]
                i += 1
            
            # Get duration
            if i < n and is_duration(tokens[i]):
                dur = tokens[i]
                i += 1
            
            # Get location
            if i < n and is_location(tokens[i]):
                loc = tokens[i]
                i += 1
            
            # Skip any remaining descriptions
            while i < n and is_description(tokens[i]):
                i += 1
            
            # Only add if we have both designation and company
            if designation and company and len(designation) < 100:
                result.append({
                    "company_name": company,
                    "designation": designation,
                    "duration": dur,
                    "location": loc,
                    "role": None
                })
        
        logger.info(f"✅ Parsed {len(result)} experience entries after filtering")
        return result
    
    def scrape_education(self, driver):
        """Scrape education section with improved parsing for LinkedIn structure"""
        try:
            # Scroll to education section
            driver.execute_script("window.scrollTo(0, document.body.scrollHeight * 0.6);")
            sleep(3)
            
            # Try to find and click "Show all education" button
            try:
                show_all_buttons = driver.find_elements(By.XPATH, "//button[contains(text(), 'Show all') and contains(text(), 'education')]")
                if show_all_buttons:
                    show_all_buttons[0].click()
                    sleep(2)
                    logger.info("✅ Clicked 'Show all education' button")
            except:
                pass
            
            education_data = []
            
            # Method 1: Look for education list items with specific class patterns
            try:
                edu_sections = driver.find_elements(By.XPATH, "//section[.//h2[contains(text(), 'Education')] or .//span[text()='Education']]")
                if edu_sections:
                    edu_html = edu_sections[0].get_attribute("outerHTML")
                    edu_soup = BeautifulSoup(edu_html, "html.parser")
                    
                    # Find all education list items - look for the specific pattern
                    # The HTML shows: <li class="artdeco-list__item xbAieyHsiOOoYnsLSJmOGDYJZtRumMFMSacjw FPSACggMWdGyQWRiYgxPzHNGnCUjaoqPwWDwETchWg">
                    edu_items = edu_soup.find_all("li", class_=lambda x: x and ("artdeco-list__item" in x or "pvs-list__item" in x))
                    
                    # Filter to only get top-level education items (not nested sub-items)
                    top_level_items = []
                    for item in edu_items:
                        # Check if this item contains the main education data (has a link to company or school)
                        has_school_link = item.find("a", href=lambda x: x and ("/company/" in x or "/search/results/all/" in x))
                        if has_school_link:
                            top_level_items.append(item)
                    
                    logger.info(f"🔍 Found {len(top_level_items)} top-level education items")
                    
                    for idx, item in enumerate(top_level_items):
                        try:
                            # Find the main education container within this item
                            edu_container = item.find("div", class_=lambda x: x and "display-flex" in x and "flex-column" in x)
                            
                            if not edu_container:
                                edu_container = item
                            
                            # Extract college/school name - look for the bold text with school name
                            college = ""
                            college_elem = edu_container.find("span", class_=lambda x: x and "t-bold" in x)
                            if not college_elem:
                                college_elem = edu_container.find("div", class_=lambda x: x and "t-bold" in x)
                            if college_elem:
                                college = college_elem.get_text(strip=True)
                            
                            # Extract degree - look for t-14 t-normal spans (not caption)
                            degree = ""
                            degree_spans = edu_container.find_all("span", class_=lambda x: x and "t-14" in x and "t-normal" in x and "t-black--light" not in x)
                            for span in degree_spans:
                                text = span.get_text(strip=True)
                                # Check if it looks like a degree (not a date)
                                if text and not any(month in text for month in ['Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun', 'Jul', 'Aug', 'Sep', 'Oct', 'Nov', 'Dec']) and len(text) > 10 and not text.startswith('Grade:'):
                                    degree = text
                                    break
                            
                            # Extract duration - look for caption text with dates
                            duration = ""
                            duration_elem = edu_container.find("span", class_=lambda x: x and "pvs-entity__caption-wrapper" in x)
                            if not duration_elem:
                                # Try alternative selector for duration - look in all t-14 spans
                                duration_spans = edu_container.find_all("span", class_=lambda x: x and "t-14" in x and "t-normal" in x)
                                for span in duration_spans:
                                    text = span.get_text(strip=True)
                                    # Check if it looks like a date (and not already captured as degree)
                                    if text != degree and (any(month in text for month in ['Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun', 'Jul', 'Aug', 'Sep', 'Oct', 'Nov', 'Dec']) or ('20' in text and len(text) < 30)):
                                        duration = text
                                        break
                            else:
                                duration = duration_elem.get_text(strip=True)
                            
                            # Extract grade - look for "Grade:" text
                            grade = ""
                            grade_divs = edu_container.find_all("div", class_=lambda x: x and "t-14" in x and "t-normal" in x)
                            for div in grade_divs:
                                text = div.get_text(strip=True)
                                if text.startswith("Grade:"):
                                    # Remove "Grade:" prefix to avoid duplication
                                    grade = text.replace("Grade:", "").strip()
                                    break
                            
                            # Only add if we have at least college name
                            if college and len(college) > 3:
                                edu_dict = {
                                    "college": college,
                                    "degree": degree if degree else None,
                                    "duration": duration if duration else None,
                                    "grade": grade if grade else None
                                }
                                education_data.append(edu_dict)
                                logger.info(f"✅ Parsed education #{idx+1}: {college}")
                        
                        except Exception as e:
                            logger.debug(f"Error processing education item #{idx+1}: {e}")
                            continue
                    
                    if education_data:
                        logger.info(f"🎓 Found {len(education_data)} education entries")
                        return education_data
                        
            except Exception as e:
                logger.debug(f"Education list items method failed: {e}")
            
            # Method 2: Fallback to token-based parsing
            try:
                edu_sections = driver.find_elements(By.XPATH, "//section[.//h2[contains(text(), 'Education')] or .//span[text()='Education']]")
                if edu_sections:
                    edu_html = edu_sections[0].get_attribute("outerHTML")
                    edu_soup = BeautifulSoup(edu_html, "html.parser")
                    
                    # Extract all text with separators
                    all_text = edu_soup.get_text(separator="|", strip=True)
                    tokens = [t.strip() for t in all_text.split("|") if t.strip()]
                    
                    logger.info(f"🔍 Fallback: Found {len(tokens)} tokens")
                    
                    # Remove "Education" header if present
                    if tokens and tokens[0].strip().lower() == "education":
                        tokens = tokens[1:]
                    
                    # Parse education entries
                    i = 0
                    while i < len(tokens):
                        # Skip grades and skill lists
                        if (tokens[i].startswith('Grade:') or 
                            'and +' in tokens[i] or 
                            tokens[i].lower().startswith('skills:') or
                            len(tokens[i]) > 200):
                            i += 1
                            continue
                        
                        college = ""
                        degree = ""
                        duration = ""
                        grade = ""
                        
                        # Get college/school name (usually first)
                        if i < len(tokens) and len(tokens[i]) > 5 and len(tokens[i]) < 150:
                            college = tokens[i]
                            i += 1
                        
                        # Get degree (if it looks like a degree)
                        if (i < len(tokens) and 
                            any(keyword in tokens[i] for keyword in ['Bachelor', 'Master', 'degree', 'btech', 'mtech', 'phd', 'diploma', 'certificate']) and
                            len(tokens[i]) < 150):
                            degree = tokens[i]
                            i += 1
                        
                        # Get duration (if it looks like a date range)
                        if (i < len(tokens) and 
                            (('20' in tokens[i] and ('-' in tokens[i] or 'to' in tokens[i] or '–' in tokens[i])) or 
                             any(month in tokens[i] for month in ['Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun', 'Jul', 'Aug', 'Sep', 'Oct', 'Nov', 'Dec'])) and
                            len(tokens[i]) < 50):
                            duration = tokens[i]
                            i += 1
                        
                        # Get grade (if it starts with "Grade:")
                        if i < len(tokens) and tokens[i].startswith('Grade:'):
                            # Remove "Grade:" prefix to avoid duplication
                            grade = tokens[i].replace("Grade:", "").strip()
                            i += 1
                        
                        # Only add if we have at least college name
                        if college and len(college) > 5:
                            edu_dict = {
                                "college": college,
                                "degree": degree if degree else None,
                                "duration": duration if duration else None,
                                "grade": grade if grade else None
                            }
                            education_data.append(edu_dict)
                        else:
                            i += 1
                    
                    if education_data:
                        logger.info(f"🎓 Found {len(education_data)} education entries via fallback")
                        return education_data
            except Exception as e:
                logger.debug(f"Fallback education method failed: {e}")
            
            logger.info("🎓 No education section found")
            return []
            
        except Exception as e:
            logger.warning(f"❌ Error in education section: {e}")
            return []
    
    def scrape_projects(self, driver, profile_url):
        """Scrape projects by navigating to the dedicated projects page"""
        try:
            # Navigate directly to the projects detail page
            projects_url = profile_url.rstrip('/') + '/details/projects/'
            logger.info(f"🚀 Navigating to projects page: {projects_url}")
            driver.get(projects_url)
            sleep(3)
            
            projects_list = []
            
            try:
                # Find all project items on the dedicated page
                page_source = driver.page_source
                soup = BeautifulSoup(page_source, "html.parser")
                
                # Find all project list items
                project_items = soup.find_all("li", class_=lambda x: x and ("pvs-list__paged-list-item" in x or "artdeco-list__item" in x))
                logger.info(f"🔍 Found {len(project_items)} project items on dedicated page")
                
                for idx, item in enumerate(project_items):
                    try:
                        # Extract project name
                        project_name = ""
                        name_spans = item.find_all("span", attrs={"aria-hidden": "true"})
                        for span in name_spans:
                            parent = span.find_parent()
                            if parent and "t-bold" in parent.get("class", []):
                                text = span.get_text(strip=True)
                                if text and len(text) > 3 and not text.startswith('Skills:'):
                                    project_name = text
                                    break
                        
                        if not project_name:
                            continue
                        
                        # Extract description
                        description = ""
                        desc_spans = item.find_all("span", attrs={"aria-hidden": "true"})
                        for span in desc_spans:
                            text = span.get_text(strip=True)
                            if (text and text != project_name and 
                                not text.startswith('Skills:') and 
                                not text.startswith('Associated with') and
                                len(text) > 40 and len(text) < 600):
                                description = text
                                break
                        
                        # Extract skills
                        skills = ""
                        for span in desc_spans:
                            text = span.get_text(strip=True)
                            if 'Skills:' in text:
                                skills = text.split('Skills:')[1].strip() if 'Skills:' in text else text
                                break
                        
                        # Only add if valid
                        if project_name and len(project_name) > 3:
                            if not any(p['project_name'] == project_name for p in projects_list):
                                project_dict = {
                                    'project_name': project_name,
                                    'description': description if description else None,
                                    'skills': skills if skills else None,
                                    'duration': None
                                }
                                projects_list.append(project_dict)
                                logger.info(f"✅ Parsed project #{len(projects_list)}: {project_name}")
                    
                    except Exception as e:
                        logger.debug(f"Error processing project item #{idx+1}: {e}")
                        continue
                
                if projects_list:
                    logger.info(f"🚀 Found {len(projects_list)} projects total")
                    return projects_list
                else:
                    logger.warning("⚠️ No projects found on dedicated page")
                    
            except Exception as e:
                logger.error(f"❌ Projects extraction failed: {e}")
                import traceback
                logger.error(traceback.format_exc())
            
            return []
            
        except Exception as e:
            logger.warning(f"❌ Error in projects section: {e}")
            import traceback
            logger.warning(traceback.format_exc())
            return []
    
    def scrape_licenses(self, driver):
        """Scrape licenses and certifications with new LinkedIn structure"""
        try:
            # Scroll to licenses/certifications section
            driver.execute_script("window.scrollTo(0, document.body.scrollHeight * 0.8);")
            sleep(3)
            
            # Try to find and click "Show all licenses" or "Show all certifications" button
            try:
                show_all_buttons = driver.find_elements(By.XPATH, "//button[contains(text(), 'Show all') and (contains(text(), 'license') or contains(text(), 'certification'))]")
                if show_all_buttons:
                    show_all_buttons[0].click()
                    sleep(2)
                    logger.info("✅ Clicked 'Show all licenses/certifications' button")
            except:
                pass
            
            licenses_list = []
            
            # Method 1: Look for license/certification cards in new LinkedIn structure
            try:
                license_cards = driver.find_elements(By.CSS_SELECTOR, "div[data-view-name*='license'], div[data-view-name*='certification'], li[data-view-name*='license'], li[data-view-name*='certification']")
                if not license_cards:
                    # Alternative selectors
                    license_cards = driver.find_elements(By.CSS_SELECTOR, "section[data-section='licenses'] li, section[data-section='certifications'] li, div.license-item, div.certification-item")
                
                for card in license_cards[:15]:  # Limit to first 15 licenses/certifications
                    try:
                        card_html = card.get_attribute("outerHTML")
                        card_soup = BeautifulSoup(card_html, "html.parser")
                        
                        # Extract text content
                        text_elements = card_soup.find_all(text=True)
                        card_text = [t.strip() for t in text_elements if t.strip() and len(t.strip()) > 2]
                        
                        # Filter out section headers and common text
                        filtered_text = []
                        for text in card_text:
                            if text.lower() not in ['licenses & certifications', 'licenses', 'certifications', 'show all', 'view', 'more']:
                                filtered_text.append(text)
                        
                        if len(filtered_text) >= 1:
                            license_dict = {
                                "name": filtered_text[0] if len(filtered_text) > 0 else None,
                                "institute": filtered_text[1] if len(filtered_text) > 1 else None,
                                "issued_date": filtered_text[2] if len(filtered_text) > 2 else None
                            }
                            # Only add if we have a meaningful license name
                            if license_dict['name'] and len(license_dict['name']) > 3:
                                licenses_list.append(license_dict)
                        
                    except Exception as e:
                        logger.debug(f"Error processing license card: {e}")
                        continue
                        
                if licenses_list:
                    logger.info(f"🏆 Found {len(licenses_list)} licenses/certifications via cards")
                    return licenses_list
                    
            except Exception as e:
                logger.debug(f"License cards method failed: {e}")
            
            # Method 2: Traditional section-based approach
            try:
                # Look for licenses, certifications, or accomplishments sections
                license_sections = driver.find_elements(By.XPATH, "//section[.//h2[contains(text(), 'Licenses')] or .//h2[contains(text(), 'Certifications')] or .//span[text()='Licenses & certifications']]")
                if license_sections:
                    licenses_html = license_sections[0].get_attribute("outerHTML")
                    licenses_soup = BeautifulSoup(licenses_html, "html.parser")
                    
                    # Look for list items or license blocks
                    license_blocks = licenses_soup.find_all("li") or licenses_soup.find_all("div", class_=lambda x: x and ("license" in x.lower() or "certification" in x.lower()))
                    
                    for block in license_blocks:
                        text_content = block.get_text(separator="|", strip=True)
                        text_parts = [t.strip() for t in text_content.split("|") if t.strip()]
                        
                        if len(text_parts) >= 2:
                            license_dict = {
                                "name": text_parts[0] if len(text_parts) > 0 else None,
                                "institute": text_parts[1] if len(text_parts) > 1 else None,
                                "issued_date": text_parts[2] if len(text_parts) > 2 else None
                            }
                            licenses_list.append(license_dict)
                    
                    if licenses_list:
                        logger.info(f"🏆 Found {len(licenses_list)} licenses/certifications via section")
                        return licenses_list
            except Exception as e:
                logger.debug(f"Traditional licenses method failed: {e}")
            
            logger.info("🏆 No licenses/certifications section found")
            return []
            
        except Exception as e:
            logger.warning(f"❌ Error in licenses section: {e}")
            return []
    
    def scrape_skills(self, driver, profile_url):
        """Scrape skills by navigating to the dedicated skills page"""
        try:
            # Navigate directly to the skills detail page
            skills_url = profile_url.rstrip('/') + '/details/skills/'
            logger.info(f"🛠️ Navigating to skills page: {skills_url}")
            driver.get(skills_url)
            sleep(4)
            
            skills_list = []
            
            try:
                # Get page source
                page_source = driver.page_source
                soup = BeautifulSoup(page_source, "html.parser")
                
                # Method 1: Look for spans with aria-hidden="true" inside hoverable-link-text divs
                # This is the most accurate method based on the HTML structure
                hoverable_divs = soup.find_all("div", class_=lambda x: x and "hoverable-link-text" in x)
                logger.info(f"🔍 Found {len(hoverable_divs)} hoverable-link-text divs")
                
                for div in hoverable_divs:
                    span = div.find("span", attrs={"aria-hidden": "true"})
                    if span:
                        skill_text = span.get_text(strip=True)
                        # Filter out noise and duplicates
                        if (skill_text and 
                            len(skill_text) >= 2 and 
                            len(skill_text) <= 100 and
                            skill_text.lower() not in ['skills', 'show all', 'view', 'more', 'back'] and
                            skill_text not in skills_list):
                            skills_list.append(skill_text)
                            logger.info(f"✅ Found skill: {skill_text}")
                
                # Method 2: Fallback to <p> tags if Method 1 didn't find anything
                if not skills_list:
                    logger.info("🔄 Fallback: Trying <p> tag extraction...")
                    all_p_tags = soup.find_all("p")
                    
                    # Known tech skills to look for
                    known_skills = [
                        'MongoDB', 'REST APIs', 'React.js', 'chromadb', 'OpenCV',
                        'yolo', 'Flask', 'AIML', 'PHP', 'boostrap', 'sqlserver',
                        'Web Development', 'Teamwork', 'MERN Stack', 'SQL',
                        '.NET core MVC', 'Data Structures', 'Python', 'Java'
                    ]
                    
                    for p in all_p_tags:
                        text = p.get_text(strip=True)
                        # Only match exact skill names (not partial matches in longer text)
                        if text in known_skills and text not in skills_list:
                            skills_list.append(text)
                            logger.info(f"✅ Matched skill: {text}")
                
                if skills_list:
                    logger.info(f"🛠️ Extracted {len(skills_list)} skills total")
                    return skills_list
                else:
                    logger.warning("⚠️ No skills found on dedicated page")
                    
            except Exception as e:
                logger.error(f"❌ Skills extraction failed: {e}")
                import traceback
                logger.error(traceback.format_exc())
            
            return []
            
        except Exception as e:
            logger.warning(f"❌ Error in skills section: {e}")
            import traceback
            logger.warning(traceback.format_exc())
            return []
    
    def scrape_profile(self, profile_url):
        """Main scraping function"""
        driver = None
        try:
            existing_profile = self.collection.find_one({"url": profile_url})
            is_update = existing_profile is not None
            
            driver = self.setup_driver()
            
            if not self.login(driver):
                return False, "Login failed"
            
            logger.info(f"📄 Loading profile: {profile_url}")
            driver.get(profile_url)
            WebDriverWait(driver, 20).until(EC.presence_of_element_located((By.TAG_NAME, "body")))
            sleep(3)
            
            # Check for CAPTCHA or login redirect
            if "checkpoint" in driver.current_url or "challenge" in driver.current_url:
                logger.warning("⚠️ CAPTCHA detected - please solve manually")
                input("Press Enter after solving CAPTCHA...")
            
            if "login" in driver.current_url:
                logger.warning("⚠️ Redirected to login - session expired")
                return False, "Session expired, please restart"
            
            # Comprehensive scrolling to load all content
            logger.info("🔄 Scrolling to load all profile content...")
            logger.info("📜 Scroll 1/3: Loading top sections...")
            for i in range(4):  # Scroll to 50%
                driver.execute_script(f"window.scrollTo(0, document.body.scrollHeight * {(i+1)/8});")
                sleep(2)
            
            logger.info("📜 Scroll 2/3: Loading middle sections...")
            for i in range(4, 6):  # Scroll to 75%
                driver.execute_script(f"window.scrollTo(0, document.body.scrollHeight * {(i+1)/8});")
                sleep(2)
            
            logger.info("📜 Scroll 3/3: Loading bottom sections (Projects, Skills)...")
            for i in range(6, 10):  # Scroll to 100% and beyond
                driver.execute_script(f"window.scrollTo(0, document.body.scrollHeight * {(i+1)/8});")
                sleep(3)  # Wait longer for bottom sections
            
            # Scroll to absolute bottom
            driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
            sleep(3)
            logger.info("✅ Finished scrolling - all content should be loaded")
            
            # DON'T scroll back to top - keep the page scrolled so content stays loaded
            # driver.execute_script("window.scrollTo(0, 0);")
            # sleep(2)
            
            page_source = driver.page_source
            soup = BeautifulSoup(page_source, "html.parser")  # Use html.parser for better compatibility
            
            # Check what page we're actually on
            current_url = driver.current_url
            page_title = driver.title
            logger.info(f"🌐 Current URL: {current_url}")
            logger.info(f"📄 Page title: {page_title}")
            
            # Check if we're on the right page
            if "linkedin.com/in/" not in current_url:
                logger.warning("⚠️ Not on LinkedIn profile page!")
                return False, "Redirected away from LinkedIn profile"
            
            # Extract name with multiple approaches - more robust
            name = None
            
            # Method 1: Try specific CSS selectors
            name_selectors = [
                # Various LinkedIn CSS structures
                "p[class*='_295d11f0']",  # Generic pattern for name paragraphs
                "p[class*='b1a6cf12']",
                "p.eb7256ab.b1a6cf12",
                "p._2cda7f44._295d11f0",
                "h1.text-heading-xlarge",
                "h1",
                ".pv-text-details__left-panel h1",
                ".ph5 h1"
            ]
            
            for selector in name_selectors:
                try:
                    name_elem = soup.select_one(selector)
                    if name_elem:
                        name = name_elem.get_text(strip=True)
                        # Clean up the name
                        name = name.split('•')[0].strip()
                        name = name.split('\n')[0].strip()
                        if name and name != "LinkedIn" and "Join" not in name and 5 < len(name) < 50:
                            logger.info(f"👤 Found name with selector '{selector}': {name}")
                            break
                except Exception as e:
                    logger.debug(f"Selector '{selector}' failed: {e}")
                    continue
            
            # Method 2: Look for name in page title
            if not name:
                try:
                    title = soup.find('title')
                    if title:
                        title_text = title.get_text()
                        if '|' in title_text:
                            potential_name = title_text.split('|')[0].strip()
                            if 5 < len(potential_name) < 50 and potential_name != "LinkedIn":
                                name = potential_name
                                logger.info(f"👤 Found name from page title: {name}")
                except Exception as e:
                    logger.debug(f"Title extraction failed: {e}")
            
            # Method 3: Generic text-based search for name-like patterns
            if not name:
                try:
                    all_paragraphs = soup.find_all('p')
                    for p in all_paragraphs:
                        text = p.get_text().strip()
                        words = text.split()
                        # Look for 2-4 word names
                        if 2 <= len(words) <= 4 and 5 <= len(text) <= 50:
                            # Filter out common non-name text
                            if not any(word in text.lower() for word in ['show', 'all', 'view', 'more', 'skills', 'experience', 'education', 'profile', 'connect', 'message', 'follow', 'home', 'jobs', 'network']):
                                name = text.split('•')[0].strip()
                                name = name.split('\n')[0].strip()
                                if name and len(name) > 5:
                                    logger.info(f"👤 Found name via text search: {name}")
                                    break
                except Exception as e:
                    logger.debug(f"Text search failed: {e}")
            
            if not name or name == "N/A":
                logger.warning("⚠️ Could not extract name - might be blocked or wrong page")
                # Save page source for debugging
                with open("debug_page.html", "w", encoding="utf-8") as f:
                    f.write(page_source)
                logger.info("💾 Saved page source to debug_page.html")
                return False, "Could not extract profile name"
            
            # Extract headline with multiple selectors including new LinkedIn structure
            headline_selectors = [
                # New LinkedIn CSS structure variations
                "p._2cda7f44.fc9d8ddd._7c54c101.b71e8ea7._4b051636._0f2e688a._4c464f09._19805243",  # Dhruvi's profile
                "p.eb7256ab._7c39b193.ebf6c521._03194cc5._3e29b192.b5762d6c._0889552e.adbce56e",  # Vraj's profile
                "div._3da5b139._62bb4831._01b04366.e80dfd4f._081f0e77.a6ebefbf._316564f0",
                # Fallback to older selectors
                "div.text-body-medium",
                ".pv-text-details__left-panel .text-body-medium",
                ".ph5 .text-body-medium",
                ".pv-shared-text-with-see-more"
            ]
            
            headline = None
            for selector in headline_selectors:
                try:
                    headline_elem = soup.select_one(selector)
                    if headline_elem:
                        headline = headline_elem.get_text(strip=True)
                        # Skip if it's just the name or too short
                        if headline and headline != name and len(headline) > 10:
                            logger.info(f"💼 Found headline with selector '{selector}': {headline[:50]}...")
                            break
                except Exception as e:
                    logger.debug(f"Headline selector '{selector}' failed: {e}")
                    continue
            
            # If still no headline, try text-based search for known patterns
            if not headline:
                try:
                    all_paragraphs = soup.find_all('p')
                    for p in all_paragraphs:
                        text = p.get_text().strip()
                        # Look for typical headline patterns
                        if any(keyword in text.lower() for keyword in ['developer', 'engineer', 'analyst', 'manager', 'consultant']) and len(text) > 20 and len(text) < 200:
                            if text != name:  # Make sure it's not the name
                                headline = text
                                logger.info(f"💼 Found headline via text search: {headline[:50]}...")
                                break
                except Exception as e:
                    logger.debug(f"Headline text search failed: {e}")
            
            if not headline:
                logger.info("💼 No headline found")
            
            # Extract about section with new LinkedIn structure
            about = None
            try:
                # First, try to find and click the "see more" button in About section
                try:
                    logger.info("📝 Looking for 'see more' button in About section...")
                    
                    # Method 1: Find button with "see more" or "show more" text near About section
                    see_more_buttons = driver.find_elements(By.XPATH, 
                        "//section[contains(@class, 'summary') or contains(@data-section, 'summary')]//button[contains(translate(., 'SEEMOR', 'seemor'), 'see more') or contains(translate(., 'SHOWMOR', 'showmor'), 'show more')]"
                    )
                    
                    if not see_more_buttons:
                        # Method 2: Find any button with aria-expanded="false" near about text
                        see_more_buttons = driver.find_elements(By.XPATH,
                            "//div[contains(@class, 'inline-show-more-text')]//button[@aria-expanded='false']"
                        )
                    
                    if not see_more_buttons:
                        # Method 3: Find button with "...more" text
                        see_more_buttons = driver.find_elements(By.XPATH,
                            "//button[contains(., '...more') or contains(., 'see more')]"
                        )
                    
                    if see_more_buttons:
                        logger.info(f"✅ Found {len(see_more_buttons)} 'see more' button(s), clicking first one...")
                        see_more_buttons[0].click()
                        sleep(2)
                        logger.info("✅ Clicked 'see more' button")
                    else:
                        logger.info("ℹ️ No 'see more' button found (text might already be expanded)")
                        
                except Exception as e:
                    logger.debug(f"Could not click 'see more' button: {e}")
                
                # Refresh page source after clicking
                page_source = driver.page_source
                soup = BeautifulSoup(page_source, "html.parser")
                
                # Try multiple selectors for about section
                about_selectors = [
                    # New LinkedIn structure - expandable text
                    "span[data-testid='expandable-text-box']",
                    # About section with display-flex
                    "section[data-section='summary'] div.display-flex",
                    "div.pv-about__summary-text",
                    # Fallback selectors
                    ".pv-about-section .pv-about__summary-text",
                    ".about-section .about-section__text"
                ]
                
                for selector in about_selectors:
                    try:
                        about_elem = soup.select_one(selector)
                        if about_elem:
                            about_text = about_elem.get_text(strip=True)
                            # Clean up the text - remove "...more" or "see more" artifacts
                            about_text = about_text.replace('...more', '').replace('…more', '').strip()
                            
                            if about_text and len(about_text) > 20:  # Ensure it's substantial content
                                about = about_text
                                logger.info(f"📝 Found about with selector '{selector}': {len(about)} characters")
                                break
                    except Exception as e:
                        logger.debug(f"About selector '{selector}' failed: {e}")
                        continue
                
                if not about:
                    logger.info("📝 No about section found")
                    
            except Exception as e:
                logger.error(f"❌ Error extracting about: {e}")
            
            # Extract skills from headline as fallback
            skills = []
            try:
                # Extract skills mentioned in headline
                if headline:
                    # Look for technology/skill keywords in headline
                    tech_keywords = ['Python', 'JavaScript', 'Java', 'React', 'Node.js', 'SQL', 'MongoDB', 'AWS', 'Docker', 'Git', 'HTML', 'CSS', 'PHP', 'Laravel', 'Django', 'Flask', 'Angular', 'Vue', 'TypeScript', 'C++', 'C#', '.NET', 'Spring', 'Express', 'PostgreSQL', 'MySQL', 'Redis', 'Kubernetes', 'Jenkins', 'Linux', 'Ubuntu', 'Windows', 'MacOS', 'Android', 'iOS', 'Swift', 'Kotlin', 'Flutter', 'Dart', 'Go', 'Rust', 'Scala', 'Ruby', 'Perl', 'R', 'MATLAB', 'TensorFlow', 'PyTorch', 'Pandas', 'NumPy', 'Scikit-learn', 'OpenCV', 'Selenium', 'Jest', 'Cypress', 'Postman', 'Figma', 'Photoshop', 'Illustrator', 'Sketch', 'InVision', 'Zeplin', 'Slack', 'Jira', 'Trello', 'Asana', 'Notion', 'Confluence', 'Bitbucket', 'GitLab', 'GitHub', 'VS Code', 'IntelliJ', 'Eclipse', 'Xcode', 'Sublime Text', 'Atom', 'Vim', 'Emacs', 'AI/ML', 'Machine Learning', 'Artificial Intelligence', 'Data Science', 'Cybersecurity', 'Full Stack', 'Backend', 'Frontend', 'DevOps', 'Cloud Computing', 'Microservices', 'API', 'REST', 'GraphQL', 'Blockchain', 'IoT', 'Big Data', 'Analytics', 'Visualization', 'ETL', 'Data Engineering', 'Software Engineering', 'Web Development', 'Mobile Development', 'Game Development', 'UI/UX', 'Design', 'Agile', 'Scrum', 'Kanban', 'CI/CD', 'Testing', 'QA', 'Automation', 'Scripting', 'Networking', 'Security', 'Penetration Testing', 'Ethical Hacking', 'Forensics', 'Compliance', 'GDPR', 'HIPAA', 'SOX', 'PCI DSS']
                    
                    headline_skills = []
                    for keyword in tech_keywords:
                        if keyword.lower() in headline.lower():
                            headline_skills.append(keyword)
                    
                    if headline_skills:
                        skills = headline_skills
                        logger.info(f"🛠️ Extracted {len(skills)} skills from headline: {skills}")
                        
            except Exception as e:
                logger.debug(f"Skills headline extraction failed: {e}")
            
            # Extract sections
            tokens = self.get_experience_tokens(driver)
            experience = self.parse_experience_tokens(tokens) if tokens else []
            education = self.scrape_education(driver)
            projects = self.scrape_projects(driver, profile_url)  # Pass profile_url
            licenses = self.scrape_licenses(driver)
            
            # Extract skills - use scrape_skills method
            skills = self.scrape_skills(driver, profile_url)  # Pass profile_url
            
            # Fallback: if no skills found, try to extract from headline
            if not skills:
                logger.info("🛠️ No skills scraped, trying to extract from headline...")
                if headline:
                    known_skills = []
                    tech_keywords = ["Python", "PHP", "React", "SQL", "AI/ML", "Cybersecurity", ".NET", "Full Stack"]
                    for keyword in tech_keywords:
                        if keyword in headline:
                            known_skills.append(keyword)
                    
                    if known_skills:
                        skills = known_skills
                        logger.info(f"🛠️ Extracted {len(skills)} skills from headline: {skills}")
                
                # Final fallback
                if not skills:
                    skills = []
                    logger.info("🛠️ No skills found")
            
            profile_data = {
                "name": name,
                "url": profile_url,
                "headline": headline,
                "about": about,
                "experience": experience,
                "education": education,
                "projects": projects,
                "licenses": licenses,
                "skills": skills,
                "courses": [],
                "honors_awards": [],
                "profile_picture": None,
                "last_updated": datetime.now()
            }
            
            if not is_update:
                profile_data["scraped_at"] = datetime.now()
            
            if is_update:
                self.collection.update_one({"url": profile_url}, {"$set": profile_data})
                logger.info(f"✅ Profile updated: {name}")
            else:
                self.collection.insert_one(profile_data)
                logger.info(f"✅ Profile created: {name}")
            
            return True, f"Successfully scraped profile: {name}"
        
        except Exception as e:
            logger.error(f"❌ Scraping failed: {e}")
            return False, str(e)
        
        finally:
            if driver:
                driver.quit()
