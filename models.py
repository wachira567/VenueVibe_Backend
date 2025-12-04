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

# 1. Get the URL exactly as Neon gives it
DATABASE_URL = os.getenv("DATABASE_URL")

# 2. Fix the "postgres://" legacy bug (Render sometimes provides 'postgres://' but SQLAlchemy needs 'postgresql://')
if DATABASE_URL and DATABASE_URL.startswith("postgres://"):
    DATABASE_URL = DATABASE_URL.replace("postgres://", "postgresql://", 1)

# 3. Create Engine with "Pre-Ping" (CRITICAL FOR NEON)
engine = create_engine(
    DATABASE_URL,
    echo=True,
    pool_pre_ping=True,   # <--- Checks connection before use (Fixes SSL closed error)
    pool_recycle=300,     # <--- Recycle connections every 5 minutes
    pool_size=5,          # <--- Keep 5 connections open
    max_overflow=10       # <--- Allow 10 extra during spikes
)
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
