from datetime import datetime
from functools import wraps

from flask import Blueprint, render_template, redirect, url_for, flash, request, abort
from flask_login import login_required, current_user

from extensions import db
from models import (
    User, Trek, Booking,
    ROLE_ADMIN, ROLE_STAFF, ROLE_TREKKER,
    STATUS_PENDING, STATUS_APPROVED, STATUS_ACTIVE, STATUS_BLACKLISTED,
    TREK_PENDING, TREK_APPROVED, TREK_OPEN, TREK_CLOSED, TREK_COMPLETED,
    DIFFICULTIES,
)

admin_bp = Blueprint("admin", __name__, url_prefix="/admin")


def admin_required(view):
    @wraps(view)
    def wrapped(*args, **kwargs):
        if not current_user.is_authenticated or not current_user.is_admin:
            abort(403)
        return view(*args, **kwargs)
    return wrapped


@admin_bp.route("/dashboard")
@login_required
@admin_required
def dashboard():
    total_treks = Trek.query.count()
    total_users = User.query.filter_by(role=ROLE_TREKKER).count()
    total_staff = User.query.filter_by(role=ROLE_STAFF).count()
    total_bookings = Booking.query.count()
    pending_staff = User.query.filter_by(role=ROLE_STAFF, status=STATUS_PENDING).count()
    recent_treks = Trek.query.order_by(Trek.created_at.desc()).limit(5).all()

    return render_template(
        "admin/dashboard.html",
        total_treks=total_treks,
        total_users=total_users,
        total_staff=total_staff,
        total_bookings=total_bookings,
        pending_staff=pending_staff,
        recent_treks=recent_treks,
    )


# ---------------------------------------------------------------------------
# Trek management
# ---------------------------------------------------------------------------
@admin_bp.route("/treks")
@login_required
@admin_required
def treks():
    q = request.args.get("q", "").strip()
    query = Trek.query
    if q:
        like = f"%{q}%"
        query = query.filter(db.or_(Trek.name.ilike(like), Trek.location.ilike(like)))
    all_treks = query.order_by(Trek.created_at.desc()).all()
    return render_template("admin/treks.html", treks=all_treks, q=q)


@admin_bp.route("/treks/new", methods=["GET", "POST"])
@login_required
@admin_required
def trek_new():
    staff_list = User.query.filter_by(role=ROLE_STAFF, status=STATUS_APPROVED).all()

    if request.method == "POST":
        name = request.form.get("name", "").strip()
        location = request.form.get("location", "").strip()
        difficulty = request.form.get("difficulty", "Easy")
        duration_days = request.form.get("duration_days", type=int) or 1
        total_slots = request.form.get("total_slots", type=int) or 10
        description = request.form.get("description", "").strip()
        start_date_str = request.form.get("start_date", "")
        end_date_str = request.form.get("end_date", "")
        assigned_staff_id = request.form.get("assigned_staff_id", type=int)

        if not name or not location:
            flash("Trek name and location are required.", "danger")
            return render_template("admin/trek_form.html", staff_list=staff_list, trek=None)

        start_date = datetime.strptime(start_date_str, "%Y-%m-%d").date() if start_date_str else None
        end_date = datetime.strptime(end_date_str, "%Y-%m-%d").date() if end_date_str else None

        status = TREK_APPROVED if assigned_staff_id else TREK_PENDING

        trek = Trek(
            name=name, location=location, difficulty=difficulty,
            duration_days=duration_days, total_slots=total_slots,
            available_slots=total_slots, description=description,
            start_date=start_date, end_date=end_date,
            assigned_staff_id=assigned_staff_id or None,
            status=status,
        )
        db.session.add(trek)
        db.session.commit()
        flash(f"Trek '{name}' created.", "success")
        return redirect(url_for("admin.treks"))

    return render_template("admin/trek_form.html", staff_list=staff_list, trek=None)


@admin_bp.route("/treks/<int:trek_id>/edit", methods=["GET", "POST"])
@login_required
@admin_required
def trek_edit(trek_id):
    trek = Trek.query.get_or_404(trek_id)
    staff_list = User.query.filter_by(role=ROLE_STAFF, status=STATUS_APPROVED).all()

    if request.method == "POST":
        trek.name = request.form.get("name", "").strip()
        trek.location = request.form.get("location", "").strip()
        trek.difficulty = request.form.get("difficulty", "Easy")
        trek.duration_days = request.form.get("duration_days", type=int) or 1
        new_total = request.form.get("total_slots", type=int) or trek.total_slots
        description = request.form.get("description", "").strip()
        start_date_str = request.form.get("start_date", "")
        end_date_str = request.form.get("end_date", "")
        assigned_staff_id = request.form.get("assigned_staff_id", type=int)

        # keep available_slots consistent when total_slots changes
        booked = trek.total_slots - trek.available_slots
        trek.total_slots = new_total
        trek.available_slots = max(new_total - booked, 0)

        trek.description = description
        trek.start_date = datetime.strptime(start_date_str, "%Y-%m-%d").date() if start_date_str else None
        trek.end_date = datetime.strptime(end_date_str, "%Y-%m-%d").date() if end_date_str else None
        trek.assigned_staff_id = assigned_staff_id or None

        if trek.assigned_staff_id and trek.status == TREK_PENDING:
            trek.status = TREK_APPROVED

        db.session.commit()
        flash("Trek updated.", "success")
        return redirect(url_for("admin.treks"))

    return render_template("admin/trek_form.html", staff_list=staff_list, trek=trek)


@admin_bp.route("/treks/<int:trek_id>/delete", methods=["POST"])
@login_required
@admin_required
def trek_delete(trek_id):
    trek = Trek.query.get_or_404(trek_id)
    db.session.delete(trek)
    db.session.commit()
    flash("Trek removed.", "info")
    return redirect(url_for("admin.treks"))


# ---------------------------------------------------------------------------
# Staff management
# ---------------------------------------------------------------------------
@admin_bp.route("/staff")
@login_required
@admin_required
def staff_list():
    q = request.args.get("q", "").strip()
    query = User.query.filter_by(role=ROLE_STAFF)
    if q:
        like = f"%{q}%"
        query = query.filter(db.or_(User.name.ilike(like), User.email.ilike(like)))
    staff = query.order_by(User.created_at.desc()).all()
    return render_template("admin/staff_list.html", staff=staff, q=q)


@admin_bp.route("/staff/<int:staff_id>/approve", methods=["POST"])
@login_required
@admin_required
def staff_approve(staff_id):
    staff = User.query.filter_by(id=staff_id, role=ROLE_STAFF).first_or_404()
    staff.status = STATUS_APPROVED
    db.session.commit()
    flash(f"{staff.name} approved as trek staff.", "success")
    return redirect(url_for("admin.staff_list"))


@admin_bp.route("/staff/<int:staff_id>/blacklist", methods=["POST"])
@login_required
@admin_required
def staff_blacklist(staff_id):
    staff = User.query.filter_by(id=staff_id, role=ROLE_STAFF).first_or_404()
    staff.status = STATUS_BLACKLISTED
    db.session.commit()
    flash(f"{staff.name} has been blacklisted.", "warning")
    return redirect(url_for("admin.staff_list"))


@admin_bp.route("/staff/<int:staff_id>/reactivate", methods=["POST"])
@login_required
@admin_required
def staff_reactivate(staff_id):
    staff = User.query.filter_by(id=staff_id, role=ROLE_STAFF).first_or_404()
    staff.status = STATUS_APPROVED
    db.session.commit()
    flash(f"{staff.name} has been reactivated.", "success")
    return redirect(url_for("admin.staff_list"))


# ---------------------------------------------------------------------------
# Trekker (user) management
# ---------------------------------------------------------------------------
@admin_bp.route("/users")
@login_required
@admin_required
def users_list():
    q = request.args.get("q", "").strip()
    query = User.query.filter_by(role=ROLE_TREKKER)
    if q:
        like = f"%{q}%"
        query = query.filter(db.or_(User.name.ilike(like), User.email.ilike(like)))
    users = query.order_by(User.created_at.desc()).all()
    return render_template("admin/users_list.html", users=users, q=q)


@admin_bp.route("/users/<int:user_id>/blacklist", methods=["POST"])
@login_required
@admin_required
def user_blacklist(user_id):
    user = User.query.filter_by(id=user_id, role=ROLE_TREKKER).first_or_404()
    user.status = STATUS_BLACKLISTED
    db.session.commit()
    flash(f"{user.name} has been blacklisted.", "warning")
    return redirect(url_for("admin.users_list"))


@admin_bp.route("/users/<int:user_id>/reactivate", methods=["POST"])
@login_required
@admin_required
def user_reactivate(user_id):
    user = User.query.filter_by(id=user_id, role=ROLE_TREKKER).first_or_404()
    user.status = STATUS_ACTIVE
    db.session.commit()
    flash(f"{user.name} has been reactivated.", "success")
    return redirect(url_for("admin.users_list"))


# ---------------------------------------------------------------------------
# Bookings overview
# ---------------------------------------------------------------------------
@admin_bp.route("/bookings")
@login_required
@admin_required
def bookings():
    all_bookings = Booking.query.order_by(Booking.booking_date.desc()).all()
    return render_template("admin/bookings.html", bookings=all_bookings)


# ---------------------------------------------------------------------------
# Global search (treks, staff, users)
# ---------------------------------------------------------------------------
@admin_bp.route("/search")
@login_required
@admin_required
def search():
    q = request.args.get("q", "").strip()
    trek_results, staff_results, user_results = [], [], []

    if q:
        like = f"%{q}%"
        id_match = q.isdigit()

        trek_query = Trek.query.filter(db.or_(Trek.name.ilike(like), Trek.location.ilike(like)))
        if id_match:
            trek_query = Trek.query.filter(db.or_(Trek.name.ilike(like), Trek.location.ilike(like), Trek.id == int(q)))
        trek_results = trek_query.all()

        staff_query = User.query.filter_by(role=ROLE_STAFF).filter(
            db.or_(User.name.ilike(like), User.email.ilike(like))
        )
        if id_match:
            staff_query = User.query.filter_by(role=ROLE_STAFF).filter(
                db.or_(User.name.ilike(like), User.email.ilike(like), User.id == int(q))
            )
        staff_results = staff_query.all()

        user_query = User.query.filter_by(role=ROLE_TREKKER).filter(
            db.or_(User.name.ilike(like), User.email.ilike(like))
        )
        if id_match:
            user_query = User.query.filter_by(role=ROLE_TREKKER).filter(
                db.or_(User.name.ilike(like), User.email.ilike(like), User.id == int(q))
            )
        user_results = user_query.all()

    return render_template(
        "admin/search.html", q=q,
        trek_results=trek_results, staff_results=staff_results, user_results=user_results
    )
