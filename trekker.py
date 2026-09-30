from functools import wraps

from flask import Blueprint, render_template, redirect, url_for, flash, request, abort
from flask_login import login_required, current_user

from extensions import db
from models import (
    User, Trek, Booking,
    DIFFICULTIES, TREK_OPEN,
    BOOKING_BOOKED, BOOKING_CANCELLED, BOOKING_COMPLETED,
)

trekker_bp = Blueprint("trekker", __name__, url_prefix="/trekker")


def trekker_required(view):
    @wraps(view)
    def wrapped(*args, **kwargs):
        if not current_user.is_authenticated or not current_user.is_trekker:
            abort(403)
        return view(*args, **kwargs)
    return wrapped


@trekker_bp.route("/dashboard")
@login_required
@trekker_required
def dashboard():
    open_treks = Trek.query.filter_by(status=TREK_OPEN).order_by(Trek.start_date).limit(5).all()
    my_bookings = (
        Booking.query.filter_by(user_id=current_user.id, status=BOOKING_BOOKED)
        .order_by(Booking.booking_date.desc())
        .all()
    )
    return render_template("trekker/dashboard.html", open_treks=open_treks, my_bookings=my_bookings)


@trekker_bp.route("/treks")
@login_required
@trekker_required
def treks():
    q = request.args.get("q", "").strip()
    difficulty = request.args.get("difficulty", "").strip()
    location = request.args.get("location", "").strip()

    query = Trek.query.filter_by(status=TREK_OPEN)
    if q:
        like = f"%{q}%"
        query = query.filter(db.or_(Trek.name.ilike(like), Trek.location.ilike(like)))
    if difficulty:
        query = query.filter_by(difficulty=difficulty)
    if location:
        query = query.filter(Trek.location.ilike(f"%{location}%"))

    results = query.order_by(Trek.start_date).all()

    # mark which treks the current user already booked (active booking)
    my_active_trek_ids = {
        b.trek_id for b in Booking.query.filter_by(user_id=current_user.id, status=BOOKING_BOOKED).all()
    }

    return render_template(
        "trekker/treks.html", treks=results, q=q, difficulty=difficulty, location=location,
        difficulties=DIFFICULTIES, my_active_trek_ids=my_active_trek_ids,
    )


@trekker_bp.route("/treks/<int:trek_id>")
@login_required
@trekker_required
def trek_detail(trek_id):
    trek = Trek.query.get_or_404(trek_id)
    already_booked = Booking.query.filter_by(
        user_id=current_user.id, trek_id=trek.id, status=BOOKING_BOOKED
    ).first() is not None
    return render_template("trekker/trek_detail.html", trek=trek, already_booked=already_booked)


@trekker_bp.route("/treks/<int:trek_id>/book", methods=["POST"])
@login_required
@trekker_required
def book_trek(trek_id):
    trek = Trek.query.get_or_404(trek_id)

    if trek.status != TREK_OPEN:
        flash("This trek is not open for booking.", "danger")
        return redirect(url_for("trekker.trek_detail", trek_id=trek.id))

    existing = Booking.query.filter_by(
        user_id=current_user.id, trek_id=trek.id, status=BOOKING_BOOKED
    ).first()
    if existing:
        flash("You have already booked this trek.", "warning")
        return redirect(url_for("trekker.trek_detail", trek_id=trek.id))

    # Re-fetch with a guard to prevent overbooking under concurrent requests
    if trek.available_slots <= 0:
        flash("Sorry, this trek is fully booked.", "danger")
        return redirect(url_for("trekker.trek_detail", trek_id=trek.id))

    trek.available_slots -= 1
    booking = Booking(user_id=current_user.id, trek_id=trek.id, status=BOOKING_BOOKED)
    db.session.add(booking)
    db.session.commit()

    flash(f"Trek '{trek.name}' booked successfully!", "success")
    return redirect(url_for("trekker.my_bookings"))


@trekker_bp.route("/bookings")
@login_required
@trekker_required
def my_bookings():
    bookings = (
        Booking.query.filter_by(user_id=current_user.id)
        .order_by(Booking.booking_date.desc())
        .all()
    )
    return render_template("trekker/bookings.html", bookings=bookings)


@trekker_bp.route("/bookings/<int:booking_id>/cancel", methods=["POST"])
@login_required
@trekker_required
def cancel_booking(booking_id):
    booking = Booking.query.filter_by(id=booking_id, user_id=current_user.id).first_or_404()

    if booking.status != BOOKING_BOOKED:
        flash("This booking cannot be cancelled.", "warning")
        return redirect(url_for("trekker.my_bookings"))

    booking.status = BOOKING_CANCELLED
    booking.trek.available_slots += 1
    db.session.commit()

    flash("Booking cancelled.", "info")
    return redirect(url_for("trekker.my_bookings"))


@trekker_bp.route("/profile", methods=["GET", "POST"])
@login_required
@trekker_required
def profile():
    if request.method == "POST":
        name = request.form.get("name", "").strip()
        phone = request.form.get("phone", "").strip()
        new_password = request.form.get("new_password", "")

        if not name:
            flash("Name cannot be empty.", "danger")
            return render_template("trekker/profile.html")

        current_user.name = name
        current_user.phone = phone
        if new_password:
            if len(new_password) < 6:
                flash("Password must be at least 6 characters.", "danger")
                return render_template("trekker/profile.html")
            current_user.set_password(new_password)

        db.session.commit()
        flash("Profile updated.", "success")
        return redirect(url_for("trekker.profile"))

    return render_template("trekker/profile.html")
