from fastapi import FastAPI

app = FastAPI(title="Event Management API")

@app.get("/")
async def root():
    return {"message": "API is running"}

