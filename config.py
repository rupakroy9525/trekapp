import os

BASE_DIR = os.path.abspath(os.path.dirname(__file__))


class Config:
    SECRET_KEY = "trek-secret-key-change-in-production"
    SQLALCHEMY_DATABASE_URI = "sqlite:///" + os.path.join(BASE_DIR, "trekking.db")
    SQLALCHEMY_TRACK_MODIFICATIONS = False

    # Default admin account (pre-existing superuser, seeded programmatically)
    ADMIN_EMAIL = "admin@trekmanager.com"
    ADMIN_PASSWORD = "Admin@123"
    ADMIN_NAME = "System Admin"
