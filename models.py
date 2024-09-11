from flask_sqlalchemy import SQLAlchemy
from werkzeug.security import generate_password_hash, check_password_hash

db = SQLAlchemy()

class User(db.Model):
    __tablename__ = 'users'

    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(50), nullable=False, unique=True)
    email = db.Column(db.String(100), nullable=False, unique=True)
    password_hash = db.Column(db.String(255), nullable=False)

    def set_password(self, password):
        """Hash the password and set it."""
        self.password_hash = generate_password_hash(password)

    def check_password(self, password):
        """Check if the provided password matches the stored hash."""
        return check_password_hash(self.password_hash, password)

    # Define the signup method
    @classmethod
    def signup(cls, username, email, password):
        """Sign up a user with a hashed password."""
        user = cls(username=username, email=email)
        user.set_password(password)  # Hashes the password
        db.session.add(user)
        db.session.commit()
        return user

    @classmethod
    def authenticate(cls, username, password):
        """Find user with `username` and check if `password` is correct."""
        user = cls.query.filter_by(username=username).first()
        if user and user.check_password(password):  # Use user.check_password
            return user
        return False

class Favorite(db.Model):
    __tablename__ = 'favorites'

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id', ondelete='CASCADE'), nullable=False)
    news_title = db.Column(db.String(255), nullable=False)
    news_link = db.Column(db.String(500), nullable=False)
    publish_date = db.Column(db.DateTime, nullable=False)
    description = db.Column(db.String, nullable=True)

    user = db.relationship('User', backref=db.backref('favorites', lazy=True))

def connect_db(app):
    """Connect this database to provided Flask app."""
    db.app = app
    db.init_app(app)

