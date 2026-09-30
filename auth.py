from flask import Blueprint, render_template, redirect, url_for, flash, request
from flask_login import login_user, logout_user, login_required, current_user

from extensions import db
from models import User, ROLE_ADMIN, ROLE_STAFF, ROLE_TREKKER, STATUS_PENDING, STATUS_ACTIVE, STATUS_BLACKLISTED

auth_bp = Blueprint("auth", __name__, url_prefix="/auth")


def _role_home(user):
    if user.role == ROLE_ADMIN:
        return url_for("admin.dashboard")
    if user.role == ROLE_STAFF:
        return url_for("staff.dashboard")
    return url_for("trekker.dashboard")


@auth_bp.route("/login", methods=["GET", "POST"])
def login():
    if current_user.is_authenticated:
        return redirect(_role_home(current_user))

    if request.method == "POST":
        email = request.form.get("email", "").strip().lower()
        password = request.form.get("password", "")

        user = User.query.filter_by(email=email).first()

        if not user or not user.check_password(password):
            flash("Invalid email or password.", "danger")
            return render_template("auth/login.html")

        if user.role == ROLE_STAFF and user.status == STATUS_PENDING:
            flash("Your staff account is awaiting admin approval.", "warning")
            return render_template("auth/login.html")

        if user.status == STATUS_BLACKLISTED:
            flash("Your account has been blacklisted. Contact the admin.", "danger")
            return render_template("auth/login.html")

        login_user(user)
        flash(f"Welcome back, {user.name}!", "success")
        return redirect(_role_home(user))

    return render_template("auth/login.html")


@auth_bp.route("/register/staff", methods=["GET", "POST"])
def register_staff():
    if request.method == "POST":
        name = request.form.get("name", "").strip()
        email = request.form.get("email", "").strip().lower()
        phone = request.form.get("phone", "").strip()
        password = request.form.get("password", "")
        confirm = request.form.get("confirm_password", "")

        error = None
        if not name or not email or not password:
            error = "Name, email and password are required."
        elif password != confirm:
            error = "Passwords do not match."
        elif len(password) < 6:
            error = "Password must be at least 6 characters."
        elif User.query.filter_by(email=email).first():
            error = "An account with this email already exists."

        if error:
            flash(error, "danger")
            return render_template("auth/register_staff.html")

        staff = User(
            name=name, email=email, phone=phone,
            role=ROLE_STAFF, status=STATUS_PENDING
        )
        staff.set_password(password)
        db.session.add(staff)
        db.session.commit()

        flash("Registration submitted! Please wait for admin approval before logging in.", "success")
        return redirect(url_for("auth.login"))

    return render_template("auth/register_staff.html")


@auth_bp.route("/register/trekker", methods=["GET", "POST"])
def register_trekker():
    if request.method == "POST":
        name = request.form.get("name", "").strip()
        email = request.form.get("email", "").strip().lower()
        phone = request.form.get("phone", "").strip()
        password = request.form.get("password", "")
        confirm = request.form.get("confirm_password", "")

        error = None
        if not name or not email or not password:
            error = "Name, email and password are required."
        elif password != confirm:
            error = "Passwords do not match."
        elif len(password) < 6:
            error = "Password must be at least 6 characters."
        elif User.query.filter_by(email=email).first():
            error = "An account with this email already exists."

        if error:
            flash(error, "danger")
            return render_template("auth/register_trekker.html")

        trekker = User(
            name=name, email=email, phone=phone,
            role=ROLE_TREKKER, status=STATUS_ACTIVE
        )
        trekker.set_password(password)
        db.session.add(trekker)
        db.session.commit()

        flash("Registration successful! You can now log in.", "success")
        return redirect(url_for("auth.login"))

    return render_template("auth/register_trekker.html")


@auth_bp.route("/logout")
@login_required
def logout():
    logout_user()
    flash("You have been logged out.", "info")
    return redirect(url_for("auth.login"))
