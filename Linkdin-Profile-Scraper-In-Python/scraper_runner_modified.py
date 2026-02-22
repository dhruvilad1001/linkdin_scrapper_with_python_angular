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
from bs4 import BeautifulSoup as _BeautifulSoup, FeatureNotFound
import logging

# Load environment variables
load_dotenv()

# Logger setup
logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")
logger = logging.getLogger(__name__)

_soup_fallback_logged = False


def BeautifulSoup(markup, features=None, **kwargs):
    """Wrapper that falls back to the stdlib parser when lxml isn't installed."""
    global _soup_fallback_logged
    parser = features or "lxml"
    try:
        return _BeautifulSoup(markup, parser, **kwargs)
    except FeatureNotFound:
        if not _soup_fallback_logged:
            logger.warning(
                "Requested HTML parser '%s' is not available. Falling back to 'html.parser'.",
                parser
            )
            _soup_fallback_logged = True
        return _BeautifulSoup(markup, "html.parser", **kwargs)

#----- Expand function 
def expand_all_sections(driver):
    """Click all expandable See All / Show More buttons on LinkedIn."""
    button_texts = [
        "See all", "see all",
        "Show all", "show all",
        "See more", "see more",
        "Show more", "show more",
        "Expand", "expand"
    ]

    for text in button_texts:
        try:
            buttons = driver.find_elements(By.XPATH, f"//button[contains(., '{text}')]")
            for btn in buttons:
                try:
                    driver.execute_script("arguments[0].click();", btn)
                    sleep(1)
                except:
                    pass
        except:
            pass


def close_modal_if_present(driver):
    """Close any open LinkedIn modal dialogs if present."""
    close_selectors = [
        "//button[@aria-label='Dismiss']",
        "//button[@data-test-modal-close-btn='true']",
        "//button[contains(@class,'artdeco-modal__dismiss')]"
    ]
    for selector in close_selectors:
        try:
            close_btn = driver.find_element(By.XPATH, selector)
            driver.execute_script("arguments[0].click();", close_btn)
            sleep(0.8)
            return
        except NoSuchElementException:
            continue
        except Exception:
            break
    try:
        body = driver.find_element(By.TAG_NAME, "body")
        body.send_keys(Keys.ESCAPE)
        sleep(0.5)
    except Exception:
        pass


def capture_show_all_content(driver, section_element, wait_timeout=10):
    """
    Clicks the Show all control inside a section (if present) and returns a BeautifulSoup object
    representing the expanded content (modal, detail page, or inline expansion).
    """
    show_all_locators = [
        ".//button[contains(translate(., 'ABCDEFGHIJKLMNOPQRSTUVWXYZ', 'abcdefghijklmnopqrstuvwxyz'), 'show all')]",
        ".//a[contains(translate(., 'ABCDEFGHIJKLMNOPQRSTUVWXYZ', 'abcdefghijklmnopqrstuvwxyz'), 'show all')]",
        ".//span[contains(translate(., 'ABCDEFGHIJKLMNOPQRSTUVWXYZ', 'abcdefghijklmnopqrstuvwxyz'), 'show all')]/ancestor::button",
        ".//span[contains(translate(., 'ABCDEFGHIJKLMNOPQRSTUVWXYZ', 'abcdefghijklmnopqrstuvwxyz'), 'show all')]/ancestor::a"
    ]

    show_all_element = None
    for locator in show_all_locators:
        try:
            show_all_element = section_element.find_element(By.XPATH, locator)
            break
        except NoSuchElementException:
            continue

    if not show_all_element:
        return None

    previous_url = driver.current_url
    try:
        driver.execute_script("arguments[0].click();", show_all_element)
    except Exception:
        return None

    sleep(1)

    # Scenario 1: Modal dialog opens
    try:
        modal = WebDriverWait(driver, wait_timeout).until(
            EC.presence_of_element_located((By.XPATH, "//div[@role='dialog']"))
        )
        html = modal.get_attribute("outerHTML")
        soup = BeautifulSoup(html, "lxml")
        close_modal_if_present(driver)
        return soup
    except TimeoutException:
        pass

    # Scenario 2: Navigated to a detail page
    if driver.current_url != previous_url:
        try:
            WebDriverWait(driver, wait_timeout).until(
                EC.presence_of_element_located((By.XPATH, "//section[.//span[contains(text(), 'Licenses') or contains(text(), 'Certifications')]]"))
            )
        except TimeoutException:
            sleep(1)
        soup = BeautifulSoup(driver.page_source, "lxml")
        driver.back()
        WebDriverWait(driver, wait_timeout).until(
            EC.presence_of_element_located((By.TAG_NAME, "body"))
        )
        sleep(1.5)
        return soup

    # Scenario 3: Inline expansion (no modal/navigation)
    try:
        updated_html = section_element.get_attribute("outerHTML")
        return BeautifulSoup(updated_html, "lxml")
    except Exception:
        return None


def scrape_licenses_and_certifications(driver):
    """Collect all licenses & certifications, including 'Show all' content.
    Uses the exact logic from the working notebook implementation."""
    try:
        # First scroll near the licenses section
        driver.execute_script("window.scrollTo(0, document.body.scrollHeight * 0.7);")
        sleep(2)

        clicked_see_all_licenses = False
        item_list = []

        # --- Try clicking "See all licenses" button using the specific ID ---
        try:
            see_all_licenses_btn = WebDriverWait(driver, 5).until(
                EC.presence_of_element_located((By.ID, "navigation-index-see-all-licenses-and-certifications"))
            )
            # Scroll into view
            driver.execute_script("arguments[0].scrollIntoView({block: 'center'});", see_all_licenses_btn)
            sleep(1)

            # Try normal click first
            try:
                see_all_licenses_btn.click()
            except ElementClickInterceptedException:
                # Fallback: force JS click
                driver.execute_script("arguments[0].click();", see_all_licenses_btn)

            sleep(3)
            logger.info("✅ Clicked 'see all licenses' button")
            clicked_see_all_licenses = True

        except (NoSuchElementException, TimeoutException):
            logger.info("ℹ️ 'See all licenses' button not found, scraping from main profile page")

        # --- Parse page source ---
        page_source = driver.page_source
        soup = BeautifulSoup(page_source, 'lxml')

        items = []

        if clicked_see_all_licenses:
            # We're on the dedicated licenses page - look for the main section first
            licenses_section = soup.find('section', {'class': 'artdeco-card pb3'})
            if licenses_section:
                items = licenses_section.find_all('li', {'class': 'pvs-list__paged-list-item'})
            else:
                # Fallback: find all license items on the page
                items = soup.find_all('li', {'class': 'pvs-list__paged-list-item'})
        else:
            # We're on the main profile page - look for licenses section
            try:
                licenses_section = WebDriverWait(driver, 10).until(
                    EC.presence_of_element_located((By.XPATH, "//section[.//span[contains(text(), 'Licenses') or contains(text(), 'Certifications')]]"))
                )
                licenses_html = licenses_section.get_attribute("outerHTML")
                licenses_soup = BeautifulSoup(licenses_html, "lxml")
                items = licenses_soup.find_all("li", {"class": "artdeco-list__item"})
                if not items:
                    items = licenses_soup.find_all("li", {"class": "pvs-list__paged-list-item"})
            except:
                items = []

        # --- Extract license data using the notebook's get_license logic ---
        def get_license(item):
            spans = item.find_all('span', {'class': 'visually-hidden'})
            item_dict = {}

            filtered_spans = []
            for span in spans:
                text = span.get_text().strip().lower()
                # Filter out connection/profile related spans (exact logic from notebook)
                if not any(keyword in text for keyword in ['connection', 'mutual', 'profile', 'view', 'connect']):
                    filtered_spans.append(span.get_text().strip())

            if len(filtered_spans) > 0:
                item_dict['name'] = filtered_spans[0]
            if len(filtered_spans) > 1:
                item_dict['institute'] = filtered_spans[1]
            if len(filtered_spans) > 2:
                item_dict['issued_date'] = filtered_spans[2]

            return item_dict

        # Process all license items
        for item in items:
            # Additional filter: Skip items that are clearly "more profiles for you" recommendations
            item_text_lower = item.get_text(" ", strip=True).lower()
            if any(keyword in item_text_lower for keyword in ['more profiles for you', 'people also viewed', 'people you may know']):
                continue
            
            license_data = get_license(item)
            # Only keep valid entries that have a name (exact logic from notebook)
            if license_data.get('name'):
                item_list.append(license_data)

        logger.info(f"✅ Found {len(item_list)} license/certification entries")

        # Go back if we navigated into "see all" page
        if clicked_see_all_licenses:
            driver.back()
            sleep(2)

        return item_list

    except Exception as e:
        logger.warning(f"⚠️ Licenses error: {e}")
        return []


def scrape_education(driver):
    """Collect all education entries, including 'Show all' content.
    Uses the exact logic from the working notebook implementation."""
    try:
        # First scroll to education section
        driver.execute_script("window.scrollTo(0, document.body.scrollHeight * 0.5);")
        sleep(2)

        clicked_see_all_education = False

        # --- Try clicking "See all education" button using the specific ID ---
        try:
            see_all_education_btn = WebDriverWait(driver, 5).until(
                EC.element_to_be_clickable((By.ID, "navigation-index-see-all-education"))
            )
            # Scroll into view
            driver.execute_script("arguments[0].scrollIntoView({block: 'center'});", see_all_education_btn)
            sleep(1)
            try:
                see_all_education_btn.click()
            except ElementClickInterceptedException:
                # Fallback: force JS click
                driver.execute_script("arguments[0].click();", see_all_education_btn)

            sleep(3)
            logger.info("✅ Clicked 'See all education' button")
            clicked_see_all_education = True

        except (NoSuchElementException, TimeoutException):
            logger.info("ℹ️ No 'See all education' button, scraping from main profile page")

        # --- Get page source and parse ---
        page_source = driver.page_source
        soup = BeautifulSoup(page_source, "lxml")

        education_data = []

        if clicked_see_all_education:
            # We're on dedicated education page - look for the main section first
            edu_section = soup.find("section", {"class": "artdeco-card pb3"})
            if edu_section:
                edu_blocks = edu_section.find_all("li", {"class": "pvs-list__paged-list-item"})
            else:
                # Fallback: find all education items on the page
                edu_blocks = soup.find_all("li", {"class": "pvs-list__paged-list-item"})
        else:
            # We're on main profile page - look for education section
            edu_sections = driver.find_elements(By.XPATH, "//section[.//span[text()='Education']]")
            if edu_sections:
                edu_html = edu_sections[0].get_attribute("outerHTML")
                edu_soup = BeautifulSoup(edu_html, "lxml")
                edu_blocks = edu_soup.find_all("li", {"class": "artdeco-list__item"})
                if not edu_blocks:
                    edu_blocks = edu_soup.find_all("li", {"class": "pvs-list__paged-list-item"})
            else:
                edu_blocks = []

        # --- Process each education block ---
        for block in edu_blocks:
            spans = block.find_all("span", {"class": "visually-hidden"})
            if not spans:
                continue

            edu_dict = {}
            # Map spans safely (exact logic from notebook)
            if len(spans) >= 1:
                edu_dict["college"] = spans[0].get_text(strip=True)
            if len(spans) >= 2:
                edu_dict["degree"] = spans[1].get_text(strip=True)
            if len(spans) >= 3:
                edu_dict["duration"] = spans[2].get_text(strip=True)
            if len(spans) >= 4:
                edu_dict["grade"] = spans[3].get_text(strip=True)

            # Only keep entries with a valid college field (exact logic from notebook)
            if edu_dict.get("college"):
                education_data.append(edu_dict)

        logger.info(f"✅ Found {len(education_data)} education entries")

        # Go back if we clicked see all education
        if clicked_see_all_education:
            driver.back()
            sleep(2)

        return education_data

    except Exception as e:
        logger.warning(f"⚠️ Education error: {e}")
        return []


def scrape_projects(driver):
    """Collect all projects, including 'Show all' content.
    Uses the exact logic from the working notebook implementation."""
    try:
        # Try to find and click "see all projects" button
        clicked_see_all_projects = False

        try:
            see_all_projects_btn = WebDriverWait(driver, 5).until(
                EC.presence_of_element_located((By.ID, "navigation-index-see-all-projects"))
            )
            # Scroll into view
            driver.execute_script("arguments[0].scrollIntoView({block: 'center'});", see_all_projects_btn)
            sleep(1)
            try:
                see_all_projects_btn.click()
            except ElementClickInterceptedException:
                # Fallback: force JS click
                driver.execute_script("arguments[0].click();", see_all_projects_btn)

            sleep(3)
            logger.info("✅ Clicked 'see all projects' button")
            clicked_see_all_projects = True

        except (NoSuchElementException, TimeoutException):
            logger.info("ℹ️ 'See all projects' button not found, scraping from main profile page")

        # --- Parse page source ---
        page_source = driver.page_source
        soup = BeautifulSoup(page_source, 'lxml')

        items = []

        if clicked_see_all_projects:
            # We're on the dedicated projects page - look for the main section first
            projects_section = soup.find('section', {'class': 'artdeco-card pb3'})
            if projects_section:
                items = projects_section.find_all('li', {'class': 'pvs-list__paged-list-item'})
            else:
                # Fallback: find all project items on the page
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

        # --- Extract project data using the notebook's get_project logic ---
        def get_project(item):
            spans = item.find_all('span', {'class': 'visually-hidden'})
            item_dict = {}

            # Filter out connection/profile related spans (exact logic from notebook)
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

        # Process all project items
        item_list = []
        for item in items:
            project_data = get_project(item)
            # Only keep valid entries that have a project_name (exact logic from notebook)
            if project_data.get('project_name'):
                item_list.append(project_data)

        logger.info(f"✅ Found {len(item_list)} project entries")

        # Go back if we clicked see all projects
        if clicked_see_all_projects:
            driver.back()
            sleep(2)

        return item_list

    except Exception as e:
        logger.warning(f"⚠️ Projects error: {e}")
        return []


def scrape_experience_by_list_items(driver, timeout=15):
    """Scrape the Experience section, properly grouping roles by company."""
    try:
        driver.execute_script("window.scrollTo(0, document.body.scrollHeight * 0.35);")
        sleep(2)

        def click_element(element):
            try:
                driver.execute_script("arguments[0].scrollIntoView({block: 'center'});", element)
                sleep(0.3)
                driver.execute_script("arguments[0].click();", element)
                return True
            except Exception:
                try:
                    element.click()
                    return True
                except Exception:
                    return False

        clicked_see_all_experience = False
        current_url = driver.current_url

        # --- Try every known "See all experience" pattern ---
        see_all_locators = [
            (By.ID, "navigation-index-see-all-experience"),
            (By.ID, "navigation-index-see-all-experiences"),
            (By.XPATH, "//a[contains(@href, 'see-all-experiences')]"),
            (By.XPATH, "//button[contains(translate(., 'ABCDEFGHIJKLMNOPQRSTUVWXYZ', 'abcdefghijklmnopqrstuvwxyz'), 'see all experience')]"),
            (By.XPATH, "//button[contains(translate(., 'ABCDEFGHIJKLMNOPQRSTUVWXYZ', 'abcdefghijklmnopqrstuvwxyz'), 'show all experience')]")
        ]

        for by, value in see_all_locators:
            try:
                btn = WebDriverWait(driver, 5).until(EC.element_to_be_clickable((by, value)))
                if click_element(btn):
                    logger.info("✅ Clicked a 'See all experience(s)' trigger")
                    clicked_see_all_experience = True
                    WebDriverWait(driver, timeout).until(
                        lambda d: d.current_url != current_url or
                        "see-all-experiences" in d.current_url or
                        len(d.find_elements(By.XPATH, "//section[.//span[text()='Experience']]")) > 0
                    )
                    sleep(2)
                    break
            except Exception:
                continue

        # --- Expand inline "Show more experiences" toggles (for grouped roles) ---
        inline_xpaths = [
            "//button[contains(@aria-label, 'Show more experiences at')]",
            "//button[contains(@aria-label, 'Show all experiences at')]",
            "//button[contains(@aria-label, 'Show more role')]",
            "//button[contains(translate(., 'ABCDEFGHIJKLMNOPQRSTUVWXYZ', 'abcdefghijklmnopqrstuvwxyz'), 'show more experience')]"
        ]
        for xp in inline_xpaths:
            try:
                for btn in driver.find_elements(By.XPATH, xp):
                    click_element(btn)
                    sleep(0.2)
            except Exception:
                continue

        page_source = driver.page_source
        soup = BeautifulSoup(page_source, "lxml")

        experience_sections = []
        if clicked_see_all_experience:
            # Dedicated experience page uses artdeco cards
            experience_sections = soup.find_all("section", {"class": re.compile(r"(experience|artdeco-card)")})
        if not experience_sections:
            # Fallback to main profile section
            section = soup.find("section", id=lambda x: x and "experience" in x.lower())
            if not section:
                section = soup.find("section", {"class": re.compile("experience")})
            if section:
                experience_sections = [section]

        if not experience_sections:
            logger.info("ℹ️ Could not locate an experience section")
            if clicked_see_all_experience:
                driver.back()
                sleep(2)
            return []

        # Look for the main experience container divs (like the one you provided)
        experience_containers = []
        for section in experience_sections:
            # Find divs with the specific class pattern from your HTML
            containers = section.find_all("div", {"class": re.compile(r"lPfzONPqRSDhFlebEZTYwuERDOvWtOkiFSRQLkwnihSqPqLZnPtzCdyDeNUrCIoRrAY")})
            if containers:
                experience_containers.extend(containers)
            else:
                # Fallback: look for li elements as before
                containers = section.find_all("li", {"class": re.compile(r"(?:pvs-list__paged-list-item|artdeco-list__item)")})
                experience_containers.extend(containers)

        if not experience_containers:
            logger.info("ℹ️ No experience containers detected")
            if clicked_see_all_experience:
                driver.back()
                sleep(2)
            return []

        roles_set = {
            "Full-time", "Part-time", "Internship", "Contract", "Self-employed",
            "Freelance", "Apprenticeship", "Volunteer", "Temporary", "Seasonal"
        }
        skip_tokens = ("connection", "connections", "mutual", "profile", "view profile", "followers", "follow", "connect")
        suggestion_cta_keywords = ("connect", "message", "follow")

        def block_is_suggestion(block):
            """Return True when the block represents a sidebar 'People also viewed' card."""
            for btn in block.find_all("button"):
                text = btn.get_text(strip=True).lower()
                if any(keyword in text for keyword in suggestion_cta_keywords):
                    return True
            return False

        def is_duration(value: str) -> bool:
            if not value:
                return False
            s2 = value.lower()
            return (" to " in s2 and ("present" in s2 or "mo" in s2 or "yr" in s2)) or (" yr" in s2) or (" mo" in s2)

        def is_location(value: str) -> bool:
            if not value:
                return False
            if is_duration(value) or value in roles_set:
                return False
            loc_keywords = ["india", "remote", "on-site", "onsite", "hybrid", "work from home"]
            if any(k in value.lower() for k in loc_keywords):
                return True
            return ("," in value and len(value.split()) >= 2)

        def clean_company(value: str) -> str:
            if not value:
                return ""
            result = value
            for r in roles_set:
                result = result.replace(f"· {r}", "").replace(r, "")
            return result.strip("· ").strip()



        def extract_tokens(element):
            spans = element.find_all("span", {"class": "visually-hidden"})
            tokens = []
            for span in spans:
                text = span.get_text(strip=True)
                if not text:
                    continue
                lower = text.lower()
                if any(bad in lower for bad in skip_tokens):
                    continue
                tokens.append(text)
            return tokens

        experiences = []

        for container in experience_containers:
            # Skip suggestion blocks
            container_text = container.get_text(" ", strip=True).lower()
            if any(keyword in container_text for keyword in ["connect", "message", "follow", "view profile"]):
                continue

            # Check if this container has nested roles (ul > li structure)
            nested_ul = container.find("ul", {"class": re.compile(r"NOPXqmTcPBajzuPsitjIEcbHvgQBrYCxAYd")})
            
            if nested_ul:
                # This is a company container with multiple roles
                # Extract company info from the parent container (outside the ul)
                company_tokens = []
                
                # Get all spans from the container but exclude those inside the nested ul
                for span in container.find_all("span", {"class": "visually-hidden"}):
                    # Check if this span is inside the nested ul
                    if nested_ul and nested_ul in span.parents:
                        continue  # Skip spans inside nested roles
                    
                    text = span.get_text(strip=True)
                    if text and not any(bad in text.lower() for bad in skip_tokens):
                        company_tokens.append(text)
                
                # Extract company name and total duration
                company_name = ""
                company_duration = ""
                
                for token in company_tokens:
                    if not company_name and not is_duration(token) and not is_location(token) and token not in roles_set:
                        company_name = clean_company(token)
                    elif is_duration(token) and not company_duration:
                        company_duration = token
                
                if not company_name:
                    continue
                
                # Extract individual roles from nested li elements
                role_items = nested_ul.find_all("li", recursive=False)
                designations = []
                
                for role_item in role_items:
                    role_tokens = extract_tokens(role_item)
                    
                    designation = ""
                    duration = ""
                    location = ""
                    role_type = ""
                    
                    for token in role_tokens:
                        stripped = token.strip()
                        
                        # Skip company name if it appears in role tokens
                        if company_name and stripped.lower() == company_name.lower():
                            continue
                            
                        if stripped in roles_set and not role_type:
                            role_type = stripped
                        elif not designation and not is_duration(stripped) and not is_location(stripped):
                            designation = stripped
                        elif is_duration(stripped) and not duration:
                            duration = stripped
                        elif is_location(stripped) and not location:
                            location = stripped
                    
                    if designation:  # Only add if we have a valid designation
                        designations.append({
                            "designation": designation,
                            "duration": duration,
                            "location": location,
                            "role": role_type
                        })
                
                # Create the company experience entry
                if designations:
                    experiences.append({
                        "company_name": company_name,
                        "duration": company_duration,
                        "designations": designations
                    })
            
            else:
                # This is a single role container (no nested structure)
                tokens = extract_tokens(container)
                
                company_name = ""
                designation = ""
                duration = ""
                location = ""
                role_type = ""
                
                for token in tokens:
                    stripped = token.strip()
                    
                    if stripped in roles_set and not role_type:
                        role_type = stripped
                    elif not designation and not is_duration(stripped) and not is_location(stripped):
                        if not company_name:
                            company_name = clean_company(stripped)
                        else:
                            designation = stripped
                    elif is_duration(stripped) and not duration:
                        duration = stripped
                    elif is_location(stripped) and not location:
                        location = stripped
                
                if company_name and designation:
                    experiences.append({
                        "company_name": company_name,
                        "duration": duration,
                        "designations": [{
                            "designation": designation,
                            "duration": duration,
                            "location": location,
                            "role": role_type
                        }]
                    })
        
        logger.info(f"✅ Found {len(experiences)} companies with {sum(len(exp['designations']) for exp in experiences)} total roles")

        if clicked_see_all_experience:
            driver.back()
            sleep(2)

        return experiences

    except Exception as e:
        logger.warning(f"⚠️ Experience error: {e}")
        return []


def get_experience_tokens(driver, timeout=15):
    """Scroll and fetch all hidden text tokens from the Experience section.
    DEPRECATED: Use scrape_experience_by_list_items instead to avoid duplicate experiences."""
    driver.execute_script("window.scrollTo(0, document.body.scrollHeight * 0.35);")
    sleep(2)

    try:
        exp_section = WebDriverWait(driver, timeout).until(
            EC.presence_of_element_located((By.XPATH, "//section[.//span[text()='Experience']]"))
        )
    except TimeoutException:
        logger.info("ℹ️ No 'Experience' section found on this profile.")
        return []

    exp_html = exp_section.get_attribute("outerHTML")
    exp_soup = BeautifulSoup(exp_html, "lxml")
    tokens = [s.get_text(strip=True) for s in exp_soup.select("span.visually-hidden") if s.get_text(strip=True)]
    return tokens


def parse_experience_tokens(tokens):
    """Parse tokens into clean company_name, designation, duration, location (logic lifted from Linkedin_Final_Code.ipynb)."""
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
        if is_duration(s):
            return False
        if s in roles_set:
            return False
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

    result = []
    i, n = 0, len(tokens)

    while i < n:
        designation, company, dur, loc = "", "", "", ""

        if i < n:
            designation = tokens[i]
            i += 1

        if i < n:
            if tokens[i] not in roles_set and not is_duration(tokens[i]) and not is_location(tokens[i]):
                company = tokens[i]
                i += 1

        if i < n and is_duration(tokens[i]):
            dur = tokens[i]
            i += 1

        if i < n and is_location(tokens[i]):
            loc = tokens[i]
            i += 1

        # Fix: swap if designation looks like duration
        if is_duration(designation):
            dur, designation = designation, ""

        # Skip junk designations, but never skip companies
        if looks_like_description(designation):
            designation = ""

        # Ensure company is always kept if it contains company-like keywords
        if company and any(kw in company.lower() for kw in ["pvt", "inc", "solutions", "system", "hr", "ltd"]):
            pass
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


def scrape_profile_picture(driver, name, profile_url):
    """Extract and save profile picture from LinkedIn profile.
    Returns the relative path to the saved image, or None if not found."""
    try:
        # Create profile_pictures directory if it doesn't exist
        profile_pics_dir = "profile_pictures"
        os.makedirs(profile_pics_dir, exist_ok=True)
        
        # Try multiple selectors for profile picture
        img_selectors = [
            "img.pv-top-card-profile-picture__image",
            "img.profile-photo-edit__preview",
            "img[data-delayed-url*='profile-displayphoto']",
            "img[alt*='profile']",
            "//img[contains(@class, 'profile')]",
            "//img[contains(@src, 'profile')]"
        ]
        
        img_url = None
        img_element = None
        
        # Try to find profile picture using various methods
        for selector in img_selectors:
            try:
                if selector.startswith("//"):
                    # XPath selector
                    img_element = driver.find_element(By.XPATH, selector)
                else:
                    # CSS selector
                    img_element = driver.find_element(By.CSS_SELECTOR, selector)
                
                if img_element:
                    # Try to get image URL from src attribute
                    img_url = img_element.get_attribute("src")
                    if not img_url or img_url == "":
                        # Try data-delayed-url or data-src
                        img_url = img_element.get_attribute("data-delayed-url") or \
                                 img_element.get_attribute("data-src") or \
                                 img_element.get_attribute("data-lazy-src")
                    
                    if img_url and img_url.startswith("http"):
                        break
            except (NoSuchElementException, Exception):
                continue
        
        # If not found via selectors, try BeautifulSoup
        if not img_url:
            try:
                page_source = driver.page_source
                soup = BeautifulSoup(page_source, "lxml")
                
                # Look for profile picture in various ways
                img_tags = soup.find_all("img", src=lambda x: x and ("profile" in x.lower() or "photo" in x.lower()))
                for img in img_tags:
                    src = img.get("src") or img.get("data-delayed-url") or img.get("data-src")
                    if src and src.startswith("http") and ("profile" in src.lower() or "photo" in src.lower()):
                        img_url = src
                        break
            except Exception as e:
                logger.warning(f"⚠️ Error finding profile picture via BeautifulSoup: {e}")
        
        if not img_url or not img_url.startswith("http"):
            logger.info("ℹ️ Profile picture not found")
            return None
        
        # Download the image
        try:
            # Generate filename from profile URL or name
            url_hash = hashlib.md5(profile_url.encode()).hexdigest()[:12]
            safe_name = re.sub(r'[^\w\-_\.]', '_', name or "unknown")[:50]
            filename = f"{safe_name}_{url_hash}.jpg"
            filepath = os.path.join(profile_pics_dir, filename)
            
            # Download image
            headers = {
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
            }
            response = requests.get(img_url, headers=headers, timeout=10, stream=True)
            response.raise_for_status()
            
            # Save image
            with open(filepath, 'wb') as f:
                for chunk in response.iter_content(chunk_size=8192):
                    f.write(chunk)
            
            logger.info(f"✅ Profile picture saved: {filepath}")
            return filepath  # Return relative path
            
        except Exception as e:
            logger.warning(f"⚠️ Error downloading profile picture: {e}")
            return None
            
    except Exception as e:
        logger.warning(f"⚠️ Profile picture error: {e}")
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
            driver.get(profile_url)
            wait.until(EC.presence_of_element_located((By.TAG_NAME, "body")))
            sleep(3)
            
            # Expand all hidden sections before scraping
            expand_all_sections(driver)

            # Scroll fully to load dynamic blocks
            for _ in range(8):
                driver.execute_script("window.scrollBy(0, 800);")
                sleep(1)

            # Expand again after scroll
            expand_all_sections(driver)


            # Progressive scroll
            for _ in range(5):
                driver.execute_script("window.scrollBy(0, document.body.scrollHeight/5);")
                sleep(1)

            # Click "see more" buttons
            for btn_text in ["see more", "See more", "Show all"]:
                try:
                    buttons = driver.find_elements(By.XPATH, f"//button[contains(., '{btn_text}')]")
                    for btn in buttons[:3]:  # Limit to avoid infinite loops
                        try:
                            driver.execute_script("arguments[0].click();", btn)
                            sleep(1)
                        except:
                            pass
                except:
                    continue

            page_source = driver.page_source
            soup = BeautifulSoup(page_source, "lxml")

            # --- NAME ---
            try:
                name_elem = soup.find("h1", class_="text-heading-xlarge")
                if not name_elem:
                    name_elem = soup.find("h1")
                name = name_elem.get_text(strip=True) if name_elem else "N/A"
            except:
                name = "N/A"

            # --- HEADLINE ---
            try:
                headline = soup.find("div", class_="text-body-medium").get_text(strip=True)
            except:
                headline = "N/A"

            # --- ABOUT ---
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
            experience = scrape_experience_by_list_items(driver)
            if not experience:
                tokens = get_experience_tokens(driver)
                if tokens:
                    experience = parse_experience_tokens(tokens)

            # --- EDUCATION ---
            education = scrape_education(driver)

            # --- PROJECTS ---
            projects = scrape_projects(driver)

            # --- LICENSES/CERTIFICATIONS ---
            licenses = scrape_licenses_and_certifications(driver)

            # --- COURSES ---
            try:
                courses_section = driver.find_elements(By.XPATH, 
                    "//section[.//span[contains(text(), 'Course')]]")
                
                courses = []
                if courses_section:
                    courses_html = courses_section[0].get_attribute("outerHTML")
                    courses_soup = BeautifulSoup(courses_html, "lxml")
                    items = courses_soup.find_all("li", {"class": "artdeco-list__item"})
                    if not items:
                        items = courses_soup.find_all("li", {"class": "pvs-list__paged-list-item"})

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
                        filtered_spans = [
                            s.get_text(strip=True) for s in spans
                            if not any(keyword in s.get_text(strip=True).lower() 
                                     for keyword in ['connection', 'mutual', 'profile', 'view'])
                        ]

                        if len(filtered_spans) >= 2:
                            courses.append({
                                'course_name': filtered_spans[0],
                                'associated_with': filtered_spans[1]
                            })
            except Exception as e:
                logger.warning(f"⚠️ Courses error: {e}")
                courses = []

            # --- HONORS & AWARDS ---
            try:
                awards_section = driver.find_elements(By.XPATH, 
                    "//section[.//span[contains(text(), 'Honors') or contains(text(), 'awards')]]")
                
                honors_awards = []
                if awards_section:
                    awards_html = awards_section[0].get_attribute("outerHTML")
                    awards_soup = BeautifulSoup(awards_html, "lxml")
                    items = awards_soup.find_all("li", {"class": "artdeco-list__item"})
                    if not items:
                        items = awards_soup.find_all("li", {"class": "pvs-list__paged-list-item"})

                    for item in items:
                        spans = [s.get_text(strip=True) for s in item.find_all("span", {"class": "visually-hidden"})]
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

                            honors_awards.append(award_dict)
            except Exception as e:
                logger.warning(f"⚠️ Awards error: {e}")
                honors_awards = []

            # --- PROFILE PICTURE ---
            profile_picture_path = scrape_profile_picture(driver, name, profile_url)

            # --- PREPARE PROFILE DATA ---
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
                "profile_picture": profile_picture_path,  # Add profile picture path
                "last_updated": datetime.now()
            }
            
            # Add scraped_at only for new profiles
            if not is_update:
                profile_data["scraped_at"] = datetime.now()

            # --- SAVE OR UPDATE TO MONGODB ---
            if is_update:
                # Update existing profile
                collection.update_one(
                    {"url": profile_url},
                    {"$set": profile_data}
                )
                logger.info(f"🔄 Profile updated: {name}")
                return True, "Profile updated successfully"
            else:
                # Insert new profile
                collection.insert_one(profile_data)
                logger.info(f"✅ Profile saved: {name}")
                return True, "Profile scraped successfully"

        finally:
            driver.quit()

    except Exception as e:
        logger.error(f"❌ Error scraping {profile_url}: {e}")
        return False, str(e)

    finally:
        if "client" in locals():
            client.close()
            