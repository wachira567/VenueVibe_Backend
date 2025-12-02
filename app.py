from fastapi import FastAPI, Depends, HTTPException, status
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from datetime import datetime
from sqlalchemy.orm import Session
from models import get_db, User, Venue, Booking

app = FastAPI(title="VenueVibe API")

# CORS (Allows React frontend to talk to this backend)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

# --- Pydantic Schemas (Data Validation) ---


class UserSchema(BaseModel):
    username: str
    email: str
    password: str
    role: str = "Client"


class VenueSchema(BaseModel):
    name: str
    location: str
    capacity: int
    price_per_day: int
    category: str
    image_url: str
    description: str


class BookingSchema(BaseModel):
    user_id: int
    venue_id: int
    event_date: datetime
    guest_count: int


# --- Endpoints ---


@app.get("/")
def read_root():
    return {"message": "Welcome to VenueVibe API"}


# 1. USERS
@app.post("/users")
def create_user(user: UserSchema, db: Session = Depends(get_db)):
    # Check if exists
    existing = db.query(User).filter(User.email == user.email).first()
    if existing:
        raise HTTPException(status_code=400, detail="Email already registered")

    new_user = User(
        username=user.username,
        email=user.email,
        password_hash=user.password,
        role=user.role,
    )
    db.add(new_user)
    db.commit()
    return {"message": "User created", "user_id": new_user.id}


# 2. VENUES
@app.post("/venues")
def create_venue(venue: VenueSchema, db: Session = Depends(get_db)):
    new_venue = Venue(
        name=venue.name,
        location=venue.location,
        capacity=venue.capacity,
        price_per_day=venue.price_per_day,
        category=venue.category,
        image_url=venue.image_url,
        description=venue.description,
    )
    db.add(new_venue)
    db.commit()
    return {"message": "Venue added"}


@app.get("/venues")
def get_venues(db: Session = Depends(get_db)):
    return db.query(Venue).all()


# 3. BOOKINGS (The Critical Logic)
@app.post("/bookings")
def create_booking(booking: BookingSchema, db: Session = Depends(get_db)):
    # A. Get the Venue details
    venue = db.query(Venue).filter(Venue.id == booking.venue_id).first()
    if not venue:
        raise HTTPException(status_code=404, detail="Venue not found")

    # B. Capacity Validation
    if booking.guest_count > venue.capacity:
        raise HTTPException(
            status_code=400,
            detail=f"Guest count ({booking.guest_count}) exceeds venue capacity ({venue.capacity})",
        )

    # C. Availability Check 
    # Check if there is already an APPROVED booking for this venue on this date
    # Note: We compare dates only 
    conflict = (
        db.query(Booking)
        .filter(
            Booking.venue_id == booking.venue_id,
            Booking.event_date == booking.event_date,
            Booking.status == "Approved",
        )
        .first()
    )

    if conflict:
        raise HTTPException(
            status_code=400, detail="Venue is not available on this date"
        )

    # D. Calculate Cost & Save
    total_cost = venue.price_per_day  # Flat rate per day

    new_booking = Booking(
        user_id=booking.user_id,
        venue_id=booking.venue_id,
        event_date=booking.event_date,
        guest_count=booking.guest_count,
        total_cost=total_cost,
        status="Pending",  # Default status
    )

    db.add(new_booking)
    db.commit()
    return {"message": "Booking request submitted", "status": "Pending"}


@app.get("/bookings")
def get_bookings(db: Session = Depends(get_db)):
    return db.query(Booking).all()
