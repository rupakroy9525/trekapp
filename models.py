from datetime import datetime, date
from flask_login import UserMixin
from werkzeug.security import generate_password_hash, check_password_hash

from extensions import db

# ---------------------------------------------------------------------------
# Role & status constants
# ---------------------------------------------------------------------------
ROLE_ADMIN = "admin"
ROLE_STAFF = "staff"
ROLE_TREKKER = "trekker"

# User.status values
STATUS_PENDING = "Pending"        # staff awaiting admin approval
STATUS_APPROVED = "Approved"      # staff approved by admin
STATUS_ACTIVE = "Active"          # trekker / admin default
STATUS_BLACKLISTED = "Blacklisted"

# Trek.status values
TREK_PENDING = "Pending"
TREK_APPROVED = "Approved"
TREK_OPEN = "Open"
TREK_CLOSED = "Closed"
TREK_COMPLETED = "Completed"

# Booking.status values
BOOKING_BOOKED = "Booked"
BOOKING_CANCELLED = "Cancelled"
BOOKING_COMPLETED = "Completed"

DIFFICULTIES = ["Easy", "Moderate", "Hard"]


class User(UserMixin, db.Model):
    """Single table for Admin, Trek Staff and Trekker (User) accounts."""
    __tablename__ = "users"

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(120), nullable=False)
    email = db.Column(db.String(150), unique=True, nullable=False, index=True)
    phone = db.Column(db.String(20))
    password_hash = db.Column(db.String(255), nullable=False)
    role = db.Column(db.String(20), nullable=False)  # admin / staff / trekker
    status = db.Column(db.String(20), nullable=False, default=STATUS_ACTIVE)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    # Treks this staff member is assigned to
    assigned_treks = db.relationship(
        "Trek", backref="staff", lazy=True, foreign_keys="Trek.assigned_staff_id"
    )
    # Bookings made by this trekker
    bookings = db.relationship(
        "Booking", backref="trekker", lazy=True, foreign_keys="Booking.user_id"
    )

    def set_password(self, raw_password):
        self.password_hash = generate_password_hash(raw_password)

    def check_password(self, raw_password):
        return check_password_hash(self.password_hash, raw_password)

    @property
    def is_admin(self):
        return self.role == ROLE_ADMIN

    @property
    def is_staff(self):
        return self.role == ROLE_STAFF

    @property
    def is_trekker(self):
        return self.role == ROLE_TREKKER

    def __repr__(self):
        return f"<User {self.id} {self.name} ({self.role})>"


class Trek(db.Model):
    __tablename__ = "treks"

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(150), nullable=False)
    location = db.Column(db.String(150), nullable=False)
    difficulty = db.Column(db.String(20), nullable=False, default="Easy")
    duration_days = db.Column(db.Integer, nullable=False, default=1)
    total_slots = db.Column(db.Integer, nullable=False, default=10)
    available_slots = db.Column(db.Integer, nullable=False, default=10)
    assigned_staff_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=True)
    status = db.Column(db.String(20), nullable=False, default=TREK_PENDING)
    start_date = db.Column(db.Date, nullable=True)
    end_date = db.Column(db.Date, nullable=True)
    description = db.Column(db.Text, default="")
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    bookings = db.relationship(
        "Booking", backref="trek", lazy=True, cascade="all, delete-orphan"
    )

    @property
    def active_booking_count(self):
        return sum(1 for b in self.bookings if b.status == BOOKING_BOOKED)

    def __repr__(self):
        return f"<Trek {self.id} {self.name}>"


class Booking(db.Model):
    __tablename__ = "bookings"

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False)
    trek_id = db.Column(db.Integer, db.ForeignKey("treks.id"), nullable=False)
    booking_date = db.Column(db.DateTime, default=datetime.utcnow)
    status = db.Column(db.String(20), nullable=False, default=BOOKING_BOOKED)

    def __repr__(self):
        return f"<Booking {self.id} user={self.user_id} trek={self.trek_id}>"
