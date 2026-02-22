import os
import sys
from selenium import webdriver
from selenium.webdriver.common.by import By
from time import sleep
from dotenv import load_dotenv
from pymongo import MongoClient
import json
from datetime import datetime

load_dotenv()

class LinkedInScraperIntegration:
    def __init__(self):
        self.driver = None
        self.logged_in = False
        
        # MongoDB connection
        self.client = MongoClient(os.getenv('MONGO_URI', 'mongodb://localhost:27017/'))
        self.db = self.client[os.getenv('DATABASE_NAME', 'Linkedin')]
        self.collection = self.db[os.getenv('COLLECTION_NAME', 'profile_data')]
    
    def login_to_linkedin(self):
        """Login to LinkedIn"""
        if not self.driver:
            self.driver = webdriver.Chrome()
        
        self.driver.get('https://www.linkedin.com/login')
        sleep(2)
        
        email = self.driver.find_element(By.ID, 'username')
        email.send_keys(os.getenv('Email'))
        
        password = self.driver.find_element(By.ID, 'password')
        password.send_keys(os.getenv('Password'))
        
        password.submit()
        sleep(3)
        self.logged_in = True
        print("Logged in to LinkedIn successfully")
    
    def scrape_single_profile(self, profile_url):
        """Scrape a single profile and save to database"""
        try:
            if not self.logged_in:
                self.login_to_linkedin()
            
            # Navigate to profile
            self.driver.get(profile_url)
            sleep(3)
            
            # Basic profile extraction (simplified version)
            profile_data = {
                'url': profile_url,
                'scraped_at': datetime.now(),
                'name': 'Profile Name',  # You'll integrate your scraping logic here
                'headline': 'Professional Headline',
                'status': 'scraped'
            }
            
            # Save to MongoDB
            self.collection.update_one(
                {'url': profile_url},
                {'$set': profile_data},
                upsert=True
            )
            
            print(f"Successfully scraped: {profile_url}")
            return True
            
        except Exception as e:
            print(f"Error scraping {profile_url}: {e}")
            return False
    
    def close(self):
        """Close browser and database connection"""
        if self.driver:
            self.driver.quit()
        if self.client:
            self.client.close()

# Function to be called by Flask app
def scrape_profile_for_flask(url):
    scraper = LinkedInScraperIntegration()
    try:
        result = scraper.scrape_single_profile(url)
        return result
    finally:
        scraper.close()