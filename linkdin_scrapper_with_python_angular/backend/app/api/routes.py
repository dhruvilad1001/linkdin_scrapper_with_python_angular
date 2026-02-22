from fastapi import APIRouter, HTTPException, BackgroundTasks
from fastapi.responses import FileResponse
from typing import List
from datetime import datetime, timedelta
from bson import ObjectId
import logging
import asyncio
from concurrent.futures import ThreadPoolExecutor

from app.models import (
    ProfileResponse, ScrapeRequest, BulkScrapeRequest, 
    ExportRequest, SearchRequest, StatsResponse
)
from app.database import Database
from app.services.scraper_service import LinkedInScraper
from app.services.export_service import ExportService

router = APIRouter()
logger = logging.getLogger(__name__)
executor = ThreadPoolExecutor(max_workers=3)

@router.get("/health")
async def health_check():
    """Health check endpoint"""
    return {"status": "healthy", "timestamp": datetime.now().isoformat()}

@router.get("/profiles", response_model=List[ProfileResponse])
async def get_profiles(skip: int = 0, limit: int = 20, search: str = None):
    """Get all profiles with pagination and search"""
    try:
        collection = Database.get_collection()
        
        query = {}
        if search:
            query = {
                '$or': [
                    {'name': {'$regex': search, '$options': 'i'}},
                    {'headline': {'$regex': search, '$options': 'i'}},
                    {'experience.company_name': {'$regex': search, '$options': 'i'}}
                ]
            }
        
        profiles = await collection.find(query).sort('last_updated', -1).skip(skip).limit(limit).to_list(length=limit)
        
        # Convert ObjectId to string
        for profile in profiles:
            profile['_id'] = str(profile['_id'])
        
        return profiles
    
    except Exception as e:
        logger.error(f"Error fetching profiles: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/profiles/{profile_id}", response_model=ProfileResponse)
async def get_profile(profile_id: str):
    """Get single profile by ID"""
    try:
        collection = Database.get_collection()
        profile = await collection.find_one({'_id': ObjectId(profile_id)})
        
        if not profile:
            raise HTTPException(status_code=404, detail="Profile not found")
        
        profile['_id'] = str(profile['_id'])
        return profile
    
    except Exception as e:
        logger.error(f"Error fetching profile: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/scrape")
async def scrape_profile(request: ScrapeRequest, background_tasks: BackgroundTasks):
    """Scrape a single LinkedIn profile"""
    try:
        url = request.url.strip()
        
        if not url.startswith("https://www.linkedin.com/in/"):
            raise HTTPException(status_code=400, detail="Invalid LinkedIn profile URL")
        
        # Run scraper in background
        def run_scraper():
            scraper = LinkedInScraper()
            return scraper.scrape_profile(url)
        
        loop = asyncio.get_event_loop()
        success, message = await loop.run_in_executor(executor, run_scraper)
        
        if success:
            return {"success": True, "message": message, "url": url}
        else:
            raise HTTPException(status_code=500, detail=message)
    
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Scraping error: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/scrape/bulk")
async def bulk_scrape(request: BulkScrapeRequest, background_tasks: BackgroundTasks):
    """Scrape multiple LinkedIn profiles"""
    try:
        urls = [url.strip() for url in request.urls if url.strip()]
        
        valid_urls = [url for url in urls if url.startswith("https://www.linkedin.com/in/")]
        invalid_urls = [url for url in urls if not url.startswith("https://www.linkedin.com/in/")]
        
        if not valid_urls:
            raise HTTPException(status_code=400, detail="No valid URLs provided")
        
        def bulk_scrape_task():
            scraper = LinkedInScraper()
            results = []
            for url in valid_urls:
                try:
                    success, message = scraper.scrape_profile(url)
                    results.append({"url": url, "success": success, "message": message})
                except Exception as e:
                    results.append({"url": url, "success": False, "message": str(e)})
            return results
        
        background_tasks.add_task(bulk_scrape_task)
        
        return {
            "success": True,
            "message": f"Bulk scraping started for {len(valid_urls)} profiles",
            "valid_urls": valid_urls,
            "invalid_urls": invalid_urls
        }
    
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Bulk scraping error: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/stats", response_model=StatsResponse)
async def get_statistics():
    """Get database statistics"""
    try:
        collection = Database.get_collection()
        
        total_profiles = await collection.count_documents({})
        
        today_start = datetime.now().replace(hour=0, minute=0, second=0, microsecond=0)
        today_profiles = await collection.count_documents({'last_updated': {'$gte': today_start}})
        
        # Top companies
        company_pipeline = [
            {'$unwind': '$experience'},
            {'$group': {'_id': '$experience.company_name', 'count': {'$sum': 1}}},
            {'$sort': {'count': -1}},
            {'$limit': 10}
        ]
        top_companies = await collection.aggregate(company_pipeline).to_list(length=10)
        
        # Top schools
        education_pipeline = [
            {'$unwind': '$education'},
            {'$group': {'_id': '$education.college', 'count': {'$sum': 1}}},
            {'$sort': {'count': -1}},
            {'$limit': 10}
        ]
        top_schools = await collection.aggregate(education_pipeline).to_list(length=10)
        
        return {
            'total_profiles': total_profiles,
            'today_profiles': today_profiles,
            'top_companies': top_companies,
            'top_schools': top_schools
        }
    
    except Exception as e:
        logger.error(f"Error getting statistics: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/export")
async def export_profiles(request: ExportRequest):
    """Export profiles to Excel"""
    try:
        collection = Database.get_collection()
        export_service = ExportService(collection)
        
        filepath, error = await export_service.export_to_excel(request.format, request.filters)
        
        if error:
            raise HTTPException(status_code=500, detail=error)
        
        if filepath:
            return FileResponse(
                filepath,
                media_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
                filename=filepath.split('/')[-1]
            )
        else:
            raise HTTPException(status_code=500, detail="Export failed")
    
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Export error: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.delete("/profiles/{profile_id}")
async def delete_profile(profile_id: str):
    """Delete a profile"""
    try:
        collection = Database.get_collection()
        result = await collection.delete_one({'_id': ObjectId(profile_id)})
        
        if result.deleted_count == 0:
            raise HTTPException(status_code=404, detail="Profile not found")
        
        return {"success": True, "message": "Profile deleted successfully"}
    
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Delete error: {e}")
        raise HTTPException(status_code=500, detail=str(e))
