#!/usr/bin/env python3
"""
Render deployment entry point for VenueVibe Backend
"""

import os
import subprocess
import uvicorn

if __name__ == "__main__":
    # Run database migrations on startup
    print("Running database migrations...")
    try:
        subprocess.run(["alembic", "upgrade", "head"], check=True)
        print("Database migrations completed successfully")
    except subprocess.CalledProcessError as e:
        print(f"Database migration failed: {e}")
        # Continue anyway - database might already be up to date

    # Start the FastAPI server
    port = int(os.environ.get("PORT", 8000))
    print(f"Starting server on port {port}")
    uvicorn.run("app:app", host="0.0.0.0", port=port, reload=False)
