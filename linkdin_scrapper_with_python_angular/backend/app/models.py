from pydantic import BaseModel, Field, HttpUrl
from typing import List, Optional
from datetime import datetime
from bson import ObjectId

class PyObjectId(ObjectId):
    @classmethod
    def __get_validators__(cls):
        yield cls.validate
    
    @classmethod
    def validate(cls, v):
        if not ObjectId.is_valid(v):
            raise ValueError("Invalid ObjectId")
        return ObjectId(v)
    
    @classmethod
    def __get_pydantic_json_schema__(cls, field_schema):
        field_schema.update(type="string")

class Experience(BaseModel):
    company_name: Optional[str] = None
    designation: Optional[str] = None
    duration: Optional[str] = None
    location: Optional[str] = None
    role: Optional[str] = None

class Education(BaseModel):
    college: Optional[str] = None
    degree: Optional[str] = None
    duration: Optional[str] = None
    grade: Optional[str] = None

class Project(BaseModel):
    project_name: Optional[str] = None
    duration: Optional[str] = None
    description: Optional[str] = None
    skills: Optional[str] = None

class License(BaseModel):
    name: Optional[str] = None
    institute: Optional[str] = None
    issued_date: Optional[str] = None

class Course(BaseModel):
    course_name: Optional[str] = None
    associated_with: Optional[str] = None

class HonorAward(BaseModel):
    award_name: Optional[str] = None
    issued_by: Optional[str] = None
    issued_date: Optional[str] = None
    associated_with: Optional[str] = None

class ProfileBase(BaseModel):
    name: str
    url: str
    headline: Optional[str] = None
    about: Optional[str] = None
    experience: List[Experience] = []
    education: List[Education] = []
    projects: List[Project] = []
    licenses: List[License] = []
    courses: List[Course] = []
    honors_awards: List[HonorAward] = []
    profile_picture: Optional[str] = None

class ProfileCreate(ProfileBase):
    pass

class ProfileInDB(ProfileBase):
    id: PyObjectId = Field(default_factory=PyObjectId, alias="_id")
    scraped_at: datetime = Field(default_factory=datetime.now)
    last_updated: datetime = Field(default_factory=datetime.now)
    
    class Config:
        populate_by_name = True
        arbitrary_types_allowed = True
        json_encoders = {ObjectId: str}

class ProfileResponse(ProfileBase):
    id: str = Field(alias="_id")
    scraped_at: Optional[datetime] = None
    last_updated: Optional[datetime] = None
    
    class Config:
        populate_by_name = True

class ScrapeRequest(BaseModel):
    url: str

class BulkScrapeRequest(BaseModel):
    urls: List[str]

class ExportRequest(BaseModel):
    format: str = "grouped"  # grouped or flat
    filters: Optional[dict] = {}

class SearchRequest(BaseModel):
    query: str
    limit: int = 20

class StatsResponse(BaseModel):
    total_profiles: int
    today_profiles: int
    top_companies: List[dict]
    top_schools: List[dict]
