import os
from datetime import datetime
from sqlalchemy import Column, Integer, Text, DateTime, ForeignKey, create_engine
from sqlalchemy.orm import declarative_base, sessionmaker, relationship
from dotenv import load_dotenv

# Load env variables
load_dotenv()
DATABASE_URL = os.getenv("DATABASE_URL")

# Setup Engine
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
    password_hash = Column(Text, nullable=False) 
    role = Column(Text, default="Client") # 'Admin' or 'Client'

# --- 2. Venues Table ---
class Venue(Base):
    __tablename__ = "venues"

    id = Column(Integer, primary_key=True)
    name = Column(Text, nullable=False)
    location = Column(Text, nullable=False)
    capacity = Column(Integer, nullable=False)
    price_per_day = Column(Integer, nullable=False)
    category = Column(Text, nullable=False) # 'Garden', 'Hall'
    image_url = Column(Text)
    description = Column(Text)

# --- 3. Bookings Table ---
class Booking(Base):
    __tablename__ = "bookings"

    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey("users.id"))
    venue_id = Column(Integer, ForeignKey("venues.id"))
    event_date = Column(DateTime, nullable=False)
    guest_count = Column(Integer, nullable=False)
    total_cost = Column(Integer, nullable=False)
    status = Column(Text, default="Pending") # 'Pending', 'Approved', 'Rejected'
    
    # Relationships (Optional but helpful for joins)
    user = relationship("User")
    venue = relationship("Venue")