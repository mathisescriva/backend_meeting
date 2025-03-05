from pydantic import BaseModel
from typing import Optional
from datetime import datetime

class MeetingBase(BaseModel):
    title: str
    file_url: str

class MeetingCreate(MeetingBase):
    pass

class MeetingUpdate(BaseModel):
    title: Optional[str] = None
    transcript_text: Optional[str] = None
    transcript_status: Optional[str] = None

class Meeting(MeetingBase):
    id: str
    user_id: str
    transcript_text: Optional[str] = None
    transcript_status: Optional[str] = "pending"
    created_at: Optional[str] = None

    class Config:
        orm_mode = True
