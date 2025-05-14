from flask_sqlalchemy import SQLAlchemy
from datetime import datetime
import uuid

db = SQLAlchemy()

class User(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(50), unique=True, nullable=False)
    email = db.Column(db.String(100), unique=True, nullable=False)
    password_hash = db.Column(db.String(128), nullable=False)
    first_name = db.Column(db.String(50))
    last_name = db.Column(db.String(50))
    phone = db.Column(db.String(20))
    is_admin = db.Column(db.Boolean, default=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    bookings = db.relationship('Booking', backref='user', lazy=True)
    vehicles = db.relationship('Vehicle', backref='owner', lazy=True)
    
    def __repr__(self):
        return f'<User {self.username}>'

class Vehicle(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    license_plate = db.Column(db.String(20), nullable=False)
    make = db.Column(db.String(50))
    model = db.Column(db.String(50))
    color = db.Column(db.String(30))
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    bookings = db.relationship('Booking', backref='vehicle', lazy=True)
    
    def __repr__(self):
        return f'<Vehicle {self.license_plate}>'

class ParkingSpace(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    position_x = db.Column(db.Integer, nullable=False)
    position_y = db.Column(db.Integer, nullable=False)
    space_id = db.Column(db.String(10), unique=True, nullable=False)
    zone = db.Column(db.String(20), default='General')  # e.g., 'VIP', 'Disabled', 'General'
    hourly_rate = db.Column(db.Float, default=150.00)  # Default hourly rate in INR (equivalent to ~$2.00)
    is_active = db.Column(db.Boolean, default=True)
    bookings = db.relationship('Booking', backref='parking_space', lazy=True)
    
    def __repr__(self):
        return f'<ParkingSpace {self.space_id}>'

class Booking(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    booking_reference = db.Column(db.String(10), unique=True, nullable=False)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=True)  # Can be null for guest bookings
    user_name = db.Column(db.String(100), nullable=False)
    user_email = db.Column(db.String(100), nullable=False)
    vehicle_id = db.Column(db.Integer, db.ForeignKey('vehicle.id'), nullable=True)
    license_plate = db.Column(db.String(20), nullable=False)
    start_time = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)
    end_time = db.Column(db.DateTime, nullable=False)
    is_active = db.Column(db.Boolean, default=True)
    created_at = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)
    parking_space_id = db.Column(db.Integer, db.ForeignKey('parking_space.id'), nullable=False)
    total_price = db.Column(db.Float, nullable=False)
    payment_status = db.Column(db.String(20), default='Pending')  # 'Pending', 'Paid', 'Refunded'
    check_in_time = db.Column(db.DateTime, nullable=True)
    check_out_time = db.Column(db.DateTime, nullable=True)
    selection_method = db.Column(db.String(20), default='Manual')  # 'Auto' or 'Manual'
    
    def __repr__(self):
        return f'<Booking {self.booking_reference} for {self.user_name}>'
    
    @staticmethod
    def generate_reference():
        """Generate a unique booking reference"""
        return str(uuid.uuid4())[:8].upper()

class Payment(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    booking_id = db.Column(db.Integer, db.ForeignKey('booking.id'), nullable=False)
    amount = db.Column(db.Float, nullable=False)
    payment_method = db.Column(db.String(50), nullable=False)  # 'Razorpay', 'Credit Card', 'PayPal', etc.
    transaction_id = db.Column(db.String(100), nullable=True)  # Razorpay order ID
    payment_id = db.Column(db.String(100), nullable=True)  # Razorpay payment ID
    status = db.Column(db.String(20), default='Pending')  # 'Pending', 'Completed', 'Failed', 'Refunded'
    payment_date = db.Column(db.DateTime, nullable=True)  # When payment was completed
    currency = db.Column(db.String(3), default='INR')
    payment_data = db.Column(db.Text, nullable=True)  # JSON data from payment gateway
    booking = db.relationship('Booking', backref='payments')
    
    def __repr__(self):
        return f'<Payment {self.id} for Booking {self.booking_id}>'

class ParkingEvent(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    parking_space_id = db.Column(db.Integer, db.ForeignKey('parking_space.id'), nullable=False)
    booking_id = db.Column(db.Integer, db.ForeignKey('booking.id'), nullable=True)
    event_type = db.Column(db.String(20), nullable=False)  # 'Entry', 'Exit', 'Violation'
    license_plate = db.Column(db.String(20), nullable=True)
    timestamp = db.Column(db.DateTime, default=datetime.utcnow)
    image_path = db.Column(db.String(255), nullable=True)  # Path to captured image
    notes = db.Column(db.Text, nullable=True)
    
    def __repr__(self):
        return f'<ParkingEvent {self.id} - {self.event_type}>'