# VenueVibe Backend

A robust FastAPI-based backend API for the VenueVibe venue booking platform. This API provides comprehensive venue management, user authentication, booking processing, and administrative functionality.

## Project Overview

VenueVibe Backend is the server-side component of a full-stack venue booking platform. It handles data persistence, business logic, authentication, file uploads, and provides RESTful API endpoints for the frontend application.

## Live Deployment

- **Backend API:** https://venuevibe-backend.onrender.com/
- **API Documentation:** https://venuevibe-backend.onrender.com/docs
- **Frontend Application:** https://venue-vibe-frontend-git-main-washiras-projects-fb5072e5.vercel.app

## Repository Links

- **Backend Repository:** https://github.com/wachira567/VenueVibe_Backend
- **Frontend Repository:** https://github.com/wachira567/VenueVibe_Frontend

## Features

### Core Functionality

- **Venue Management:** CRUD operations for venue listings with image uploads
- **User Authentication:** JWT-based authentication with email/password and Google OAuth
- **Booking System:** Comprehensive booking management with availability checking
- **Invoice Generation:** PDF invoice creation using ReportLab
- **Saved Venues:** User-specific venue bookmarking system

### Administrative Features

- **Admin Dashboard:** Revenue tracking and business analytics
- **Booking Management:** Approve/reject bookings and update payment status
- **User Management:** View and manage user accounts
- **Venue Administration:** Full venue CRUD operations
- **Reporting:** Statistical data and charts for business insights

### Security Features

- **Password Hashing:** Secure password storage using bcrypt
- **JWT Authentication:** Stateless authentication with token expiration
- **Role-based Access:** Admin and client user roles
- **CORS Protection:** Configured cross-origin resource sharing
- **Input Validation:** Pydantic models for data validation

## Technology Stack

### Web Framework

- **FastAPI:** Modern, high-performance web framework for building APIs with automatic OpenAPI documentation
- **Uvicorn:** ASGI server for production deployment
- **Starlette:** ASGI toolkit providing request/response handling

### Database and ORM

- **PostgreSQL:** Robust relational database for data persistence
- **SQLAlchemy:** Python SQL toolkit and Object-Relational Mapping
- **Alembic:** Database migration tool for schema versioning

### Authentication and Security

- **PassLib:** Password hashing and verification
- **Python-JOSE:** JSON Web Token encoding and decoding
- **Authlib:** OAuth integration for Google authentication

### File Handling

- **Cloudinary:** Cloud-based image storage and optimization
- **Python-Multipart:** File upload handling for FastAPI

### PDF Generation

- **ReportLab:** PDF creation library for invoice generation

### Development Tools

- **Python-Dotenv:** Environment variable management
- **Pydantic:** Data validation and serialization
- **Uvicorn Standard:** Development server with hot reload

## Project Structure

```
├── alembic.ini              # Database migration configuration
├── app.py                   # Main FastAPI application
├── models.py                # SQLAlchemy database models
├── create_db.py             # Database initialization script
├── seed_data.py             # Sample data seeding script
├── start.py                 # Production server entry point
├── run.py                   # Development server script
├── Pipfile                  # Python dependency management
├── Pipfile.lock             # Locked dependency versions
├── migrations/              # Database migration files
│   └── versions/
├── requirements.txt         # Alternative dependency specification
└── README.md               # This file
```

## Database Schema

### Users Table

- User authentication and profile information
- Role-based access control (Admin/Client)
- OAuth provider support

### Venues Table

- Venue details including capacity, pricing, and location
- Image storage with Cloudinary integration
- Category-based organization

### Bookings Table

- Booking records with date ranges and guest counts
- Status tracking (Pending/Approved/Rejected)
- Payment status management
- Contact information storage

### SavedVenues Table

- User-venue relationships for bookmarking
- Unique constraints to prevent duplicates

## API Endpoints

### Authentication

- `POST /token` - Email/password login
- `GET /login/google` - Google OAuth initiation
- `GET /auth/google` - Google OAuth callback

### Users

- `POST /users` - User registration
- `GET /users/me` - Current user information
- `PUT /users/profile` - Profile updates

### Venues

- `POST /venues` - Create venue (Admin)
- `GET /venues` - List venues with filtering
- `GET /venues/{id}` - Venue details
- `PUT /venues/{id}` - Update venue (Admin)
- `DELETE /venues/{id}` - Delete venue (Admin)
- `POST /venues/{id}/save` - Save venue to user list
- `DELETE /venues/{id}/save` - Remove from saved venues
- `GET /venues/saved` - User's saved venues

### Bookings

- `POST /bookings` - Create booking
- `GET /bookings` - List all bookings (Admin)
- `GET /bookings/my-bookings` - User's bookings
- `PUT /bookings/{id}/status` - Update booking status (Admin)
- `GET /bookings/{id}/invoice` - Download PDF invoice

### Administrative

- `GET /admin/reports` - Dashboard statistics
- `GET /admin/bookings` - All bookings management
- `GET /admin/users` - User management
- `GET /admin/venues` - Venue management
- `DELETE /users/{id}` - Delete user (Admin)

### Utility

- `POST /upload` - Image upload to Cloudinary
- `GET /venues/{id}/booked-dates` - Venue availability

## Environment Configuration

Required environment variables:

- `SECRET_KEY` - JWT signing key
- `DATABASE_URL` - PostgreSQL connection string
- `GOOGLE_CLIENT_ID` - Google OAuth client ID
- `GOOGLE_CLIENT_SECRET` - Google OAuth client secret
- `FRONTEND_URL` - Frontend application URL
- `CLOUDINARY_CLOUD_NAME` - Cloudinary cloud name
- `CLOUDINARY_API_KEY` - Cloudinary API key
- `CLOUDINARY_API_SECRET` - Cloudinary API secret
- `MAIL_USERNAME` - SMTP username (optional)
- `MAIL_PASSWORD` - SMTP password (optional)
- `MAIL_FROM` - Sender email address (optional)
- `MAIL_PORT` - SMTP port (optional)
- `MAIL_SERVER` - SMTP server (optional)

## Database Setup

1. Install PostgreSQL and create database
2. Configure DATABASE_URL environment variable
3. Run migrations: `alembic upgrade head`
4. Seed sample data: `python seed_data.py`

## Development Setup

1. Clone the repository
2. Install Python dependencies: `pipenv install` or `pip install -r requirements.txt`
3. Configure environment variables
4. Initialize database: `python create_db.py`
5. Run migrations: `alembic upgrade head`
6. Start development server: `python run.py` or `uvicorn app:app --reload`

## Production Deployment

The application is deployed on Render with:

- **Web Service:** Uvicorn server with Gunicorn
- **Database:** PostgreSQL hosted on Neon
- **File Storage:** Cloudinary for image management
- **SSL/TLS:** Automatic HTTPS provisioning

### Deployment Configuration

- Environment variables configured in Render dashboard
- Automatic database migrations on startup
- Health checks and monitoring enabled

## API Documentation

Interactive API documentation available at `/docs` (Swagger UI) and `/redoc` (ReDoc) when running the application.

## Security Implementation

### Authentication Flow

1. User login with email/password or Google OAuth
2. JWT token generation with expiration
3. Token validation on protected endpoints
4. Role-based access control for admin functions

### Data Protection

- Password hashing with bcrypt
- JWT tokens with secure signing
- HTTPS enforcement in production
- CORS configuration for frontend access

### Input Validation

- Pydantic models for request/response validation
- SQL injection prevention with SQLAlchemy
- File upload restrictions and validation

## Performance Optimizations

- **Database Connection Pooling:** SQLAlchemy connection pooling for efficient database access
- **Async Operations:** FastAPI's async capabilities for concurrent request handling
- **Image Optimization:** Cloudinary automatic image optimization and CDN delivery
- **Caching:** Database connection reuse and prepared statements

## Error Handling

- Comprehensive error responses with appropriate HTTP status codes
- Database transaction management with rollback on errors
- Logging for debugging and monitoring
- Graceful handling of external service failures

## Testing

The application includes comprehensive testing for:

- API endpoint functionality
- Authentication and authorization
- Database operations
- Error handling scenarios

## Monitoring and Logging

- Structured logging with request/response details
- Database query logging in development
- Error tracking and alerting
- Performance monitoring with response times

## Contributing

1. Fork the repository
2. Create a feature branch from main
3. Implement changes with proper testing
4. Ensure all tests pass
5. Submit a pull request with detailed description

## License

This project is proprietary software. All rights reserved.

## Support

For technical issues or questions:

- Check the API documentation at `/docs`
- Review the codebase and comments
- Create an issue in the repository
- Contact the development team through the frontend application
