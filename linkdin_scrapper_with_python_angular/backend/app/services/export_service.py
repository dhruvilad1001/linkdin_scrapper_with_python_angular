import pandas as pd
import re
from datetime import datetime
import os
import logging

logger = logging.getLogger(__name__)

class ExportService:
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
            return {"duration": "", "start_date": "", "end_date": ""}
        
        s = self.clean_text(duration_str)
        pattern = r'(\w{3}\s+\d{4})\s+to\s+((?:\w{3}\s+\d{4})|Present)'
        match = re.search(pattern, s, re.IGNORECASE)
        
        if match:
            return {
                "start_date": match.group(1),
                "end_date": match.group(2),
                "duration": s
            }
        
        return {"duration": s, "start_date": "", "end_date": ""}
    
    async def export_to_excel(self, format_type='grouped', filters=None):
        """Export profiles to Excel"""
        try:
            query = filters if filters else {}
            profiles = await self.collection.find(query).to_list(length=None)
            
            if not profiles:
                return None, "No profiles found to export"
            
            if format_type == 'grouped':
                return self._export_grouped_format(profiles)
            else:
                return self._export_flat_format(profiles)
        
        except Exception as e:
            logger.error(f"Export error: {e}")
            return None, str(e)
    
    def _export_grouped_format(self, profiles):
        """Export in grouped format with multiple sheets"""
        try:
            os.makedirs('exports', exist_ok=True)
            filename = f"linkedin_profiles_grouped_{datetime.now().strftime('%Y%m%d_%H%M%S')}.xlsx"
            filepath = os.path.join('exports', filename)
            
            basic_data = []
            exp_data = []
            edu_data = []
            
            for profile in profiles:
                name = self.clean_text(profile.get('name', ''))
                url = self.clean_text(profile.get('url', ''))
                
                basic_data.append({
                    'name': name,
                    'url': url,
                    'headline': self.clean_text(profile.get('headline', '')),
                    'about': self.clean_text(profile.get('about', ''))[:500]
                })
                
                for idx, exp in enumerate(profile.get('experience', [])):
                    dates = self.extract_dates(exp.get('duration', ''))
                    exp_data.append({
                        'name': name if idx == 0 else '',
                        'company_name': self.clean_text(exp.get('company_name', '')),
                        'designation': self.clean_text(exp.get('designation', '')),
                        'duration': dates['duration'],
                        'location': self.clean_text(exp.get('location', ''))
                    })
                
                for idx, edu in enumerate(profile.get('education', [])):
                    edu_data.append({
                        'name': name if idx == 0 else '',
                        'college': self.clean_text(edu.get('college', '')),
                        'degree': self.clean_text(edu.get('degree', '')),
                        'duration': self.clean_text(edu.get('duration', ''))
                    })
            
            with pd.ExcelWriter(filepath, engine='xlsxwriter') as writer:
                if basic_data:
                    pd.DataFrame(basic_data).to_excel(writer, sheet_name='Basic_Info', index=False)
                if exp_data:
                    pd.DataFrame(exp_data).to_excel(writer, sheet_name='Experience', index=False)
                if edu_data:
                    pd.DataFrame(edu_data).to_excel(writer, sheet_name='Education', index=False)
            
            logger.info(f"✅ Exported {len(profiles)} profiles to {filepath}")
            return filepath, None
        
        except Exception as e:
            logger.error(f"Export error: {e}")
            return None, str(e)
    
    def _export_flat_format(self, profiles):
        """Export in flat format (single sheet)"""
        try:
            os.makedirs('exports', exist_ok=True)
            filename = f"linkedin_profiles_flat_{datetime.now().strftime('%Y%m%d_%H%M%S')}.xlsx"
            filepath = os.path.join('exports', filename)
            
            flat_data = []
            for profile in profiles:
                first_exp = profile.get('experience', [{}])[0] if profile.get('experience') else {}
                first_edu = profile.get('education', [{}])[0] if profile.get('education') else {}
                
                flat_data.append({
                    'Name': profile.get('name', ''),
                    'URL': profile.get('url', ''),
                    'Headline': profile.get('headline', ''),
                    'Current_Company': first_exp.get('company_name', ''),
                    'Current_Position': first_exp.get('designation', ''),
                    'Education_College': first_edu.get('college', ''),
                    'Total_Projects': len(profile.get('projects', []))
                })
            
            pd.DataFrame(flat_data).to_excel(filepath, index=False, engine='openpyxl')
            return filepath, None
        
        except Exception as e:
            return None, str(e)
