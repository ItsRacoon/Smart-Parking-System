from flask_sqlalchemy import SQLAlchemy
from datetime import datetime

db = SQLAlchemy()

class ParkingSpace(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    position_x = db.Column(db.Integer, nullable=False)
    position_y = db.Column(db.Integer, nullable=False)
    space_id = db.Column(db.String(10), unique=True, nullable=False)
    bookings = db.relationship('Booking', backref='parking_space', lazy=True)

class Booking(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_name = db.Column(db.String(100), nullable=False)
    user_email = db.Column(db.String(100), nullable=False)
    license_plate = db.Column(db.String(20), nullable=False)
    start_time = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)
    end_time = db.Column(db.DateTime, nullable=False)
    is_active = db.Column(db.Boolean, default=True)
    created_at = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)
    parking_space_id = db.Column(db.Integer, db.ForeignKey('parking_space.id'), nullable=False)

    def __repr__(self):
        return f'<Booking {self.id} for {self.user_name}>'