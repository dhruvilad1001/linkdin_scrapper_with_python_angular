from flask import Flask, render_template, request, jsonify, send_file, redirect, url_for, flash, session
from pymongo import MongoClient
import pandas as pd
from datetime import datetime, timedelta
import os
import json
import subprocess
import threading
from werkzeug.utils import secure_filename
import re
from typing import Dict, List, Any
import logging
from bson import ObjectId
from dotenv import load_dotenv

# Import the actual scraper runner
from scraper_runner import run_linkedin_scraper

# Load environment variables
load_dotenv()

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

app = Flask(__name__)
app.secret_key = os.getenv('SECRET_KEY', 'your-secret-key-change-in-production')
app.config['UPLOAD_FOLDER'] = 'uploads'
app.config['MAX_CONTENT_LENGTH'] = 16 * 1024 * 1024  # 16MB max file size

# MongoDB Configuration from .env file
MONGO_URI = os.getenv('MONGO_URI', 'mongodb://localhost:27017/')
DATABASE_NAME = os.getenv('DATABASE_NAME', 'Linkedin')
COLLECTION_NAME = os.getenv('COLLECTION_NAME', 'profile_data')

# Initialize MongoDB connection
try:
    client = MongoClient(MONGO_URI)
    db = client[DATABASE_NAME]
    collection = db[COLLECTION_NAME]
    client.admin.command('ping')
    logger.info("MongoDB connection established successfully")
except Exception as e:
    logger.error(f"Failed to connect to MongoDB: {e}")
    client = None
    db = None
    collection = None

# Ensure directories exist
os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)
os.makedirs('exports', exist_ok=True)
os.makedirs('templates', exist_ok=True)

class ProfileManager:
    """Handles all profile-related database operations"""
    
    def __init__(self, collection):
        self.collection = collection
    
    def get_all_profiles(self, limit=50, skip=0):
        """Get all profiles with pagination"""
        try:
            if self.collection is None:
                return []
                
            profiles = list(self.collection.find({}, {
                'name': 1, 'headline': 1, 'url': 1, 'last_updated': 1,
                'experience': {'$slice': 1}, 'education': {'$slice': 1}
            }).sort('last_updated', -1).skip(skip).limit(limit))
            
            for profile in profiles:
                profile['_id'] = str(profile['_id'])
                if 'last_updated' in profile and profile['last_updated']:
                    if isinstance(profile['last_updated'], datetime):
                        profile['last_updated'] = profile['last_updated'].strftime('%Y-%m-%d %H:%M:%S')
            
            return profiles
        except Exception as e:
            logger.error(f"Error fetching profiles: {e}")
            return []
    
    def get_profile_by_id(self, profile_id):
        """Get detailed profile by ID"""
        try:
            if self.collection is None:
                return None
                
            profile = self.collection.find_one({'_id': ObjectId(profile_id)})
            if profile:
                profile['_id'] = str(profile['_id'])
                if 'last_updated' in profile and profile['last_updated']:
                    if isinstance(profile['last_updated'], datetime):
                        profile['last_updated'] = profile['last_updated'].strftime('%Y-%m-%d %H:%M:%S')
            return profile
        except Exception as e:
            logger.error(f"Error fetching profile {profile_id}: {e}")
            return None
    
    def search_profiles(self, query, limit=20):
        """Search profiles by name, headline, or company"""
        try:
            if self.collection is None:
                return []
                
            search_filter = {
                '$or': [
                    {'name': {'$regex': query, '$options': 'i'}},
                    {'headline': {'$regex': query, '$options': 'i'}},
                    {'experience.company_name': {'$regex': query, '$options': 'i'}}
                ]
            }
            
            profiles = list(self.collection.find(search_filter, {
                'name': 1, 'headline': 1, 'url': 1, 'last_updated': 1
            }).limit(limit))
            
            for profile in profiles:
                profile['_id'] = str(profile['_id'])
            
            return profiles
        except Exception as e:
            logger.error(f"Error searching profiles: {e}")
            return []
    
    def get_statistics(self):
        """Get database statistics"""
        try:
            if self.collection is None:
                return {'total_profiles': 0, 'today_profiles': 0, 'top_companies': [], 'top_schools': []}
                
            total_profiles = self.collection.count_documents({})
            
            today_start = datetime.now().replace(hour=0, minute=0, second=0, microsecond=0)
            today_profiles = self.collection.count_documents({
                'last_updated': {'$gte': today_start}
            })
            
            company_pipeline = [
                {'$unwind': '$experience'},
                {'$group': {'_id': '$experience.company_name', 'count': {'$sum': 1}}},
                {'$sort': {'count': -1}},
                {'$limit': 10}
            ]
            top_companies = list(self.collection.aggregate(company_pipeline))
            
            education_pipeline = [
                {'$unwind': '$education'},
                {'$group': {'_id': '$education.college', 'count': {'$sum': 1}}},
                {'$sort': {'count': -1}},
                {'$limit': 10}
            ]
            top_schools = list(self.collection.aggregate(education_pipeline))
            
            return {
                'total_profiles': total_profiles,
                'today_profiles': today_profiles,
                'top_companies': top_companies,
                'top_schools': top_schools
            }
        except Exception as e:
            logger.error(f"Error getting statistics: {e}")
            return {'total_profiles': 0, 'today_profiles': 0, 'top_companies': [], 'top_schools': []}
    
    def delete_profile(self, profile_id):
        """Delete a profile by ID"""
        try:
            if self.collection is None:
                return False
                
            result = self.collection.delete_one({'_id': ObjectId(profile_id)})
            return result.deleted_count > 0
        except Exception as e:
            logger.error(f"Error deleting profile {profile_id}: {e}")
            return False

class ScrapingManager:
    """Handles scraping operations"""
    
    @staticmethod
    def validate_linkedin_url(url):
        """Validate if URL is a valid LinkedIn profile URL"""
        pattern = r'^https:\/\/www\.linkedin\.com\/in\/[a-zA-Z0-9\-]+\/?$'
        return re.match(pattern, url) is not None
    
    @staticmethod
    def run_scraper(url):
        """Run the actual scraper for a given URL"""
        try:
            result = run_linkedin_scraper(url)
            if isinstance(result, tuple) and len(result) >= 2:
                success, message = result[0], result[1]
            elif isinstance(result, bool):
                success, message = result, 'OK' if result else 'Failed'
            else:
                success, message = False, f'Unexpected scraper return: {repr(result)}'
            return success, message
        except Exception as e:
            logger.error(f"run_scraper exception: {e}")
            return False, str(e)

class ExportManager:
    """Handles data export operations with proper formatting"""
    
    def __init__(self, collection):
        self.collection = collection
    
    def clean_text(self, text):
        """Clean text data"""
        if text is None:
            return ""
        s = str(text)
        replacements = {
            'Â·': '·', '·': '-', '•': '•', '\xa0': ' ', '\u200b': '',
            '\r\n': ' ', '\r': ' ', '\n': ' '
        }
        for k, v in replacements.items():
            s = s.replace(k, v)
        s = re.sub(r'[\x00-\x1F\x7F]+', ' ', s)
        s = re.sub(r'\s+', ' ', s).strip()
        return s
    
    def extract_dates(self, duration_str):
        """Extract dates from duration string"""
        if not duration_str:
            return {"duration": "", "start_date": "", "end_date": "", "duration_months": ""}
        
        s = self.clean_text(duration_str)
        pattern = r'(\w{3}\s+\d{4})\s+to\s+((?:\w{3}\s+\d{4})|Present)\s*·?\s*(.+)?'
        match = re.search(pattern, s, re.IGNORECASE)
        
        if match:
            duration_text = self.clean_text(match.group(3) or "")
            duration_months = self.convert_duration_to_months(duration_text)
            
            return {
                "start_date": match.group(1),
                "end_date": match.group(2),
                "duration": duration_text,
                "duration_months": duration_months
            }
        
        # If no match, try to extract duration directly
        duration_months = self.convert_duration_to_months(s)
        return {"duration": s, "start_date": "", "end_date": "", "duration_months": duration_months}
    
    def convert_duration_to_months(self, duration_str):
        """Convert duration string to total months"""
        if not duration_str:
            return ""
        
        s = duration_str.lower()
        total_months = 0
        
        # Extract years
        year_match = re.search(r'(\d+)\s*yr', s)
        if year_match:
            total_months += int(year_match.group(1)) * 12
        
        # Extract months
        month_match = re.search(r'(\d+)\s*mo', s)
        if month_match:
            total_months += int(month_match.group(1))
        
        return str(total_months) if total_months > 0 else ""
    
    def extract_location(self, location_str):
        """Extract location details"""
        if not location_str:
            return {"city": "", "state": "", "country": "", "work_mode": ""}
        
        s = self.clean_text(location_str)
        work_mode = ""
        
        for mode in ["Remote", "On-site", "Hybrid", "Onsite"]:
            if mode.lower() in s.lower():
                work_mode = mode
                s = s.replace(mode, "").strip()
        
        s = re.sub(r'\s*·\s*', '', s).strip()
        parts = [p.strip() for p in s.split(',') if p.strip()]
        
        return {
            "city": parts[0] if len(parts) > 0 else "",
            "state": parts[1] if len(parts) > 1 else "",
            "country": parts[2] if len(parts) > 2 else (parts[-1] if parts else ""),
            "work_mode": work_mode
        }
    
    def export_to_excel(self, format_type='grouped', filters=None):
        """Export profiles to Excel with proper formatting"""
        try:
            if self.collection is None:
                return None, "Database not connected"
            
            query = filters if filters else {}
            profiles = list(self.collection.find(query))
            
            if not profiles:
                return None, "No profiles found to export"
            
            if format_type == 'grouped':
                return self._export_grouped_format(profiles)
            else:
                return self._export_flat_format(profiles)
                
        except Exception as e:
            logger.error(f"Error exporting to Excel: {e}")
            return None, str(e)
    
    def _export_grouped_format(self, profiles):
        """Export in grouped format with proper structure"""
        try:
            filename = f"linkedin_profiles_grouped_{datetime.now().strftime('%Y%m%d_%H%M%S')}.xlsx"
            filepath = os.path.join('exports', filename)
            
            basic_data = []
            exp_data = []
            edu_data = []
            proj_data = []
            cert_data = []
            awards_data = []
            courses_data = []
            
            for profile in profiles:
                name = self.clean_text(profile.get('name', ''))
                url = self.clean_text(profile.get('url', ''))
                
                # Basic Info - includes URL
                basic_data.append({
                    'name': name,
                    'url': url,
                    'headline': self.clean_text(profile.get('headline', '')),
                    'about': self.clean_text(profile.get('about', ''))[:500],
                    'last_updated': profile.get('last_updated', '')
                })
                
                # Experience - no URL, name only for first record
                experiences = profile.get('experience', [])
                for idx, exp in enumerate(experiences):
                    dates = self.extract_dates(exp.get('duration', ''))
                    location = self.extract_location(exp.get('location', ''))
                    
                    exp_data.append({
                        'name': name if idx == 0 else '',  # Name only for first record
                        'company_name': self.clean_text(exp.get('company_name', '')),
                        'designation': self.clean_text(exp.get('designation', '')),
                        'employment_type': self.clean_text(exp.get('role', '')),
                        'duration_months': dates['duration_months'],
                        'start_date': dates['start_date'],
                        'end_date': dates['end_date'],
                        'city': location['city'],
                        'state': location['state'],
                        'country': location['country'],
                        'work_mode': location['work_mode']
                    })
                
                # Education - no URL, name only for first record
                educations = profile.get('education', [])
                for idx, edu in enumerate(educations):
                    dates = self.extract_dates(edu.get('duration', ''))
                    
                    edu_data.append({
                        'name': name if idx == 0 else '',  # Name only for first record
                        'college': self.clean_text(edu.get('college', '')),
                        'degree': self.clean_text(edu.get('degree', '')),
                        'duration': dates['duration'],
                        'start_date': dates['start_date'],
                        'end_date': dates['end_date'],
                        'grade': self.clean_text(edu.get('grade', ''))
                    })
                
                # Projects - no URL, name only for first record
                projects = profile.get('projects', [])
                for idx, proj in enumerate(projects):
                    dates = self.extract_dates(proj.get('duration', ''))
                    
                    proj_data.append({
                        'name': name if idx == 0 else '',  # Name only for first record
                        'project_name': self.clean_text(proj.get('project_name', '')),
                        'duration': dates['duration'],
                        'start_date': dates['start_date'],
                        'end_date': dates['end_date'],
                        'description': self.clean_text(proj.get('description', ''))[:200],
                        'skills': self.clean_text(proj.get('skills', ''))
                    })
                
                # Certifications - no URL, name only for first record
                licenses = profile.get('licenses', [])
                for idx, cert in enumerate(licenses):
                    issued = self.clean_text(cert.get('issued_date', ''))
                    match = re.search(r'Issued\s+(\w{3}\s+\d{4})', issued)
                    issued_clean = match.group(1) if match else issued
                    
                    cert_data.append({
                        'name': name if idx == 0 else '',  # Name only for first record
                        'certification_name': self.clean_text(cert.get('name', '')),
                        'issuing_organization': self.clean_text(cert.get('institute', '')),
                        'issue_date': issued_clean
                    })
                
                # Awards - no URL, name only for first record
                awards = profile.get('honors_awards', [])
                for idx, award in enumerate(awards):
                    awards_data.append({
                        'name': name if idx == 0 else '',  # Name only for first record
                        'award_name': self.clean_text(award.get('award_name', '')),
                        'issued_by': self.clean_text(award.get('issued_by', '')),
                        'issue_date': self.clean_text(award.get('issued_date', '')),
                        'associated_with': self.clean_text(award.get('associated_with', ''))
                    })
                
                # Courses - no URL, name only for first record
                courses = profile.get('courses', [])
                for idx, course in enumerate(courses):
                    courses_data.append({
                        'name': name if idx == 0 else '',  # Name only for first record
                        'course_name': self.clean_text(course.get('course_name', '')),
                        'associated_with': self.clean_text(course.get('associated_with', ''))
                    })
            
            # Write to Excel
            with pd.ExcelWriter(filepath, engine='xlsxwriter') as writer:
                workbook = writer.book
                
                header_format = workbook.add_format({
                    'bold': True,
                    'bg_color': '#4472C4',
                    'font_color': 'white',
                    'border': 1
                })
                
                # Basic Info Sheet (with URL)
                if basic_data:
                    df = pd.DataFrame(basic_data)
                    df.to_excel(writer, sheet_name='Basic_Info', index=False)
                    ws = writer.sheets['Basic_Info']
                    for col_num, value in enumerate(df.columns.values):
                        ws.write(0, col_num, value, header_format)
                    ws.set_column('A:A', 25)
                    ws.set_column('B:B', 40)
                    ws.set_column('C:C', 50)
                    ws.set_column('D:D', 60)
                
                # Experience Sheet (no URL)
                if exp_data:
                    df = pd.DataFrame(exp_data)
                    df.to_excel(writer, sheet_name='Experience', index=False)
                    ws = writer.sheets['Experience']
                    for col_num, value in enumerate(df.columns.values):
                        ws.write(0, col_num, value, header_format)
                    ws.set_column('A:A', 20)
                    ws.set_column('B:B', 30)
                    ws.set_column('C:C', 35)
                    ws.set_column('D:D', 20)
                    ws.set_column('E:E', 15)
                
                # Education Sheet (no URL)
                if edu_data:
                    df = pd.DataFrame(edu_data)
                    df.to_excel(writer, sheet_name='Education', index=False)
                    ws = writer.sheets['Education']
                    for col_num, value in enumerate(df.columns.values):
                        ws.write(0, col_num, value, header_format)
                    ws.set_column('A:A', 20)
                    ws.set_column('B:B', 40)
                    ws.set_column('C:C', 40)
                
                # Projects Sheet (no URL)
                if proj_data:
                    df = pd.DataFrame(proj_data)
                    df.to_excel(writer, sheet_name='Projects', index=False)
                    ws = writer.sheets['Projects']
                    for col_num, value in enumerate(df.columns.values):
                        ws.write(0, col_num, value, header_format)
                    ws.set_column('A:A', 20)
                    ws.set_column('B:B', 30)
                    ws.set_column('F:F', 50)
                
                # Certifications Sheet (no URL)
                if cert_data:
                    df = pd.DataFrame(cert_data)
                    df.to_excel(writer, sheet_name='Certifications', index=False)
                    ws = writer.sheets['Certifications']
                    for col_num, value in enumerate(df.columns.values):
                        ws.write(0, col_num, value, header_format)
                    ws.set_column('A:A', 20)
                    ws.set_column('B:B', 40)
                    ws.set_column('C:C', 35)
                
                # Awards Sheet (no URL)
                if awards_data:
                    df = pd.DataFrame(awards_data)
                    df.to_excel(writer, sheet_name='Awards', index=False)
                    ws = writer.sheets['Awards']
                    for col_num, value in enumerate(df.columns.values):
                        ws.write(0, col_num, value, header_format)
                    ws.set_column('A:A', 20)
                    ws.set_column('B:B', 35)
                
                # Courses Sheet (no URL)
                if courses_data:
                    df = pd.DataFrame(courses_data)
                    df.to_excel(writer, sheet_name='Courses', index=False)
                    ws = writer.sheets['Courses']
                    for col_num, value in enumerate(df.columns.values):
                        ws.write(0, col_num, value, header_format)
                    ws.set_column('A:A', 20)
                    ws.set_column('B:B', 40)
            
            logger.info(f"✅ Exported {len(profiles)} profiles to {filepath}")
            return filepath, None
            
        except Exception as e:
            logger.error(f"Export error: {e}")
            return None, str(e)
    
    def _export_flat_format(self, profiles):
        """Export in flat format (single sheet)"""
        try:
            filename = f"linkedin_profiles_flat_{datetime.now().strftime('%Y%m%d_%H%M%S')}.xlsx"
            filepath = os.path.join('exports', filename)
            
            flat_data = []
            for profile in profiles:
                first_exp = profile.get('experience', [{}])[0] if profile.get('experience') else {}
                first_edu = profile.get('education', [{}])[0] if profile.get('education') else {}
                
                # Calculate total experience in months
                total_months = 0
                for exp in profile.get('experience', []):
                    dates = self.extract_dates(exp.get('duration', ''))
                    if dates['duration_months']:
                        total_months += int(dates['duration_months'])
                
                flat_data.append({
                    'Name': profile.get('name', ''),
                    'URL': profile.get('url', ''),
                    'Headline': profile.get('headline', ''),
                    'About': profile.get('about', '')[:300] if profile.get('about') else '',
                    'Current_Company': first_exp.get('company_name', ''),
                    'Current_Position': first_exp.get('designation', ''),
                    'Total_Experience_Months': total_months,
                    'Education_College': first_edu.get('college', ''),
                    'Education_Degree': first_edu.get('degree', ''),
                    'Total_Projects': len(profile.get('projects', [])),
                    'Total_Certifications': len(profile.get('licenses', [])),
                    'Last_Updated': profile.get('last_updated', '')
                })
            
            df = pd.DataFrame(flat_data)
            df.to_excel(filepath, index=False, engine='openpyxl')
            
            return filepath, None
            
        except Exception as e:
            return None, str(e)

# Initialize managers
profile_manager = ProfileManager(collection)
export_manager = ExportManager(collection)

# Routes
@app.route('/')
def dashboard():
    """Main dashboard"""
    try:
        stats = profile_manager.get_statistics()
        recent_profiles = profile_manager.get_all_profiles(limit=5)
        return render_template('dashboard.html', stats=stats, recent_profiles=recent_profiles)
    except Exception as e:
        logger.error(f"Dashboard error: {e}")
        return render_template('dashboard.html', stats={'total_profiles': 0, 'today_profiles': 0, 'top_companies': [], 'top_schools': []}, recent_profiles=[])

@app.route('/profiles')
def profiles():
    """Profiles listing page"""
    try:
        page = request.args.get('page', 1, type=int)
        per_page = 20
        skip = (page - 1) * per_page
        
        search_query = request.args.get('search', '')
        
        if search_query:
            profiles_list = profile_manager.search_profiles(search_query, limit=per_page)
            total_profiles = len(profiles_list)
        else:
            profiles_list = profile_manager.get_all_profiles(limit=per_page, skip=skip)
            total_profiles = collection.count_documents({}) if collection is not None else 0
        
        total_pages = (total_profiles + per_page - 1) // per_page
        
        return render_template('profiles.html', 
                             profiles=profiles_list, 
                             current_page=page, 
                             total_pages=total_pages,
                             search_query=search_query)
    except Exception as e:
        logger.error(f"Profiles page error: {e}")
        return render_template('profiles.html', profiles=[], current_page=1, total_pages=1, search_query='')

@app.route('/profile/<profile_id>')
def profile_detail(profile_id):
    """Profile detail page"""
    try:
        profile = profile_manager.get_profile_by_id(profile_id)
        if not profile:
            flash('Profile not found', 'error')
            return redirect(url_for('profiles'))
        
        return render_template('profile_detail.html', profile=profile)
    except Exception as e:
        logger.error(f"Profile detail error: {e}")
        flash('Error loading profile', 'error')
        return redirect(url_for('profiles'))

@app.route('/scraper')
def scraper():
    """Scraping interface page"""
    return render_template('scraper.html')

@app.route('/analytics')
def analytics():
    """Analytics dashboard"""
    try:
        stats = profile_manager.get_statistics()
        
        recent_activity = []
        if collection is not None:
            pipeline_recent = [
                {'$match': {'last_updated': {'$gte': datetime.now() - timedelta(days=30)}}},
                {'$group': {
                    '_id': {'$dateToString': {'format': '%Y-%m-%d', 'date': '$last_updated'}},
                    'count': {'$sum': 1}
                }},
                {'$sort': {'_id': 1}}
            ]
            recent_activity = list(collection.aggregate(pipeline_recent))
        
        return render_template('analytics.html', stats=stats, recent_activity=recent_activity)
    except Exception as e:
        logger.error(f"Analytics error: {e}")
        return render_template('analytics.html', stats={'total_profiles': 0, 'today_profiles': 0, 'top_companies': [], 'top_schools': []}, recent_activity=[])

# API Routes
@app.route('/api/scrape', methods=['POST'])
def api_scrape():
    """API endpoint to scrape a profile (creates new or updates existing)"""
    try:
        data = request.get_json()
        url = data.get('url', '').strip()
        
        if not url:
            return jsonify({'success': False, 'error': 'URL is required'}), 400
        
        if not ScrapingManager.validate_linkedin_url(url):
            return jsonify({'success': False, 'error': 'Invalid LinkedIn profile URL'}), 400
        
        # Check if profile exists
        is_update = False
        profile_id = None
        if collection is not None:
            existing = collection.find_one({'url': url})
            if existing:
                is_update = True
                profile_id = str(existing['_id'])
        
        # Run scraper (it will handle create or update)
        success, message = ScrapingManager.run_scraper(url)
        
        if success:
            if is_update:
                return jsonify({
                    'success': True, 
                    'message': 'Profile updated successfully',
                    'url': url,
                    'action': 'updated',
                    'profile_id': profile_id
                })
            else:
                # Get the newly created profile ID
                new_profile = collection.find_one({'url': url})
                new_profile_id = str(new_profile['_id']) if new_profile else None
                
                return jsonify({
                    'success': True, 
                    'message': 'Profile scraped and saved successfully',
                    'url': url,
                    'action': 'created',
                    'profile_id': new_profile_id
                })
        else:
            return jsonify({
                'success': False,
                'error': message
            }), 500
        
    except Exception as e:
        logger.error(f"API scrape error: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/api/profiles', methods=['GET'])
def api_get_profiles():
    """API endpoint to get profiles"""
    try:
        page = request.args.get('page', 1, type=int)
        limit = request.args.get('limit', 20, type=int)
        search = request.args.get('search', '')
        
        skip = (page - 1) * limit
        
        if search:
            profiles_list = profile_manager.search_profiles(search, limit=limit)
        else:
            profiles_list = profile_manager.get_all_profiles(limit=limit, skip=skip)
        
        return jsonify({
            'success': True,
            'profiles': profiles_list,
            'page': page,
            'limit': limit
        })
        
    except Exception as e:
        logger.error(f"API get profiles error: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/api/export', methods=['POST'])
def api_export():
    """API endpoint to export profiles"""
    try:
        data = request.get_json() or {}
        format_type = data.get('format', 'grouped')
        filters = data.get('filters', {})
        
        filepath, error = export_manager.export_to_excel(format_type, filters)
        
        if error:
            return jsonify({'success': False, 'error': error}), 500
        
        if filepath and os.path.exists(filepath):
            return send_file(
                filepath, 
                as_attachment=True, 
                download_name=os.path.basename(filepath),
                mimetype='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
            )
        else:
            return jsonify({'success': False, 'error': 'Export file not found'}), 500
            
    except Exception as e:
        logger.error(f"API export error: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/api/stats', methods=['GET'])
def api_get_stats():
    """API endpoint to get statistics"""
    try:
        stats = profile_manager.get_statistics()
        return jsonify({'success': True, 'stats': stats})
    except Exception as e:
        logger.error(f"API get stats error: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/api/bulk-scrape', methods=['POST'])
def api_bulk_scrape():
    """API endpoint for bulk scraping"""
    try:
        data = request.get_json()
        urls = data.get('urls', [])
        
        if not urls:
            return jsonify({'success': False, 'error': 'No URLs provided'}), 400
        
        valid_urls = []
        invalid_urls = []
        existing_urls = []
        
        for url in urls:
            url = url.strip()
            if ScrapingManager.validate_linkedin_url(url):
                # Don't skip existing URLs anymore - they will be updated
                valid_urls.append(url)
                if collection is not None and collection.find_one({'url': url}):
                    existing_urls.append(url)
            else:
                invalid_urls.append(url)
        
        if not valid_urls:
            return jsonify({
                'success': False, 
                'error': 'No valid URLs to scrape',
                'invalid_urls': invalid_urls
            }), 400
        
        def bulk_scrape_background():
            for url in valid_urls:
                try:
                    success, message = ScrapingManager.run_scraper(url)
                    if success:
                        logger.info(f"Bulk scraped: {url}")
                    else:
                        logger.error(f"Failed bulk scraping {url}: {message}")
                except Exception as e:
                    logger.error(f"Bulk scraping error for {url}: {e}")
        
        thread = threading.Thread(target=bulk_scrape_background)
        thread.daemon = True
        thread.start()
        
        return jsonify({
            'success': True,
            'message': f'Bulk scraping started for {len(valid_urls)} profiles ({len(existing_urls)} will be updated)',
            'valid_urls': valid_urls,
            'existing_urls': existing_urls,
            'invalid_urls': invalid_urls
        })
        
    except Exception as e:
        logger.error(f"API bulk scrape error: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500

# Template filters
@app.template_filter('datetime_format')
def datetime_format(value, format='%Y-%m-%d %H:%M'):
    if isinstance(value, str):
        try:
            value = datetime.strptime(value, '%Y-%m-%d %H:%M:%S')
        except:
            return value
    return value.strftime(format) if value else ''

@app.template_filter('truncate_text')
def truncate_text(text, length=100):
    if not text:
        return ''
    return text[:length] + '...' if len(text) > length else text

@app.template_filter('format_number')
def format_number(value):
    try:
        return f"{int(value):,}"
    except:
        return value

# Context processors
@app.context_processor
def inject_stats():
    try:
        if collection is not None:
            basic_stats = {
                'total_profiles': collection.count_documents({}),
                'today_profiles': collection.count_documents({
                    'last_updated': {'$gte': datetime.now().replace(hour=0, minute=0, second=0)}
                })
            }
        else:
            basic_stats = {'total_profiles': 0, 'today_profiles': 0}
        return dict(global_stats=basic_stats)
    except:
        return dict(global_stats={'total_profiles': 0, 'today_profiles': 0})

if __name__ == '__main__':
    # Create necessary directories
    os.makedirs('uploads', exist_ok=True)
    os.makedirs('exports', exist_ok=True)
    os.makedirs('templates', exist_ok=True)
    os.makedirs('static/css', exist_ok=True)
    os.makedirs('static/js', exist_ok=True)
    
    # Run the application
    app.run(debug=True, host='0.0.0.0', port=5000)
