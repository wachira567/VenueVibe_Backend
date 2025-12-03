import os
from fastapi import (
    FastAPI,
    Depends,
    HTTPException,
    status,
    Request,
    File,
    UploadFile,
    Header,
)
from typing import Optional
from fastapi.middleware.cors import CORSMiddleware
from starlette.middleware.sessions import SessionMiddleware
from authlib.integrations.starlette_client import OAuth
from starlette.responses import RedirectResponse
from pydantic import BaseModel
from datetime import datetime, timedelta, date
from sqlalchemy.orm import Session
from models import get_db, User, Venue, Booking, SavedVenue
from passlib.context import CryptContext
from jose import JWTError, jwt
import cloudinary
import cloudinary.uploader
from reportlab.pdfgen import canvas
from reportlab.lib.pagesizes import letter
from reportlab.lib.styles import getSampleStyleSheet
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle
from reportlab.lib import colors
from io import BytesIO

# Load env variables
SECRET_KEY = os.getenv("SECRET_KEY")
GOOGLE_CLIENT_ID = os.getenv("GOOGLE_CLIENT_ID")
GOOGLE_CLIENT_SECRET = os.getenv("GOOGLE_CLIENT_SECRET")
FRONTEND_URL = os.getenv("FRONTEND_URL", "http://localhost:5173")

app = FastAPI(title="VenueVibe API")

# Session middleware for OAuth
app.add_middleware(SessionMiddleware, secret_key=SECRET_KEY)

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

# OAuth setup
oauth = OAuth()
oauth.register(
    name="google",
    client_id=GOOGLE_CLIENT_ID,
    client_secret=GOOGLE_CLIENT_SECRET,
    server_metadata_url="https://accounts.google.com/.well-known/openid-configuration",
    client_kwargs={
        "scope": "openid email profile",
        "state": "fixed_state_for_dev",  # Fixed state for development
    },
)

# Configure Cloudinary
cloudinary.config(
    cloud_name=os.getenv("CLOUDINARY_CLOUD_NAME"),
    api_key=os.getenv("CLOUDINARY_API_KEY"),
    api_secret=os.getenv("CLOUDINARY_API_SECRET"),
)

# JWT settings
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 60 * 24  # 24 hours for development


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
    event_date: str
    end_date: Optional[str] = None
    guest_count: int
    contact_email: str
    contact_phone: Optional[str] = None


# --- Google OAuth Routes ---


@app.get("/login/google")
async def login_google(request: Request):
    redirect_uri = request.url_for("auth_google")
    return await oauth.google.authorize_redirect(request, redirect_uri)


@app.get("/auth/google")
async def auth_google(request: Request, db: Session = Depends(get_db)):
    try:
        token = await oauth.google.authorize_access_token(request)
    except Exception as error:
        raise HTTPException(status_code=401, detail=f"Google login failed: {error}")

    user_info = token.get("userinfo")
    if not user_info:
        raise HTTPException(
            status_code=400, detail="Failed to get user info from Google"
        )

    google_email = user_info["email"]
    google_name = user_info.get("name", google_email.split("@")[0])

    user = db.query(User).filter(User.email == google_email).first()

    if not user:
        user = User(
            username=google_name,
            email=google_email,
            password_hash=None,
            role="Client",
            provider="google",
        )
        db.add(user)
        db.commit()
        db.refresh(user)

    access_token = create_access_token(data={"sub": str(user.id)})

    frontend_url = (
        f"{FRONTEND_URL}/google-callback?token={access_token}&role={user.role}"
    )
    return RedirectResponse(url=frontend_url)


# --- Email Login ---


class LoginSchema(BaseModel):
    email: str
    password: str


@app.post("/token")
def login(login: LoginSchema, db: Session = Depends(get_db)):
    user = db.query(User).filter(User.email == login.email).first()
    if (
        not user or not user.password_hash or login.password != user.password_hash
    ):  # TEMP: plain text
        raise HTTPException(status_code=401, detail="Invalid credentials")

    access_token = create_access_token(data={"sub": str(user.id)})
    return {"access_token": access_token, "token_type": "bearer", "role": user.role}


# --- Endpoints ---


@app.get("/")
def read_root():
    return {"message": "Welcome to VenueVibe API"}


# 1. USERS
@app.post("/users")
def create_user(user: UserSchema, db: Session = Depends(get_db)):
    # Check if email exists
    existing_email = db.query(User).filter(User.email == user.email).first()
    if existing_email:
        raise HTTPException(status_code=400, detail="Email already registered")

    # Check if username exists
    existing_username = db.query(User).filter(User.username == user.username).first()
    if existing_username:
        raise HTTPException(status_code=400, detail="Username already taken")

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
    location: str = None, category: str = None, db: Session = Depends(get_db)
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
    # Parse event_date if it's a string
    if isinstance(booking.event_date, str):
        # Handle YYYY-MM-DD format
        if len(booking.event_date) == 10:  # Date only
            event_date = datetime.strptime(booking.event_date, "%Y-%m-%d")
        else:  # ISO format
            event_date = datetime.fromisoformat(
                booking.event_date.replace("Z", "+00:00")
            )
    else:
        event_date = booking.event_date

    # Parse end_date if provided
    end_date = None
    if booking.end_date:
        if isinstance(booking.end_date, str):
            if len(booking.end_date) == 10:  # Date only
                end_date = datetime.strptime(booking.end_date, "%Y-%m-%d")
            else:  # ISO format
                end_date = datetime.fromisoformat(
                    booking.end_date.replace("Z", "+00:00")
                )
        else:
            end_date = booking.end_date

    # Calculate number of days for the booking
    if end_date:
        days_diff = (
            end_date.date() - event_date.date()
        ).days + 1  # Inclusive of both dates
    else:
        days_diff = 1  # Single day booking

    total_cost = venue.price_per_day * days_diff

    new_booking = Booking(
        user_id=booking.user_id,
        venue_id=booking.venue_id,
        event_date=event_date,
        end_date=end_date,
        guest_count=booking.guest_count,
        total_cost=total_cost,
        status="Pending",  # Default status
        contact_email=booking.contact_email,
        contact_phone=booking.contact_phone,
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


@app.get("/venues/{venue_id}/booked-dates")
def get_venue_booked_dates(venue_id: int, db: Session = Depends(get_db)):
    """Get booked dates for a specific venue (public endpoint)"""
    # Get all approved bookings for this venue
    bookings = (
        db.query(Booking)
        .filter(Booking.venue_id == venue_id, Booking.status == "Approved")
        .all()
    )

    # Return just the dates
    booked_dates = [booking.event_date.strftime("%Y-%m-%d") for booking in bookings]
    return {"booked_dates": booked_dates}


# --- SAVED VENUES ENDPOINTS ---


@app.post("/venues/{venue_id}/save")
def save_venue(
    venue_id: int, Authorization: str = Header(...), db: Session = Depends(get_db)
):
    # Extract token from Authorization header
    auth_header = Authorization
    if not auth_header or not auth_header.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="Not authenticated")

    token = Authorization.split(" ")[1]
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        user_id = payload.get("sub")
        if not user_id:
            raise HTTPException(status_code=401, detail="Invalid token")

        # Find user
        user = db.query(User).filter(User.id == int(user_id)).first()
        if not user:
            raise HTTPException(status_code=404, detail="User not found")

        # Check if venue exists
        venue = db.query(Venue).filter(Venue.id == venue_id).first()
        if not venue:
            raise HTTPException(status_code=404, detail="Venue not found")

        # Check if already saved
        existing_save = (
            db.query(SavedVenue)
            .filter(SavedVenue.user_id == user.id, SavedVenue.venue_id == venue_id)
            .first()
        )

        if existing_save:
            raise HTTPException(status_code=409, detail="Venue already saved")

        # Save the venue
        saved_venue = SavedVenue(user_id=user.id, venue_id=venue_id)
        db.add(saved_venue)
        db.commit()
        return {"message": "Venue saved successfully"}

    except JWTError:
        raise HTTPException(status_code=401, detail="Invalid token")


@app.get("/bookings/{booking_id}/invoice")
def download_invoice(
    booking_id: int, Authorization: str = Header(...), db: Session = Depends(get_db)
):
    # Extract token from Authorization header
    auth_header = Authorization
    if not auth_header or not auth_header.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="Not authenticated")

    token = Authorization.split(" ")[1]
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        user_id = payload.get("sub")
        if not user_id:
            raise HTTPException(status_code=401, detail="Invalid token")

        # Find user by id
        user = db.query(User).filter(User.id == int(user_id)).first()
        if not user:
            raise HTTPException(status_code=404, detail="User not found")

        # Find the booking
        booking = db.query(Booking).filter(Booking.id == booking_id).first()
        if not booking:
            raise HTTPException(status_code=404, detail="Booking not found")

        # Check if the booking belongs to the user
        if booking.user_id != user.id:
            raise HTTPException(status_code=403, detail="Access denied")

        # Get venue details
        venue = db.query(Venue).filter(Venue.id == booking.venue_id).first()
        if not venue:
            raise HTTPException(status_code=404, detail="Venue not found")

        # Create PDF
        buffer = BytesIO()
        doc = SimpleDocTemplate(buffer, pagesize=letter)
        styles = getSampleStyleSheet()
        story = []

        # Title
        title_style = styles["Heading1"]
        title_style.alignment = 1  # Center alignment
        story.append(Paragraph("VENUEVIBE INVOICE", title_style))
        story.append(Spacer(1, 12))

        # Invoice details
        invoice_data = [
            ["Invoice Number:", f"INV-{booking.id:06d}"],
            ["Invoice Date:", datetime.now().strftime("%Y-%m-%d")],
            ["Booking ID:", str(booking.id)],
            ["Event Date:", booking.event_date.strftime("%Y-%m-%d")],
        ]

        invoice_table = Table(invoice_data, colWidths=[120, 200])
        invoice_table.setStyle(
            TableStyle(
                [
                    ("BACKGROUND", (0, 0), (-1, 0), colors.lightblue),
                    ("TEXTCOLOR", (0, 0), (-1, 0), colors.black),
                    ("ALIGN", (0, 0), (-1, -1), "LEFT"),
                    ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
                    ("FONTSIZE", (0, 0), (-1, 0), 12),
                    ("BOTTOMPADDING", (0, 0), (-1, 0), 12),
                    ("BACKGROUND", (0, 1), (-1, -1), colors.white),
                    ("GRID", (0, 0), (-1, -1), 1, colors.black),
                ]
            )
        )
        story.append(invoice_table)
        story.append(Spacer(1, 20))

        # Customer details
        story.append(Paragraph("Bill To:", styles["Heading2"]))
        customer_data = [
            ["Name:", user.username],
            ["Email:", user.email],
            ["Phone:", getattr(user, "phone", "N/A") or "N/A"],
        ]
        customer_table = Table(customer_data, colWidths=[80, 240])
        customer_table.setStyle(
            TableStyle(
                [
                    ("ALIGN", (0, 0), (-1, -1), "LEFT"),
                    ("FONTNAME", (0, 0), (-1, -1), "Helvetica"),
                    ("FONTSIZE", (0, 0), (-1, -1), 10),
                    ("GRID", (0, 0), (-1, -1), 1, colors.black),
                ]
            )
        )
        story.append(customer_table)
        story.append(Spacer(1, 20))

        # Venue details
        story.append(Paragraph("Venue Details:", styles["Heading2"]))
        venue_data = [
            ["Venue:", venue.name if venue else "Unknown Venue"],
            ["Location:", venue.location if venue else "Unknown Location"],
            ["Capacity:", f"{venue.capacity if venue else 0} guests"],
            ["Category:", venue.category if venue else "Unknown"],
        ]
        venue_table = Table(venue_data, colWidths=[80, 240])
        venue_table.setStyle(
            TableStyle(
                [
                    ("ALIGN", (0, 0), (-1, -1), "LEFT"),
                    ("FONTNAME", (0, 0), (-1, -1), "Helvetica"),
                    ("FONTSIZE", (0, 0), (-1, -1), 10),
                    ("GRID", (0, 0), (-1, -1), 1, colors.black),
                ]
            )
        )
        story.append(venue_table)
        story.append(Spacer(1, 20))

        # Booking details
        story.append(Paragraph("Booking Details:", styles["Heading2"]))

        # Calculate duration
        if booking.end_date:
            days_diff = (booking.end_date.date() - booking.event_date.date()).days + 1
            duration_text = f"{days_diff} Day{'s' if days_diff > 1 else ''}"
            date_range = f"{booking.event_date.strftime('%B %d, %Y')} - {booking.end_date.strftime('%B %d, %Y')}"
        else:
            duration_text = "1 Day"
            date_range = booking.event_date.strftime("%B %d, %Y")

        booking_data = [
            ["Event Date:", date_range],
            ["Number of Guests:", str(booking.guest_count)],
            ["Duration:", duration_text],
            ["Contact Email:", booking.contact_email],
        ]
        if booking.contact_phone:
            booking_data.append(["Contact Phone:", booking.contact_phone])

        booking_table = Table(booking_data, colWidths=[120, 200])
        booking_table.setStyle(
            TableStyle(
                [
                    ("ALIGN", (0, 0), (-1, -1), "LEFT"),
                    ("FONTNAME", (0, 0), (-1, -1), "Helvetica"),
                    ("FONTSIZE", (0, 0), (-1, -1), 10),
                    ("GRID", (0, 0), (-1, -1), 1, colors.black),
                ]
            )
        )
        story.append(booking_table)
        story.append(Spacer(1, 20))

        # Cost breakdown
        story.append(Paragraph("Cost Breakdown:", styles["Heading2"]))

        # Calculate days for cost breakdown
        if booking.end_date:
            days = (booking.end_date.date() - booking.event_date.date()).days + 1
        else:
            days = 1

        venue_total = venue.price_per_day * days
        service_fee = venue_total * 0.05

        cost_data = [
            [
                f"Venue Rental ({days} Day{'s' if days > 1 else ''}):",
                f"KES {venue_total:,}",
            ],
            ["Service Fee (5%):", f"KES {int(service_fee)}"],
            ["Total Amount:", f"KES {booking.total_cost:,}"],
        ]

        cost_table = Table(cost_data, colWidths=[150, 170])
        cost_table.setStyle(
            TableStyle(
                [
                    ("ALIGN", (0, 0), (-1, -1), "LEFT"),
                    ("FONTNAME", (0, 0), (-1, -1), "Helvetica"),
                    ("FONTSIZE", (0, 0), (-1, -1), 10),
                    ("GRID", (0, 0), (-1, -1), 1, colors.black),
                    ("BACKGROUND", (0, -1), (-1, -1), colors.lightblue),
                    ("TEXTCOLOR", (0, -1), (-1, -1), colors.black),
                    ("FONTNAME", (0, -1), (-1, -1), "Helvetica-Bold"),
                ]
            )
        )
        story.append(cost_table)
        story.append(Spacer(1, 30))

        # Footer
        footer_style = styles["Normal"]
        footer_style.alignment = 1
        footer_style.fontSize = 8
        story.append(Paragraph("Thank you for choosing VenueVibe!", footer_style))
        story.append(
            Paragraph(
                "For any questions, contact support@venuevibe.co.ke", footer_style
            )
        )

        # Build PDF
        doc.build(story)
        buffer.seek(0)

        # Return PDF as response
        from fastapi.responses import StreamingResponse

        response = StreamingResponse(
            buffer,
            media_type="application/pdf",
            headers={
                "Content-Disposition": f"attachment; filename=venuevibe-invoice-{booking.id}.pdf"
            },
        )

        # Add CORS headers for file downloads
        response.headers["Access-Control-Allow-Origin"] = "*"
        response.headers["Access-Control-Allow-Methods"] = (
            "GET, POST, PUT, DELETE, OPTIONS"
        )
        response.headers["Access-Control-Allow-Headers"] = "*"

        return response

    except JWTError:
        raise HTTPException(status_code=401, detail="Invalid token")


@app.delete("/venues/{venue_id}/save")
def unsave_venue(
    venue_id: int, Authorization: str = Header(...), db: Session = Depends(get_db)
):
    # Extract token from Authorization header
    auth_header = Authorization
    if not auth_header or not auth_header.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="Not authenticated")

    token = Authorization.split(" ")[1]
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        user_id = payload.get("sub")
        if not user_id:
            raise HTTPException(status_code=401, detail="Invalid token")

        # Find user
        user = db.query(User).filter(User.id == int(user_id)).first()
        if not user:
            raise HTTPException(status_code=404, detail="User not found")

        # Find and delete the saved venue
        saved_venue = (
            db.query(SavedVenue)
            .filter(SavedVenue.user_id == user.id, SavedVenue.venue_id == venue_id)
            .first()
        )

        if not saved_venue:
            raise HTTPException(status_code=404, detail="Venue not saved")

        db.delete(saved_venue)
        db.commit()
        return {"message": "Venue unsaved successfully"}

    except JWTError:
        raise HTTPException(status_code=401, detail="Invalid token")


@app.get("/venues/saved")
def get_saved_venues(
    request: Request,
    db: Session = Depends(get_db),
):
    print("get_saved_venues called")
    authorization = request.headers.get("authorization") or request.headers.get(
        "Authorization"
    )
    print(f"Authorization header: {authorization}")
    if not authorization or not authorization.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="Not authenticated")

    token = authorization.split(" ")[1]
    print(f"Token: {token[:50]}...")
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        print(f"Decoded payload: {payload}")
        user_id = payload.get("sub")
        if not user_id:
            raise HTTPException(status_code=401, detail="Invalid token")

        # Debug logging
        print(f"Decoded user_id: {user_id} (type: {type(user_id)})")

        # Convert to int and validate
        try:
            user_id_int = int(user_id)
            print(f"Converted user_id: {user_id_int}")
        except ValueError as e:
            print(f"Error converting user_id to int: {e}")
            raise HTTPException(
                status_code=400, detail=f"Invalid user ID format: {user_id}"
            )

        # Find user
        user = db.query(User).filter(User.id == user_id_int).first()
        if not user:
            raise HTTPException(status_code=404, detail="User not found")
        print(f"Found user: {user.username}")

        # Get saved venues with venue details
        saved_venues = db.query(SavedVenue).filter(SavedVenue.user_id == user.id).all()
        result = []
        for saved in saved_venues:
            venue = db.query(Venue).filter(Venue.id == saved.venue_id).first()
            if venue:
                result.append(
                    {
                        "id": venue.id,
                        "name": venue.name,
                        "location": venue.location,
                        "capacity": venue.capacity,
                        "price_per_day": venue.price_per_day,
                        "category": venue.category,
                        "image_url": venue.image_url,
                    }
                )

        return result

    except JWTError:
        raise HTTPException(status_code=401, detail="Invalid token")
    except Exception as e:
        # Log any other exceptions
        print(f"Error in get_saved_venues: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")


@app.get("/venues/{venue_id}")
def get_venue(venue_id: int, db: Session = Depends(get_db)):
    venue = db.query(Venue).filter(Venue.id == venue_id).first()
    if not venue:
        raise HTTPException(status_code=404, detail="Venue not found")
    return venue


@app.get("/bookings/my-bookings")
def get_user_bookings(authorization: str = Header(...), db: Session = Depends(get_db)):
    # Extract token from Authorization header
    auth_header = authorization
    if not auth_header or not auth_header.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="Not authenticated")

    token = auth_header.split(" ")[1]
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        user_id = payload.get("sub")
        if not user_id:
            raise HTTPException(status_code=401, detail="Invalid token")

        # Find user by id
        user = db.query(User).filter(User.id == int(user_id)).first()
        if not user:
            raise HTTPException(status_code=404, detail="User not found")

        # Get user's bookings with venue information
        bookings = db.query(Booking).filter(Booking.user_id == user.id).all()

        # Add venue information to each booking
        result = []
        for booking in bookings:
            venue = db.query(Venue).filter(Venue.id == booking.venue_id).first()
            booking_dict = {
                "id": booking.id,
                "user_id": booking.user_id,
                "venue_id": booking.venue_id,
                "event_date": booking.event_date,
                "end_date": booking.end_date,
                "guest_count": booking.guest_count,
                "total_cost": booking.total_cost,
                "status": booking.status,
                "contact_email": booking.contact_email,
                "contact_phone": booking.contact_phone,
                "venue_name": venue.name if venue else "Unknown Venue",
                "venue_location": venue.location if venue else "Unknown Location",
            }
            result.append(booking_dict)

        return result

    except JWTError:
        raise HTTPException(status_code=401, detail="Invalid token")


@app.put("/users/profile")
def update_user_profile(
    profile_data: dict, authorization: str = Header(...), db: Session = Depends(get_db)
):
    # Extract token from Authorization header
    auth_header = authorization
    if not auth_header or not auth_header.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="Not authenticated")

    token = auth_header.split(" ")[1]
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        user_id = payload.get("sub")
        if not user_id:
            raise HTTPException(status_code=401, detail="Invalid token")

        # Find user by id
        user = db.query(User).filter(User.id == int(user_id)).first()
        if not user:
            raise HTTPException(status_code=404, detail="User not found")

        # Update user profile
        if "username" in profile_data:
            user.username = profile_data["username"]
        if "email" in profile_data:
            user.email = profile_data["email"]
        if "phone" in profile_data:
            user.phone = profile_data["phone"]
        if "location" in profile_data:
            user.location = profile_data["location"]

        db.commit()
        return {"message": "Profile updated successfully"}

    except JWTError:
        raise HTTPException(status_code=401, detail="Invalid token")


@app.get("/users/me")
def get_current_user(authorization: str = Header(...), db: Session = Depends(get_db)):
    # Extract token from Authorization header
    auth_header = authorization
    if not auth_header or not auth_header.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="Not authenticated")

    token = auth_header.split(" ")[1]
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        user_id = payload.get("sub")
        if not user_id:
            raise HTTPException(status_code=401, detail="Invalid token")

        # Find user by id
        user = db.query(User).filter(User.id == int(user_id)).first()
        if not user:
            raise HTTPException(status_code=404, detail="User not found")

        return {
            "id": user.id,
            "username": user.username,
            "email": user.email,
            "role": user.role,
            "provider": user.provider,
            "phone": user.phone,
            "location": user.location,
        }

    except JWTError:
        raise HTTPException(status_code=401, detail="Invalid token")
