# Project Overview
This assignment requires the development and hosting of a RESTful web API that connects to a MongoDB Atlas database to store event management data. The system will manage events, attendees, venues, ticket bookings and multimedia assets including event posters (images), promotional videos and venue photos.

# Task 1
## Environment
 - Created Virtual Environment
 - python -m venv .venv
 - venv\Scripts\activate

## Downloaded Items
 - Fast API
 - Uvicorn
 - Motor
 - Pydantic
 - Python-dotenv
 - Requests

# Task 2
## Schema Design
 The schema was design on Datagrip, the collections: attendees, bookings, events, multimedia_files and venues were created and populated with 2 documents each.

## Schema Deployment
  A cluster was created on MongoDB Atlas to hold the collections. A connection between DataGrip and MongoDB Atlas was created using the uri provided by Atlas. The URI was also added to the .env file.
  The schema was run and the populated collections got added to MongoDB Atlas.

# Task 3
 - pip install python-multipart - Needed to handle file uploads.
 
## Develop API Endpoints
 Developed endpoints for CRUD:
 - Events: /events
 - Attendees: /attendees
 - Venues: /venues
 - Bookings: /bookings

Developed endpoints for file uploads and retrievals (downloads)
 - Event Posters: /upload_event_poster/{event_id} and /download_event_poster/{poster_id}
 - Promotional Videos: /upload_promo_video/{event_id} and /download_promo_video/{video_id}
 - Venue Photos: /upload_venue_photo/{venue_id} and /download_venue_photo/{photo_id}

 ## Testing
 All endpoints were tested using Postman:
 - CRUD operation endpoints
 - File uploads and downloads endpoints
 All returned a 200 OK