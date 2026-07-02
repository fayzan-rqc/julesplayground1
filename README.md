# ParkDirect - Enterprise Parking Privilege & Allocation System

ParkDirect is a web-based, mobile-friendly parking booking system designed to manage 7 on-site parking bays with priority-based allocation for ITSM and QA departments.

## Features

- **Department Priority**: 4 bays weighted to ITSM, 3 to QA.
- **Bumping Logic**: Priority users can "bump" provisional bookings from other departments.
- **PWA Ready**: Installable on mobile devices with offline support via service workers.
- **Admin Portal**: View and manage all bookings from a central dashboard.
- **Neo-Brutalist UI**: High-contrast, bold design for high visibility and ease of use.

## Local Setup Instructions

### Prerequisites

- Python 3.8+
- pip (Python package installer)

### Installation

1. **Install Dependencies**:
   ```bash
   pip install Flask Flask-SQLAlchemy
   ```

2. **Initialize the Database**:
   The database is automatically initialized and seeded with the 7 bays when you first run the application.

### Running the Application

1. **Start the Flask Server**:
   ```bash
   python app.py
   ```
   The application will be available at `http://127.0.0.1:5001`.

### How to Open and Inspect the Database

Since the app uses SQLite, you can easily inspect the database using the command line:

1. **Open the Database**:
   ```bash
   sqlite3 instance/parking.db
   ```

2. **Useful Commands inside SQLite**:
   - `.tables` - List all tables (`bay`, `booking`).
   - `SELECT * FROM bay;` - View all parking slots and their priorities.
   - `SELECT * FROM booking;` - View all current bookings.
   - `.quit` - Exit the SQLite interface.

### How to Use

1. **User Profile**:
   On your first visit, you will be redirected to the **Profile** page. Enter your name and select your department (ITSM or QA).

2. **Booking a Slot**:
   - Go to the **Slots** (Dashboard) page.
   - You must book your department's priority slots first.
   - If your department's slots are full, you can book an available slot from the other department as a **Provisional** booking.
   - **Note**: Provisional bookings can be bumped by users from the priority department at any time.

3. **My Bookings**:
   View your current and historical bookings. You can cancel active bookings for the current day.

4. **Admin Portal**:
   - Access the admin login via the Profile page or navigate directly to `/admin`.
   - The Admin Dashboard allows you to see all active bookings and perform administrative cancellations.

## Project Structure

- `app.py`: Main Flask application and business logic.
- `templates/`: Jinja2 HTML templates.
- `static/`: PWA manifest, service worker, and CSS/JS assets.
- `instance/`: SQLite database storage.

## Business Rules

- **Booking Window**: 06:00 AM – 05:00 PM, Monday – Friday.
- **Daily Reset**: Every bay returns to "Available" at 06:00 AM each day.
- **Fair Minimum Share**: Logic ensures each department has a fair share of capacity while maximizing total utilization.
