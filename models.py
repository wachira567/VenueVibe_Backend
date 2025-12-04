import os
from datetime import datetime
from sqlalchemy import (
    Column,
    Integer,
    Text,
    DateTime,
    ForeignKey,
    create_engine,
    UniqueConstraint,
)
from sqlalchemy.orm import declarative_base, sessionmaker, relationship
from dotenv import load_dotenv

# Load env variables
load_dotenv()
DATABASE_URL = os.getenv("DATABASE_URL")

# Setup Engine
# Use pg8000 for PostgreSQL (compatible with Python 3.13)
if DATABASE_URL:
    if DATABASE_URL.startswith("postgresql://"):
        # Convert postgresql:// to postgresql+pg8000://
        DATABASE_URL = DATABASE_URL.replace("postgresql://", "postgresql+pg8000://", 1)

    # For Neon, simplify the connection string (remove problematic parameters)
    if "neon.tech" in DATABASE_URL:
        # Parse and rebuild URL without problematic query parameters
        base_url = DATABASE_URL.split('?')[0]  # Remove query parameters
        DATABASE_URL = f"{base_url}?sslmode=require"

engine = create_engine(DATABASE_URL, echo=True)
Session = sessionmaker(bind=engine)
Base = declarative_base()


def get_db():
    session = Session()
    try:
        yield session
    finally:
        session.close()


# --- 1. Users Table ---
class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True)
    username = Column(Text, unique=True, nullable=False)
    email = Column(Text, unique=True, nullable=False)
    password_hash = Column(Text, nullable=True)  # Allow None for Google users
    role = Column(Text, default="Client")  # 'Admin' or 'Client'
    provider = Column(Text, default="email")  # 'email' or 'google'
    phone = Column(Text, nullable=True)
    location = Column(Text, nullable=True)


# --- 2. Venues Table ---
class Venue(Base):
    __tablename__ = "venues"

    id = Column(Integer, primary_key=True)
    name = Column(Text, nullable=False)
    location = Column(Text, nullable=False)
    capacity = Column(Integer, nullable=False)
    price_per_day = Column(Integer, nullable=False)
    category = Column(Text, nullable=False)  # 'Garden', 'Hall'
    image_url = Column(Text)
    description = Column(Text)


# --- 3. Bookings Table ---
class Booking(Base):
    __tablename__ = "bookings"

    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey("users.id"))
    venue_id = Column(Integer, ForeignKey("venues.id"))
    event_date = Column(DateTime, nullable=False)
    end_date = Column(DateTime, nullable=True)  # Optional end date for multi-day bookings
    guest_count = Column(Integer, nullable=False)
    total_cost = Column(Integer, nullable=False)
    status = Column(Text, default="Pending")  # 'Pending', 'Approved', 'Rejected'
    contact_email = Column(Text, nullable=True)  # Will be required in booking form
    contact_phone = Column(Text, nullable=True)  # Optional contact phone

    # Relationships (Optional but helpful for joins)
    user = relationship("User")
    venue = relationship("Venue")


# --- 4. Saved Venues Table ---
class SavedVenue(Base):
    __tablename__ = "saved_venues"

    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey("users.id"))
    venue_id = Column(Integer, ForeignKey("venues.id"))
    saved_at = Column(DateTime, default=datetime.utcnow)

    # Relationships
    user = relationship("User")
    venue = relationship("Venue")

    # Unique constraint to prevent duplicate saves
    __table_args__ = (
        UniqueConstraint("user_id", "venue_id", name="unique_user_venue_save"),
    )
