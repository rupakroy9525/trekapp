# Trek Manager — Trekking Management Application

A Flask + Jinja2 + Bootstrap 5 + SQLite web app for managing treks across three roles:
**Admin**, **Trek Staff**, and **Trekker (User)**.

## Tech stack
- **Backend:** Flask, Flask-SQLAlchemy, Flask-Login
- **Frontend:** Jinja2 templates, Bootstrap 5 (CDN), custom CSS (no JS frameworks; Bootstrap's own bundle JS is used only for the responsive navbar toggle — no core feature relies on JavaScript)
- **Database:** SQLite, created programmatically on first run (`db.create_all()` inside `app.py`) — no manual DB Browser steps required

## Setup

```bash
# 1. Create a virtual environment (recommended)
python -m venv venv
source venv/bin/activate      # Windows: venv\Scripts\activate

# 2. Install dependencies
pip install -r requirements.txt

# 3. Run the app
python app.py
```

The app starts at **http://127.0.0.1:5000**. On first run it automatically creates
`trekking.db` and seeds the admin account:

| Role  | Email                     | Password    |
|-------|----------------------------|-------------|
| Admin | admin@trekmanager.com      | Admin@123   |

> To reset the database, stop the server, delete `trekking.db`, and run `python app.py` again.

## Roles & flow

1. **Admin** (pre-seeded, no self-registration) logs in and can:
   - Create / edit / delete treks
   - Approve or blacklist trek staff registrations
   - Assign approved staff to a trek
   - View and search all treks, staff, and trekkers by name/ID
   - Blacklist trekkers or staff
   - View the full booking history across the platform

2. **Trek Staff** self-registers, then waits for admin approval (status: *Pending → Approved*).
   Once approved, they can log in and:
   - View treks assigned to them by the admin
   - Update available slots and trek status (Approved → Open → Closed/Completed)
   - View the list of trekkers registered for each of their treks

3. **Trekker (User)** self-registers and can log in immediately to:
   - Browse and filter **Open** treks by difficulty/location, or search by name
   - Book a trek (blocked once slots are full or the trek isn't Open, and duplicate
     bookings for the same trek are prevented)
   - View booking status and full trekking history
   - Cancel an active booking (frees up a slot)
   - Edit their profile (name, phone, password)

## Core business rules enforced
- Overbooking is prevented — a booking is only accepted while `available_slots > 0`
  and the trek status is `Open`; the slot count is decremented atomically in the
  same request that creates the booking.
- Only the staff member a trek is assigned to can manage that trek (`403` otherwise).
- Trekkers can only book treks with status `Open`.
- Blacklisted users/staff are blocked at login regardless of correct credentials.
- Pending staff accounts cannot log in until approved by the admin.

## Data model (see also ER diagram in the project report)
- **User** (`users`): id, name, email, phone, password_hash, role
  (`admin` / `staff` / `trekker`), status (`Pending` / `Approved` / `Active` / `Blacklisted`), created_at
- **Trek** (`treks`): id, name, location, difficulty, duration_days, total_slots,
  available_slots, assigned_staff_id (FK → users.id), status
  (`Pending`/`Approved`/`Open`/`Closed`/`Completed`), start_date, end_date, description
- **Booking** (`bookings`): id, user_id (FK → users.id), trek_id (FK → treks.id),
  booking_date, status (`Booked`/`Cancelled`/`Completed`)

Relationships: one staff → many treks (assigned); one trekker → many bookings;
one trek → many bookings (many-to-many between trekkers and treks via `Booking`).

## Project structure
```
trekapp/
├── app.py                 # App factory, DB init, admin seeding, error handlers
├── config.py               # Config (SQLite URI, secret key, seed admin creds)
├── extensions.py           # db, login_manager singletons
├── models.py                # User, Trek, Booking models
├── auth.py                  # Login / registration blueprint
├── admin.py                 # Admin blueprint (treks, staff, users, search, bookings)
├── staff.py                  # Trek staff blueprint
├── trekker.py                 # Trekker (user) blueprint
├── requirements.txt
├── static/css/style.css     # Design tokens & theming
└── templates/
    ├── base.html
    ├── auth/                 # login, register_staff, register_trekker
    ├── admin/                # dashboard, treks, trek_form, staff_list, users_list, bookings, search
    ├── staff/                # dashboard, trek_detail
    ├── trekker/               # dashboard, treks, trek_detail, bookings, profile
    ├── errors/                # 403, 404
    └── partials/_badges.html  # shared status/difficulty badge macros
```

## Notes for the project report
- Mention this app was scaffolded/assisted with an AI/LLM per your course's AI declaration policy.
- You'll still want to draw the ER diagram (User / Trek / Booking + relationships above)
  and list the routes above as your "API resource endpoints" if required.
