import os
from fastapi import FastAPI, Depends, HTTPException, status, Request, File, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from starlette.middleware.sessions import SessionMiddleware
from authlib.integrations.starlette_client import OAuth
from starlette.responses import RedirectResponse
from pydantic import BaseModel
from datetime import datetime, timedelta
from sqlalchemy.orm import Session
from models import get_db, User, Venue, Booking
from passlib.context import CryptContext
from jose import JWTError, jwt
import cloudinary
import cloudinary.uploader

# Load env variables
SECRET_KEY = os.getenv("SECRET_KEY")
GOOGLE_CLIENT_ID = os.getenv("GOOGLE_CLIENT_ID")
GOOGLE_CLIENT_SECRET = os.getenv("GOOGLE_CLIENT_SECRET")

app = FastAPI(title="VenueVibe API")

# Session middleware for OAuth
app.add_middleware(SessionMiddleware, secret_key=SECRET_KEY)

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

# OAuth setup
oauth = OAuth()
oauth.register(
    name='google',
    client_id=GOOGLE_CLIENT_ID,
    client_secret=GOOGLE_CLIENT_SECRET,
    server_metadata_url='https://accounts.google.com/.well-known/openid-configuration',
    client_kwargs={'scope': 'openid email profile'}
)

# Configure Cloudinary
cloudinary.config(
  cloud_name = os.getenv("CLOUDINARY_CLOUD_NAME"),
  api_key = os.getenv("CLOUDINARY_API_KEY"),
  api_secret = os.getenv("CLOUDINARY_API_SECRET")
)

# JWT settings
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 30

def create_access_token(data: dict, expires_delta: timedelta = None):
    to_encode = data.copy()
    if expires_delta:
        expire = datetime.utcnow() + expires_delta
    else:
        expire = datetime.utcnow() + timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
    return encoded_jwt

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


# --- Google OAuth Routes ---

@app.get("/login/google")
async def login_google(request: Request):
    redirect_uri = request.url_for('auth_google')
    return await oauth.google.authorize_redirect(request, redirect_uri)

@app.get("/auth/google")
async def auth_google(request: Request, db: Session = Depends(get_db)):
    try:
        token = await oauth.google.authorize_access_token(request)
    except Exception as error:
        raise HTTPException(status_code=401, detail=f"Google login failed: {error}")

    user_info = token.get('userinfo')
    if not user_info:
        raise HTTPException(status_code=400, detail="Failed to get user info from Google")

    google_email = user_info['email']
    google_name = user_info.get('name', google_email.split('@')[0])

    user = db.query(User).filter(User.email == google_email).first()

    if not user:
        user = User(
            username=google_name,
            email=google_email,
            password_hash=None,
            role="Client",
            provider="google"
        )
        db.add(user)
        db.commit()
        db.refresh(user)

    access_token = create_access_token(data={"sub": user.username})

    frontend_url = f"http://localhost:3000/google-callback?token={access_token}&role={user.role}"
    return RedirectResponse(url=frontend_url)


# --- Email Login ---

class LoginSchema(BaseModel):
    email: str
    password: str

@app.post("/token")
def login(login: LoginSchema, db: Session = Depends(get_db)):
    user = db.query(User).filter(User.email == login.email).first()
    if not user or not user.password_hash or login.password != user.password_hash:  # TEMP: plain text
        raise HTTPException(status_code=401, detail="Invalid credentials")

    access_token = create_access_token(data={"sub": user.username})
    return {"access_token": access_token, "token_type": "bearer", "role": user.role}


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

    # hashed_password = pwd_context.hash(user.password)
    hashed_password = user.password  # TEMP: plain text for testing
    new_user = User(
        username=user.username,
        email=user.email,
        password_hash=hashed_password,
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
def get_venues(
    location: str = None,
    category: str = None,
    db: Session = Depends(get_db)
):
    # Start with a query that selects everything
    query = db.query(Venue)

    # 1. Apply Location Filter (if provided)
    if location:
        # ilike means "Case Insensitive" (karen matches Karen)
        # f"%{location}%" means it matches partial words (e.g. "West" matches "Westlands")
        query = query.filter(Venue.location.ilike(f"%{location}%"))

    # 2. Apply Category Filter (if provided)
    if category:
        query = query.filter(Venue.category == category)

    return query.all()


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


# --- NEW ENDPOINT: Image Upload (Admin Only) ---
@app.post("/upload")
async def upload_image(file: UploadFile = File(...)):
    # 1. Upload the file to Cloudinary
    result = cloudinary.uploader.upload(file.file)
    # 2. Get the secure URL
    url = result.get("secure_url")
    return {"url": url}


@app.get("/bookings")
def get_bookings(db: Session = Depends(get_db)):
    return db.query(Booking).all()
