import os
from typing import List, Optional
from fastapi import FastAPI, UploadFile, File, Form, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from pydantic import BaseModel
from datetime import datetime

from database import db, create_document, get_documents
from bson import ObjectId

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Utility to convert Mongo docs

def serialize(doc):
    if not doc:
        return doc
    doc = dict(doc)
    _id = doc.get("_id")
    if isinstance(_id, ObjectId):
        doc["id"] = str(_id)
        del doc["_id"]
    # Convert datetimes to isoformat
    for k, v in list(doc.items()):
        if isinstance(v, datetime):
            doc[k] = v.isoformat()
    return doc


@app.get("/")
def read_root():
    return {"message": "Photo Sorter API"}

@app.get("/test")
def test_database():
    """Simple DB connectivity check"""
    resp = {"database": "❌ Not Connected"}
    try:
        if db is None:
            return resp
        resp["database"] = "✅ Connected"
        resp["collections"] = db.list_collection_names()
        return resp
    except Exception as e:
        return {"database": f"Error: {str(e)[:80]}"}


# Schemas for requests
class PhotoCreate(BaseModel):
    url: str
    filename: str
    place: Optional[str] = None
    year: Optional[int] = None
    people: List[str] = []
    taken_at: Optional[str] = None  # ISO string
    gps_lat: Optional[float] = None
    gps_lon: Optional[float] = None
    notes: Optional[str] = None


@app.post("/api/photos")
def add_photo(payload: PhotoCreate):
    try:
        data = payload.model_dump()
        # Convert taken_at to datetime
        if data.get("taken_at"):
            try:
                data["taken_at"] = datetime.fromisoformat(data["taken_at"])  
            except Exception:
                data["taken_at"] = None
        photo_id = create_document("photo", data)
        return {"id": photo_id}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/photos")
def list_photos(place: Optional[str] = None, year: Optional[int] = None, person: Optional[str] = None, limit: int = 100):
    try:
        filter_dict = {}
        if place:
            filter_dict["place"] = place
        if year is not None and str(year) != "":
            try:
                filter_dict["year"] = int(year)
            except Exception:
                pass
        if person:
            filter_dict["people"] = {"$in": [person]}
        docs = get_documents("photo", filter_dict, limit)
        return [serialize(d) for d in docs]
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


class PersonCreate(BaseModel):
    name: str
    alias: Optional[str] = None

@app.post("/api/people")
def create_person(p: PersonCreate):
    try:
        pid = create_document("person", {"name": p.name, "alias": p.alias, "photo_count": 0})
        return {"id": pid}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/people")
def list_people(limit: int = 200):
    try:
        docs = get_documents("person", {}, limit)
        return [serialize(d) for d in docs]
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# Simple face identification placeholder using a naive heuristic
# In a real app, you'd integrate an ML service. Here we'll accept a list of names
# and attach them to a photo by id or url.
class IdentifyRequest(BaseModel):
    photo_url: str
    people: List[str]

@app.post("/api/identify")
def identify_people(req: IdentifyRequest):
    try:
        # Update photo document to include people tags
        if db is None:
            raise Exception("Database not configured")
        result = db["photo"].update_one({"url": req.photo_url}, {"$addToSet": {"people": {"$each": req.people}}, "$set": {"updated_at": datetime.utcnow()}})
        # Increment person photo_count
        for name in req.people:
            db["person"].update_one({"name": name}, {"$inc": {"photo_count": 1}}, upsert=True)
        return {"matched": result.matched_count, "modified": result.modified_count}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# Aggregate endpoint to fetch available filters
@app.get("/api/filters")
def get_filters():
    try:
        if db is None:
            raise Exception("Database not configured")
        pipeline = [
            {"$group": {
                "_id": None,
                "places": {"$addToSet": "$place"},
                "years": {"$addToSet": "$year"},
            }},
            {"$project": {"_id": 0}}
        ]
        agg = list(db["photo"].aggregate(pipeline))
        places = []
        years = []
        if agg:
            data = agg[0]
            places = [p for p in data.get("places", []) if p]
            years = [y for y in data.get("years", []) if y is not None]
        # people from people collection
        ppl = [d.get("name") for d in db["person"].find({}, {"name": 1})]
        return {"places": sorted(places), "years": sorted(years), "people": sorted(ppl)}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# Seed mock data for gallery demo
@app.post("/api/mock/seed")
def seed_mock():
    try:
        if db is None:
            raise Exception("Database not configured")
        photos = [
            {
                "url": "https://images.unsplash.com/photo-1529626455594-4ff0802cfb7e?w=800",
                "filename": "friends-park.jpg",
                "place": "Central Park",
                "year": 2019,
                "people": ["Alice", "Bob"],
            },
            {
                "url": "https://images.unsplash.com/photo-1544005313-94ddf0286df2?w=800",
                "filename": "portrait-alice.jpg",
                "place": "Studio",
                "year": 2020,
                "people": ["Alice"],
            },
            {
                "url": "https://images.unsplash.com/photo-1517841905240-472988babdf9?w=800",
                "filename": "dog-walk.jpg",
                "place": "Brooklyn",
                "year": 2018,
                "people": ["Bob"],
            },
            {
                "url": "https://images.unsplash.com/photo-1500648767791-00dcc994a43e?w=800",
                "filename": "city-trip.jpg",
                "place": "Tokyo",
                "year": 2023,
                "people": ["Charlie", "Dana"],
            },
            {
                "url": "https://images.unsplash.com/photo-1500530855697-b586d89ba3ee?w=800",
                "filename": "mountain-hike.jpg",
                "place": "Alps",
                "year": 2021,
                "people": ["Alice", "Charlie"],
            },
        ]
        # Upsert photos (avoid duplicates by URL)
        inserted = 0
        for p in photos:
            existing = db["photo"].find_one({"url": p["url"]})
            if existing:
                continue
            p["created_at"] = datetime.utcnow()
            db["photo"].insert_one(p)
            inserted += 1
        # Recompute people counts
        # gather counts from photos collection
        counts = {}
        for doc in db["photo"].find({}, {"people": 1}):
            for name in doc.get("people", []):
                counts[name] = counts.get(name, 0) + 1
        for name, cnt in counts.items():
            db["person"].update_one({"name": name}, {"$set": {"photo_count": cnt}}, upsert=True)
        return {"inserted": inserted, "people": counts}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


if __name__ == "__main__":
    import uvicorn
    port = int(os.getenv("PORT", 8000))
    uvicorn.run(app, host="0.0.0.0", port=port)
