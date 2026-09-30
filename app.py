from flask import Flask, render_template, redirect, url_for
from flask_login import current_user

from config import Config
from extensions import db, login_manager
from models import User, ROLE_ADMIN, STATUS_ACTIVE

from auth import auth_bp
from admin import admin_bp
from staff import staff_bp
from trekker import trekker_bp


def create_app():
    app = Flask(__name__)
    app.config.from_object(Config)

    db.init_app(app)
    login_manager.init_app(app)

    app.register_blueprint(auth_bp)
    app.register_blueprint(admin_bp)
    app.register_blueprint(staff_bp)
    app.register_blueprint(trekker_bp)

    @login_manager.user_loader
    def load_user(user_id):
        return User.query.get(int(user_id))

    @app.route("/")
    def index():
        if current_user.is_authenticated:
            if current_user.is_admin:
                return redirect(url_for("admin.dashboard"))
            if current_user.is_staff:
                return redirect(url_for("staff.dashboard"))
            return redirect(url_for("trekker.dashboard"))
        return redirect(url_for("auth.login"))

    @app.errorhandler(403)
    def forbidden(e):
        return render_template("errors/403.html"), 403

    @app.errorhandler(404)
    def not_found(e):
        return render_template("errors/404.html"), 404

    with app.app_context():
        db.create_all()
        _seed_admin(app)

    return app


def _seed_admin(app):
    """Create the pre-existing superuser admin account if it doesn't exist yet."""
    existing = User.query.filter_by(role=ROLE_ADMIN).first()
    if existing:
        return
    admin = User(
        name=app.config["ADMIN_NAME"],
        email=app.config["ADMIN_EMAIL"],
        role=ROLE_ADMIN,
        status=STATUS_ACTIVE,
    )
    admin.set_password(app.config["ADMIN_PASSWORD"])
    db.session.add(admin)
    db.session.commit()
    print(f"[seed] Admin account created -> {app.config['ADMIN_EMAIL']} / {app.config['ADMIN_PASSWORD']}")


app = create_app()

if __name__ == "__main__":
    app.run(debug=True, host="0.0.0.0", port=8080)
