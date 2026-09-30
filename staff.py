from functools import wraps

from flask import Blueprint, render_template, redirect, url_for, flash, request, abort
from flask_login import login_required, current_user

from extensions import db
from models import Trek, Booking, BOOKING_BOOKED, BOOKING_COMPLETED, TREK_OPEN, TREK_CLOSED, TREK_COMPLETED, TREK_APPROVED

staff_bp = Blueprint("staff", __name__, url_prefix="/staff")


def staff_required(view):
    @wraps(view)
    def wrapped(*args, **kwargs):
        if not current_user.is_authenticated or not current_user.is_staff:
            abort(403)
        return view(*args, **kwargs)
    return wrapped


def _owns_trek_or_404(trek_id):
    trek = Trek.query.get_or_404(trek_id)
    if trek.assigned_staff_id != current_user.id:
        abort(403)
    return trek


@staff_bp.route("/dashboard")
@login_required
@staff_required
def dashboard():
    treks = Trek.query.filter_by(assigned_staff_id=current_user.id).order_by(Trek.created_at.desc()).all()
    trek_stats = [(trek, trek.active_booking_count) for trek in treks]
    return render_template("staff/dashboard.html", trek_stats=trek_stats)


@staff_bp.route("/trek/<int:trek_id>", methods=["GET", "POST"])
@login_required
@staff_required
def trek_detail(trek_id):
    trek = _owns_trek_or_404(trek_id)

    if request.method == "POST":
        new_total = request.form.get("total_slots", type=int)
        new_status = request.form.get("status")

        if new_total is not None:
            booked = trek.total_slots - trek.available_slots
            if new_total < booked:
                flash(f"Cannot set total slots below already-booked count ({booked}).", "danger")
                return redirect(url_for("staff.trek_detail", trek_id=trek.id))
            trek.total_slots = new_total
            trek.available_slots = new_total - booked

        if new_status in (TREK_OPEN, TREK_CLOSED, TREK_COMPLETED):
            trek.status = new_status
            if new_status == TREK_COMPLETED:
                for booking in trek.bookings:
                    if booking.status == BOOKING_BOOKED:
                        booking.status = BOOKING_COMPLETED

        db.session.commit()
        flash("Trek updated.", "success")
        return redirect(url_for("staff.trek_detail", trek_id=trek.id))

    participants = Booking.query.filter_by(trek_id=trek.id, status=BOOKING_BOOKED).all()
    return render_template("staff/trek_detail.html", trek=trek, participants=participants)
