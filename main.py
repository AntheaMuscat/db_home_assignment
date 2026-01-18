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


#Helper functions
def parse_object_id(id_str: str) -> ObjectId:
    """
    Convert a string to ObjectId if valid, else raise 400.
    Used to safely handle IDs passed in URLs.
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
MONGO_URI = os.getenv("MONGO_URI") # MongoDB Atlas connection string
 
app = FastAPI() 
 
# Connect to MongoDB Atlas 
# read/write user for all operations
client = motor.motor_asyncio.AsyncIOMotorClient(MONGO_URI) 
db = client.test # name of database under dbHomeAssignment Cluster

# read-only user for read operations if needed (read/write user used in assignment for simplicity)
# MONGO_URI_RO = os.getenv("MONGO_URI_RO")
# ro_client = motor.motor_asyncio.AsyncIOMotorClient(MONGO_URI_RO)
# ro_db = ro_client.test

#To use ro_db for read operations, replace db with ro_db in relevant endpoints
# events = await db_ro.events.find().to_list(100)
def clean_input(data: dict):
    """Clean input to prevent NoSQL injection.
    Reject nested dictionaries.
    Reject string values containing '$' which is special in Mongo queries."""
    for k,v in data.items():
        if isinstance(v, dict):
            raise HTTPException(status_code=400, detail="Nested dictionaries are not allowed")
        if isinstance(v, str) and ('$' in v):
            raise HTTPException(status_code=400, detail="Invalid characters in input")
        

def safe_update_fields(data: dict, allowed_fields: set) -> dict:
    """Returns only the fields that are allowed to be updated.
    Prevents NoSQL injection by deleting any fields not in allowed_fields."""
    filtered = {k: v for k, v in data.items() if k in allowed_fields}
    clean_input(filtered)
    return filtered
 
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
    
# Allowed fields for safe updates
EVENT_ALLOWED    = {"name", "description", "date", "venue_id", "max_attendees"}
ATTENDEE_ALLOWED = {"name", "email", "phone"}
VENUE_ALLOWED    = {"name", "address", "capacity"}
BOOKING_ALLOWED  = {"event_id", "attendee_id", "ticket_type", "quantity"}
 
# Event Endpoints 
@app.post("/events") 
async def create_event(event: Event): 
    """Create a new event. Saved under the events collection and return the inserted ID."""
    event_doc = event.dict() 
    clean_input(event_doc)
    result = await db.events.insert_one(event_doc) 
    return {"message": "Event created", "id": str(result.inserted_id)} 
 
@app.get("/events")
async def get_events():
    """Retrieve up to a 100 documents from the events collection in this case all documents. 
    Converts ObjectIds to strings before returning."""
    events = await db.events.find().to_list(100)
    events = string_ids(events) 
    return events

@app.put("/events/{event_id}")
async def update_event(event_id: str, event: Event):
    """Update an exisiting event by the event_id inputted in the URL.
    Helper function is called to convert the string Id back to an ObjectId making it 
    usable for MongoDB. If no event with the ID is found, 404."""
    obj_id = parse_object_id(event_id)  
    safe_data = safe_update_fields(event.dict(), EVENT_ALLOWED)
    result = await db.events.update_one({"_id": obj_id}, {"$set": safe_data})
    if result.matched_count == 0:
        raise HTTPException(status_code=404, detail="Event not found")
    return {"message": "Event updated"}


@app.delete("/events/{event_id}")
async def delete_event(event_id: str):
    """Delete an event by the event_id inputted in the URL. 
    If event with that id doesnt exist 404."""
    obj_id = parse_object_id(event_id) 
    result = await db.events.delete_one({"_id": obj_id})
    if result.deleted_count == 0:
        raise HTTPException(status_code=404, detail="Event not found")
    return {"message": "Event deleted"}
 
# Upload Event Poster (Image) 
@app.post("/upload_event_poster/{event_id}") 
async def upload_event_poster(event_id: str, file: UploadFile = File(...)): 
    """Upload an event poster image file linked to an event id.
    The file is saved as binary data in the multimedia_files collection.
    Media type is specified as event_poster for easy retrieval."""
    content = await file.read() 
    poster_doc = { 
        "event_id": event_id, 
        "filename": file.filename, 
        "content_type": file.content_type, 
        "content": content, 
        "media_type": "event_poster",
        "uploaded_at": datetime.utcnow() 
    } 
    clean_input(poster_doc)
    result = await db.multimedia_files.insert_one(poster_doc) 
    return {"message": "Event poster uploaded", "id": str(result.inserted_id)}

# Download Event Poster (Image)
@app.get("/download_event_poster/{poster_id}")
async def download_event_poster(poster_id: str):
    """Download an event poster image file by its ID.
    Validation to make sure file exists and is of media_type event_poster.
    StreamingResponse is used to send the binary data to the browser/Postman."""
    obj_id = parse_object_id(poster_id)
    poster = await db.multimedia_files.find_one({"_id": obj_id, "media_type": "event_poster"})
    if not poster:
        raise HTTPException(status_code=404, detail="Poster not found")

    return StreamingResponse(io.BytesIO(poster["content"]),
                             media_type=poster["content_type"],
                             headers={"Content-Disposition": f"attachment; filename={poster['filename']}"})
    #BytesIO converts byte data to a stream for StreamingResponse
    #content-type = image/png or image/jpeg based on uploaded file
    #Content-Disposition  : attachment - downloads instead of displaying in browser
                            #filename= sets the default filename for download


# Upload Promotional Video (Video)
@app.post("/upload_promo_video/{event_id}")
async def upload_promo_video(event_id: str, file: UploadFile = File(...)):
    """Upload a promotional video file linked to an event id.
    Like event posters, the video is saved as binary data in multimedia_files collection.
    Media type is promo_video for easy retrieval."""
    content = await file.read()
    video_doc = {
        "event_id": event_id,
        "filename": file.filename,
        "content_type": file.content_type,
        "content": content,
        "media_type": "promo_video",
        "uploaded_at": datetime.utcnow()
    }
    clean_input(video_doc)
    result = await db.multimedia_files.insert_one(video_doc)
    return {"message": "Promotional video uploaded", "id": str(result.inserted_id)}

# Download Promotional Video (Video)
@app.get("/download_promo_video/{video_id}")
async def download_promo_video(video_id: str):
    """Download a promotional video file by its ID.
    Validation to make sure file exists and is of media_type promo_video.
    Downloading works the same as event posters."""
    obj_id = parse_object_id(video_id)
    video = await db.multimedia_files.find_one({"_id": obj_id, "media_type": "promo_video"})
    if not video:
        raise HTTPException(status_code=404, detail="Video not found")

    return StreamingResponse(io.BytesIO(video["content"]),
                             media_type=video["content_type"],
                             headers={"Content-Disposition": f"attachment; filename={video['filename']}"})

# Upload Venue Photo (Image)
@app.post("/upload_venue_photo/{venue_id}")
async def upload_venue_photo(venue_id: str, file: UploadFile = File(...)):
    """Upload a venue photo image file linked to a venue id.
    Binary data saved in multimedia_files collection with media_type venue_photo."""
    content = await file.read()
    photo_doc = {
        "venue_id": venue_id,
        "filename": file.filename,
        "content_type": file.content_type,
        "content": content,
        "media_type": "venue_photo",
        "uploaded_at": datetime.utcnow()
    }
    clean_input(photo_doc)
    result = await db.multimedia_files.insert_one(photo_doc)
    return {"message": "Venue photo uploaded", "id": str(result.inserted_id)}

# Download Venue Photo (Image)
@app.get("/download_venue_photo/{photo_id}")
async def download_venue_photo(photo_id: str):
    """Download a venue photo image file by its ID.
    Validation to ensure file exists and is of media_type venue_photo.
    Same downloading as event posters and promo video."""
    obj_id = parse_object_id(photo_id)
    photo = await db.multimedia_files.find_one({"_id": obj_id, "media_type": "venue_photo"})
    if not photo:
        raise HTTPException(status_code=404, detail="Photo not found")

    return StreamingResponse(io.BytesIO(photo["content"]),
                             media_type=photo["content_type"],
                             headers={"Content-Disposition": f"attachment; filename={photo['filename']}"})

#Attendee Endpoints
@app.post("/attendees")
async def create_attendee(attendee: Attendee):
    """Create a new attendee. Saved under the attendees collection and return the inserted ID."""
    attendee_doc = attendee.dict()
    clean_input(attendee_doc)
    result = await db.attendees.insert_one(attendee_doc)
    return {"message": "Attendee created", "id": str(result.inserted_id)}

@app.get("/attendees")
async def get_attendees():
    """Retrieve all attendees found within the attendees collection.
    Converts ObjectIds to strings before returning."""
    attendees = await db.attendees.find().to_list(100)
    attendees = string_ids(attendees)
    return attendees

@app.put("/attendees/{attendee_id}")
async def update_attendee(attendee_id: str, attendee: Attendee):
    """Update an exisiting attendee by the attendee_id inputted in the URL.
        Helper function is called to convert the string Id back to an ObjectId making it
        usable for MongoDB. If no attendee with the ID is found, 404."""
    obj_id = parse_object_id(attendee_id) 
    safe_data = safe_update_fields(attendee.dict(), ATTENDEE_ALLOWED)
    result = await db.attendees.update_one({"_id": obj_id}, {"$set": safe_data})
    if result.matched_count == 0:
        raise HTTPException(status_code=404, detail="Attendee not found")
    return {"message": "Attendee updated"}

@app.delete("/attendees/{attendee_id}")
async def delete_attendee(attendee_id: str):
    """Delete an attendee by the attendee_id inputted in the URL.
     If attendee with that id doesnt exist 404."""
    obj_id = parse_object_id(attendee_id) 
    result = await db.attendees.delete_one({"_id": obj_id})
    if result.deleted_count == 0:
        raise HTTPException(status_code=404, detail="Attendee not found")
    return {"message": "Attendee deleted"}

#Venue Endpoints
@app.post("/venues")
async def create_venue(venue: Venue):
    """Create a new venue. Saved under the venues collection and return the inserted ID."""
    venue_doc = venue.dict()
    clean_input(venue_doc)
    result = await db.venues.insert_one(venue_doc)
    return {"message": "Venue created", "id": str(result.inserted_id)}

@app.get("/venues")
async def get_venues():
    """Retrieve all venues from the venues collection.
    Converts ObjectIds to strings before returning."""
    venues = await db.venues.find().to_list(100)
    venues = string_ids(venues)
    return venues

@app.put("/venues/{venue_id}")
async def update_venue(venue_id: str, venue: Venue):
    """Update an exisiting venue by the venue_id inputted in the URL.
     Helper function is called to convert the string Id back to an ObjectId making it
     usable for MongoDB. If no venue with the ID is found, 404."""
    obj_id = parse_object_id(venue_id) 
    safe_data = safe_update_fields(venue.dict(), VENUE_ALLOWED)
    result = await db.venues.update_one({"_id": obj_id}, {"$set": safe_data})
    if result.matched_count == 0:
        raise HTTPException(status_code=404, detail="Venue not found")
    return {"message": "Venue updated"}

@app.delete("/venues/{venue_id}")
async def delete_venue(venue_id: str):
    """Delete a venue by the venue_id inputted in the URL.
     If venue with that id doesnt exist 404."""
    obj_id = parse_object_id(venue_id) 
    result = await db.venues.delete_one({"_id": obj_id})
    if result.deleted_count == 0:
        raise HTTPException(status_code=404, detail="Venue not found")
    return {"message": "Venue deleted"}

#Booking Endpoints
@app.post("/bookings")
async def create_booking(booking: Booking):
    """Create a new booking. Saved under the bookings collection and return the inserted ID."""
    booking_doc = booking.dict()
    clean_input(booking_doc)
    result = await db.bookings.insert_one(booking_doc)
    return {"message": "Booking created", "id": str(result.inserted_id)}

@app.get("/bookings")
async def get_bookings():
    """Retrieve all bookings from the bookings collection.
    Converts ObjectIds to strings before returning."""
    bookings = await db.bookings.find().to_list(100)
    bookings = string_ids(bookings)
    return bookings

@app.put("/bookings/{booking_id}")
async def update_booking(booking_id: str, booking: Booking):
    """Update an exisiting booking by the booking_id inputted in the URL.
     Helper function is called to convert the string Id back to an ObjectId making it
     usable for MongoDB. If no booking with the ID is found, 404."""
    obj_id = parse_object_id(booking_id) 
    safe_data = safe_update_fields(booking.dict(), BOOKING_ALLOWED)
    result = await db.bookings.update_one({"_id": obj_id}, {"$set": safe_data})
    if result.matched_count == 0:
        raise HTTPException(status_code=404, detail="Booking not found")
    return {"message": "Booking updated"}

@app.delete("/bookings/{booking_id}")
async def delete_booking(booking_id: str):
    """Delete a booking by the booking_id inputted in the URL.
     If booking with that id doesnt exist 404."""
    obj_id = parse_object_id(booking_id) 
    result = await db.bookings.delete_one({"_id": obj_id} )
    if result.deleted_count == 0:
        raise HTTPException(status_code=404, detail="Booking not found")
    return {"message": "Booking deleted"}

