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
    if isinstance(doc, list): #in case of lists  find().to_list()
        return [string_ids(d) for d in doc]
    if isinstance(doc, dict): #MongoDB document is a dict
        new_doc = {}
        for k, v in doc.items(): #iterate through key-value pairs
            if isinstance(v, ObjectId): #if value is ObjectId, convert to str
                new_doc[k] = str(v)
            elif isinstance(v, (dict, list)): #if value is dict or list, call recursively for nested conversion
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

#Attendee Endpoints
@app.post("/attendees")
async def create_attendee(attendee: Attendee):
    attendee_doc = attendee.dict()
    result = await db.attendees.insert_one(attendee_doc)
    return {"message": "Attendee created", "id": str(result.inserted_id)}

@app.get("/attendees")
async def get_attendees():
    attendees = await db.attendees.find().to_list(100)
    attendees = string_ids(attendees)
    return attendees

@app.put("/attendees/{attendee_id}")
async def update_attendee(attendee_id: str, attendee: Attendee):
    obj_id = parse_object_id(attendee_id) 
    result = await db.attendees.update_one({"_id": obj_id}, {"$set": attendee.dict()})
    if result.matched_count == 0:
        raise HTTPException(status_code=404, detail="Attendee not found")
    return {"message": "Attendee updated"}

@app.delete("/attendees/{attendee_id}")
async def delete_attendee(attendee_id: str):
    obj_id = parse_object_id(attendee_id) 
    result = await db.attendees.delete_one({"_id": obj_id})
    if result.deleted_count == 0:
        raise HTTPException(status_code=404, detail="Attendee not found")
    return {"message": "Attendee deleted"}

#Venue Endpoints
@app.post("/venues")
async def create_venue(venue: Venue):
    venue_doc = venue.dict()
    result = await db.venues.insert_one(venue_doc)
    return {"message": "Venue created", "id": str(result.inserted_id)}

@app.get("/venues")
async def get_venues():
    venues = await db.venues.find().to_list(100)
    venues = string_ids(venues)
    return venues

@app.put("/venues/{venue_id}")
async def update_venue(venue_id: str, venue: Venue):
    obj_id = parse_object_id(venue_id) 
    result = await db.venues.update_one({"_id": obj_id}, {"$set": venue.dict()})
    if result.matched_count == 0:
        raise HTTPException(status_code=404, detail="Venue not found")
    return {"message": "Venue updated"}

@app.delete("/venues/{venue_id}")
async def delete_venue(venue_id: str):
    obj_id = parse_object_id(venue_id) 
    result = await db.venues.delete_one({"_id": obj_id})
    if result.deleted_count == 0:
        raise HTTPException(status_code=404, detail="Venue not found")
    return {"message": "Venue deleted"}