import os 
from fastapi import FastAPI, File, UploadFile, HTTPException 
from fastapi.responses import StreamingResponse 
from pydantic import BaseModel 
from typing import Optional 
from datetime import datetime 
from dotenv import load_dotenv 
import motor.motor_asyncio 
import io 
from bson import ObjectId
from fastapi import HTTPException

def parse_object_id(id_str: str) -> ObjectId:
    """
    Convert a string to ObjectId if valid, else raise 400.
    """
    if ObjectId.is_valid(id_str):
        return ObjectId(id_str)
    else:
        raise HTTPException(status_code=400, detail=f"Invalid ID: {id_str}")


def string_ids(doc):
    """
    Recursively converts ObjectId to str in a dict or list.
    """
    if isinstance(doc, list):
        return [string_ids(d) for d in doc]
    if isinstance(doc, dict):
        new_doc = {}
        for k, v in doc.items():
            if isinstance(v, ObjectId):
                new_doc[k] = str(v)
            elif isinstance(v, (dict, list)):
                new_doc[k] = string_ids(v)
            else:
                new_doc[k] = v
        return new_doc
    return doc
 
# Load environment variables from .env file 
load_dotenv() 
MONGO_URI = os.getenv("MONGO_URI")
 
app = FastAPI() 
 
# Connect to MongoDB Atlas 
client = motor.motor_asyncio.AsyncIOMotorClient(MONGO_URI) 
db = client.test
 
# Data Models 
class Event(BaseModel): 
    name: str 
    description: str 
    date: str 
    venue_id: str 
    max_attendees: int 
 
class Attendee(BaseModel): 
    name: str 
    email: str 
    phone: Optional[str] = None 
 
class Venue(BaseModel): 
    name: str 
    address: str 
    capacity: int 
 
class Booking(BaseModel): 
    event_id: str 
    attendee_id: str 
    ticket_type: str 
    quantity: int 
 
# Event Endpoints 
@app.post("/events") 
async def create_event(event: Event): 
    event_doc = event.dict() 
    result = await db.events.insert_one(event_doc) 
    return {"message": "Event created", "id": str(result.inserted_id)} 
 
@app.get("/events")
async def get_events():
    events = await db.events.find().to_list(100)
    events = string_ids(events) 
    return events

@app.put("/events/{event_id}")
async def update_event(event_id: str, event: Event):
    obj_id = parse_object_id(event_id)  # Safe conversion
    result = await db.events.update_one({"_id": obj_id}, {"$set": event.dict()})
    if result.matched_count == 0:
        raise HTTPException(status_code=404, detail="Event not found")
    return {"message": "Event updated"}


@app.delete("/events/{event_id}")
async def delete_event(event_id: str):
    obj_id = parse_object_id(event_id) 
    result = await db.events.delete_one({"_id": obj_id})
    if result.deleted_count == 0:
        raise HTTPException(status_code=404, detail="Event not found")
    return {"message": "Event deleted"}
 
# Upload Event Poster (Image) 
@app.post("/upload_event_poster/{event_id}") 
async def upload_event_poster(event_id: str, file: UploadFile = File(...)): 
    content = await file.read() 
    poster_doc = { 
        "event_id": event_id, 
        "filename": file.filename, 
        "content_type": file.content_type, 
        "content": content, 
        "uploaded_at": datetime.utcnow() 
    } 
    result = await db.event_posters.insert_one(poster_doc) 
    return {"message": "Event poster uploaded", "id": str(result.inserted_id)} 

