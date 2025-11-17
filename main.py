import os
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import List, Optional

from database import db, get_documents, create_document
from schemas import Tutor, Availability

app = FastAPI(title="Tutoring API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


class TutorOut(BaseModel):
    id: str
    name: str
    subjects: List[str]
    bio: Optional[str] = None
    location: Optional[str] = None
    photo_url: Optional[str] = None
    rating: Optional[float] = None
    availabilities: List[dict] = []


@app.get("/")
def read_root():
    return {"message": "Tutoring API is running"}


@app.get("/api/tutors", response_model=List[TutorOut])
def list_tutors():
    if db is None:
        raise HTTPException(status_code=500, detail="Database not configured")

    tutors = get_documents("tutor")

    results: List[TutorOut] = []
    for t in tutors:
        tutor_id = str(t.get("_id"))
        # fetch availabilities for this tutor
        avails = list(db["availability"].find({"tutor_id": tutor_id}))
        for a in avails:
            a["id"] = str(a.get("_id"))
            a.pop("_id", None)
        results.append(TutorOut(
            id=tutor_id,
            name=t.get("name"),
            subjects=t.get("subjects", []),
            bio=t.get("bio"),
            location=t.get("location"),
            photo_url=t.get("photo_url"),
            rating=t.get("rating"),
            availabilities=avails
        ))

    return results


@app.post("/api/seed")
def seed_sample_data():
    if db is None:
        raise HTTPException(status_code=500, detail="Database not configured")

    tutor_count = db["tutor"].count_documents({})
    if tutor_count > 0:
        return {"message": "Data already exists", "tutors": tutor_count}

    tutors = [
        Tutor(
            name="Alex Chen",
            subjects=["Math", "Physics"],
            bio="STEM tutor with 7+ years helping high school and college students.",
            location="San Francisco, CA",
            photo_url="https://images.unsplash.com/photo-1544005313-94ddf0286df2?w=400",
            rating=4.8,
        ),
        Tutor(
            name="Priya Sharma",
            subjects=["English", "Writing", "SAT"],
            bio="Former teacher specializing in test prep and essays.",
            location="New York, NY",
            photo_url="https://images.unsplash.com/photo-1524504388940-b1c1722653e1?w=400",
            rating=4.9,
        ),
        Tutor(
            name="Miguel Alvarez",
            subjects=["Chemistry", "Biology"],
            bio="Patient explainer of tricky science concepts.",
            location="Austin, TX",
            photo_url="https://images.unsplash.com/photo-1547425260-76bcadfb4f2c?w=400",
            rating=4.7,
        ),
    ]

    tutor_ids: List[str] = []
    for t in tutors:
        tid = create_document("tutor", t)
        tutor_ids.append(tid)

    # create some availability slots
    import datetime as dt
    today = dt.date.today()

    slots = [
        Availability(tutor_id=tutor_ids[0], date=str(today + dt.timedelta(days=1)), time="3:00 PM - 5:00 PM", location="Downtown Library", notes="SAT practice"),
        Availability(tutor_id=tutor_ids[0], date=str(today + dt.timedelta(days=3)), time="10:00 AM - 12:00 PM", location="Online", notes=None),
        Availability(tutor_id=tutor_ids[1], date=str(today + dt.timedelta(days=2)), time="4:00 PM - 6:00 PM", location="Union Square", notes="Essay review"),
        Availability(tutor_id=tutor_ids[1], date=str(today + dt.timedelta(days=5)), time="1:00 PM - 2:30 PM", location="Online", notes=None),
        Availability(tutor_id=tutor_ids[2], date=str(today + dt.timedelta(days=1)), time="9:00 AM - 11:00 AM", location="Campus Cafe", notes="Lab concepts"),
    ]

    for s in slots:
        create_document("availability", s)

    return {"message": "Seeded sample tutors and availability", "tutors": len(tutors), "slots": len(slots)}


@app.get("/test")
def test_database():
    response = {
        "backend": "✅ Running",
        "database": "❌ Not Available",
        "database_url": None,
        "database_name": None,
        "connection_status": "Not Connected",
        "collections": []
    }

    try:
        if db is not None:
            response["database"] = "✅ Available"
            response["database_url"] = "✅ Configured"
            response["database_name"] = db.name if hasattr(db, 'name') else "✅ Connected"
            response["connection_status"] = "Connected"
            try:
                collections = db.list_collection_names()
                response["collections"] = collections[:10]
                response["database"] = "✅ Connected & Working"
            except Exception as e:
                response["database"] = f"⚠️  Connected but Error: {str(e)[:50]}"
        else:
            response["database"] = "⚠️  Available but not initialized"
    except Exception as e:
        response["database"] = f"❌ Error: {str(e)[:50]}"

    import os
    response["database_url"] = "✅ Set" if os.getenv("DATABASE_URL") else "❌ Not Set"
    response["database_name"] = "✅ Set" if os.getenv("DATABASE_NAME") else "❌ Not Set"

    return response


if __name__ == "__main__":
    import uvicorn
    port = int(os.getenv("PORT", 8000))
    uvicorn.run(app, host="0.0.0.0", port=port)
