#!/usr/bin/env python3
"""
Seed script to populate the VenueVibe database with sample venues.
Run this script to add test data to your database.
"""

import os
import sys
from models import Venue, engine, Session
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

def seed_venues():
    """Add sample venues to the database"""

    # Sample venue data
    venues_data = [
        {
            "name": "Karen Villa Gardens",
            "location": "Karen, Nairobi",
            "capacity": 200,
            "price_per_day": 45000,
            "category": "Garden Parties",
            "image_url": "https://images.unsplash.com/photo-1587316830614-693c312483e9?q=80&w=1350&auto=format&fit=crop",
            "description": "A stunning garden venue with lush greenery, perfect for weddings and garden parties. Features a beautiful gazebo and ample parking."
        },
        {
            "name": "The Aviary Rooftop",
            "location": "Westlands, Nairobi",
            "capacity": 150,
            "price_per_day": 85000,
            "category": "Corporate Events",
            "image_url": "https://images.unsplash.com/photo-1520250497591-112f2f40a3f4?q=80&w=1350&auto=format&fit=crop",
            "description": "Modern rooftop venue with panoramic city views. Ideal for corporate events, product launches, and upscale gatherings."
        },
        {
            "name": "Watamu Blue Bay Resort",
            "location": "Watamu, Coast",
            "capacity": 300,
            "price_per_day": 120000,
            "category": "Beach Resorts",
            "image_url": "https://images.unsplash.com/photo-1571896349842-33c89424de2d?ixlib=rb-1.2.1&auto=format&fit=crop&w=1350&q=80",
            "description": "Luxurious beachfront resort with pristine white sands and turquoise waters. Perfect for destination weddings and beach ceremonies."
        },
        {
            "name": "Nairobi Conference Centre",
            "location": "Central Business District, Nairobi",
            "capacity": 500,
            "price_per_day": 95000,
            "category": "Conference Halls",
            "image_url": "https://images.unsplash.com/photo-1431540015161-0bf868a2d407?q=80&w=400&auto=format&fit=crop",
            "description": "State-of-the-art conference facility with modern AV equipment, multiple breakout rooms, and professional catering services."
        },
        {
            "name": "Limuru Country Club",
            "location": "Limuru, Kiambu",
            "capacity": 250,
            "price_per_day": 65000,
            "category": "Wedding Venues",
            "image_url": "https://images.unsplash.com/photo-1519167758481-83f550bb49b3?q=80&w=2098&auto=format&fit=crop",
            "description": "Elegant country club with manicured gardens, a grand ballroom, and championship golf course. Traditional yet luxurious."
        },
        {
            "name": "Mombasa Yacht Club",
            "location": "Mombasa, Coast",
            "capacity": 180,
            "price_per_day": 75000,
            "category": "Beach Resorts",
            "image_url": "https://images.unsplash.com/photo-1520483602335-3b36d400c576?q=80&w=400&auto=format&fit=crop",
            "description": "Exclusive yacht club with marina views and waterfront dining. Perfect for intimate celebrations and corporate retreats."
        },
        {
            "name": "Kilimani Grand Hall",
            "location": "Kilimani, Nairobi",
            "capacity": 400,
            "price_per_day": 55000,
            "category": "Conference Halls",
            "image_url": "https://images.unsplash.com/photo-1505373877841-8d25f7d46678?q=80&w=400&auto=format&fit=crop",
            "description": "Spacious community hall with modern amenities and flexible seating arrangements. Great for large gatherings and events."
        },
        {
            "name": "Naivasha Sopa Lodge",
            "location": "Naivasha, Nakuru",
            "capacity": 220,
            "price_per_day": 80000,
            "category": "Garden Parties",
            "image_url": "https://images.unsplash.com/photo-1558005530-a6a60305c992?q=80&w=400&auto=format&fit=crop",
            "description": "Lake Naivasha resort with beautiful gardens and wildlife viewing. Ideal for team building events and outdoor celebrations."
        },
        {
            "name": "Westlands Sky Lounge",
            "location": "Westlands, Nairobi",
            "capacity": 120,
            "price_per_day": 60000,
            "category": "Corporate Events",
            "image_url": "https://images.unsplash.com/photo-1516455590571-18256e5bb9ff?q=80&w=400&auto=format&fit=crop",
            "description": "Trendy rooftop lounge with city skyline views. Perfect for networking events, cocktail parties, and modern celebrations."
        },
        {
            "name": "Tsavo Safari Lodge",
            "location": "Tsavo National Park",
            "capacity": 80,
            "price_per_day": 150000,
            "category": "Wedding Venues",
            "image_url": "https://images.unsplash.com/photo-1540541338287-41700207dee6?q=80&w=400&auto=format&fit=crop",
            "description": "Exclusive safari lodge surrounded by wildlife. Unique destination for adventurous couples seeking unforgettable wedding experiences."
        }
    ]

    # Create session
    session = Session()

    try:
        # Check if venues already exist
        existing_count = session.query(Venue).count()
        if existing_count > 0:
            print(f"Database already has {existing_count} venues. Skipping seed.")
            return

        # Add venues
        for venue_data in venues_data:
            venue = Venue(**venue_data)
            session.add(venue)
            print(f"Added venue: {venue.name}")

        # Commit changes
        session.commit()
        print(f"\n✅ Successfully seeded {len(venues_data)} venues to the database!")

    except Exception as e:
        session.rollback()
        print(f"❌ Error seeding database: {e}")
        sys.exit(1)

    finally:
        session.close()

if __name__ == "__main__":
    print("🌱 Seeding VenueVibe database with sample venues...")
    seed_venues()
    print("🎉 Database seeding complete!")