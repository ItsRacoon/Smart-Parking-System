from flask import Flask, render_template, Response, request, redirect, url_for, jsonify, flash, session
from datetime import datetime
import cv2
import pickle
import cvzone
import numpy as np
import os
from datetime import datetime, timedelta
from dotenv import load_dotenv
# Import database and models
from models import db
from models import ParkingSpace
from models import Booking
from models import User
from models import Vehicle
from models import Payment
from models import ParkingEvent
from werkzeug.security import generate_password_hash, check_password_hash
import uuid

# Load environment variables from .env file
load_dotenv()

app = Flask(__name__)

# Import mail service (must be after app is created)
from mail_service import init_mail

# Define now() function for templates
@app.template_filter('now')
def now():
    """Return current datetime for use in templates"""
    return datetime.now()
app.config['SECRET_KEY'] = os.urandom(24)
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///parking.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
app.config['UPLOAD_FOLDER'] = 'static/uploads'

# Update database schema if needed
try:
    from update_db import update_payment_table
    with app.app_context():
        update_payment_table()
except Exception as e:
    print(f"Warning: Could not update database schema: {str(e)}")
app.config['MAX_CONTENT_LENGTH'] = 16 * 1024 * 1024  # 16MB max upload

# Add custom Jinja2 extensions
from datetime import datetime
app.jinja_env.globals.update(now=datetime.now)

# Add view_functions to Jinja2 environment
@app.context_processor
def inject_view_functions():
    return dict(view_functions=app.view_functions)

# Ensure upload directory exists
os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)

# Initialize database
db.init_app(app)

# Initialize mail service
init_mail(app)

# Custom template filters
@app.template_filter('format_date')
def format_date(value, format='%Y-%m-%d'):
    """Format a date using a specified format."""
    if value is None:
        return ""
    return value.strftime(format)

@app.template_filter('format_datetime')
def format_datetime(value, format='%Y-%m-%d %H:%M'):
    """Format a datetime using a specified format."""
    if value is None:
        return ""
    return value.strftime(format)

@app.template_filter('currency')
def currency_format(value):
    """Format a number as currency in Indian Rupees (INR)."""
    if value is None:
        return "₹0.00"
    # Convert USD to INR (approximate exchange rate: 1 USD = 75 INR)
    inr_value = float(value) * 75
    return "₹{:,.2f}".format(inr_value)

@app.template_filter('time_ago')
def time_ago(value):
    """Format a datetime as a relative time."""
    if value is None:
        return ""
    
    now = datetime.now()
    diff = now - value
    
    seconds = diff.total_seconds()
    if seconds < 60:
        return "just now"
    elif seconds < 3600:
        minutes = int(seconds / 60)
        return f"{minutes} minute{'s' if minutes > 1 else ''} ago"
    elif seconds < 86400:
        hours = int(seconds / 3600)
        return f"{hours} hour{'s' if hours > 1 else ''} ago"
    elif seconds < 604800:
        days = int(seconds / 86400)
        return f"{days} day{'s' if days > 1 else ''} ago"
    else:
        return value.strftime('%Y-%m-%d')

# Register blueprints
try:
    from auth import auth
    app.register_blueprint(auth, url_prefix='/auth')
except ImportError:
    print("Warning: Could not import auth blueprint")

# Register payment blueprint
try:
    from payment import payment
    app.register_blueprint(payment, url_prefix='/payment')
except ImportError:
    print("Warning: Could not import payment blueprint")

# Function to check for expired bookings
def check_expired_bookings():
    """Check for expired bookings and mark them as inactive"""
    with app.app_context():
        current_time = datetime.now()
        expired_bookings = Booking.query.filter(
            Booking.is_active == True,
            Booking.end_time < current_time
        ).all()
        
        if expired_bookings:
            for booking in expired_bookings:
                booking.is_active = False
                db.session.add(booking)
            
            db.session.commit()
            print(f"[{current_time}] Marked {len(expired_bookings)} expired bookings as inactive")

# Create a background thread to check for expired bookings every minute
import threading
import time

def booking_expiration_checker():
    """Background thread to check for expired bookings"""
    while True:
        check_expired_bookings()
        time.sleep(60)  # Check every minute

# Start the background thread
expiration_thread = threading.Thread(target=booking_expiration_checker, daemon=True)
expiration_thread.start()

# Create database tables
with app.app_context():
    db.create_all()
    
    # Initialize parking spaces from CarParkPos if not already in database
    spaces_count = ParkingSpace.query.count()
    if spaces_count == 0:
        try:
            with open('carParkPos', 'rb') as f:
                posList = pickle.load(f)
            
            # Create different zones with different rates (in INR)
            zones = ['General', 'Premium', 'VIP', 'Disabled']
            rates = [150.00, 250.00, 350.00, 100.00]  # Hourly rates in INR
            
            for i, pos in enumerate(posList):
                x, y = pos
                # Assign zones in a pattern
                zone_index = i % len(zones)
                space = ParkingSpace(
                    position_x=x, 
                    position_y=y, 
                    space_id=f'P{i+1:03d}',
                    zone=zones[zone_index],
                    hourly_rate=rates[zone_index]
                )
                db.session.add(space)
            
            db.session.commit()
            print(f"Initialized {len(posList)} parking spaces")
        except Exception as e:
            print(f"Error initializing parking spaces: {str(e)}")
    
    # Create admin user if no users exist
    if User.query.count() == 0:
        admin = User(
            username='admin',
            email='admin@smartparking.com',
            password_hash=generate_password_hash('admin123'),
            first_name='System',
            last_name='Administrator',
            is_admin=True
        )
        db.session.add(admin)
        db.session.commit()
        print("Created admin user")

# Initialize video capture
try:
    cap = cv2.VideoCapture('carPark.mp4')
    with open('carParkPos', 'rb') as f:
        posList = pickle.load(f)
except Exception as e:
    print(f"Error initializing video: {str(e)}")
    # Fallback to empty list if file doesn't exist
    posList = []

width, height = 107, 48

# Dictionary to store space status
space_status = {}

def checkParkingSpace(imgPro, img):
    spaceCounter = 0
    free_spaces = []
    
    # Get all active bookings and check for expired bookings
    with app.app_context():
        # Get current time
        current_time = datetime.now()
        
        # Check for expired bookings and mark them as inactive
        expired_bookings = Booking.query.filter(
            Booking.is_active == True,
            Booking.end_time < current_time
        ).all()
        
        # Mark expired bookings as inactive
        for booking in expired_bookings:
            booking.is_active = False
            db.session.add(booking)
        
        if expired_bookings:
            db.session.commit()
            print(f"Marked {len(expired_bookings)} expired bookings as inactive")
        
        # Get updated active bookings (only consider paid bookings as active)
        active_bookings = Booking.query.filter_by(is_active=True, payment_status='Paid').all()
        booked_spaces = [booking.parking_space_id for booking in active_bookings]
        all_spaces = ParkingSpace.query.all()
        space_mapping = {(space.position_x, space.position_y): space.id for space in all_spaces}
        space_info = {space.id: space for space in all_spaces}
    
    for i, pos in enumerate(posList):
        x, y = pos
        imgCrop = imgPro[y:y + height, x:x + width]
        count = cv2.countNonZero(imgCrop)
        
        # Check if space is physically empty (by computer vision)
        is_empty = count < 900
        
        # Check if space is booked
        space_id = space_mapping.get((x, y))
        is_booked = space_id in booked_spaces
        
        # Get space details
        space_details = space_info.get(space_id, None)
        zone = space_details.zone if space_details else 'Unknown'
        hourly_rate = space_details.hourly_rate if space_details else 0.0
        
        # Update space status
        space_status[i] = {
            'id': space_id,
            'position': (x, y),
            'is_empty': is_empty,
            'is_booked': is_booked,
            'is_available': is_empty and not is_booked,
            'zone': zone,
            'hourly_rate': hourly_rate
        }
        
        if is_empty and not is_booked:
            color = (0, 255, 0)  # Green for available
            thickness = 5
            spaceCounter += 1
            free_spaces.append(i)
        elif is_empty and is_booked:
            color = (255, 0, 0)  # Blue for booked but empty (BGR format in OpenCV)
            thickness = 5
        else:
            color = (0, 0, 255)  # Red for occupied
            thickness = 2
            
        cv2.rectangle(img, pos, (pos[0] + width, pos[1] + height), color, thickness)
        
        # Get space ID from database
        space_label = f"P{i+1:03d}"
        if is_booked:
            space_label += " (Booked)"
            
        cvzone.putTextRect(img, space_label, (x, y + height - 3), scale=1, thickness=2, offset=0, colorR=color)
    
    cvzone.putTextRect(img, f'Free: {spaceCounter}/{len(posList)}', (100, 50), scale=3, thickness=5, offset=20, colorR=(0, 200, 0))
    return free_spaces

def generate_frames():
    while True:
        success, img = cap.read()
        if not success:
            cap.set(cv2.CAP_PROP_POS_FRAMES, 0)
            continue
        imgGray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
        imgBlur = cv2.GaussianBlur(imgGray, (3, 3), 1)
        imgThreshold = cv2.adaptiveThreshold(imgBlur, 255, cv2.ADAPTIVE_THRESH_GAUSSIAN_C,
                                             cv2.THRESH_BINARY_INV, 25, 16)
        imgMedian = cv2.medianBlur(imgThreshold, 5)
        kernel = np.ones((3, 3), np.uint8)
        imgDilate = cv2.dilate(imgMedian, kernel, iterations=1)

        checkParkingSpace(imgDilate, img)

        _, buffer = cv2.imencode('.jpg', img)
        frame = buffer.tobytes()
        yield (b'--frame\r\n'
               b'Content-Type: image/jpeg\r\n\r\n' + frame + b'\r\n')

@app.route('/register', methods=['GET', 'POST'])
def register():
    """Handle user registration"""
    if request.method == 'POST':
        username = request.form.get('username')
        email = request.form.get('email')
        password = request.form.get('password')
        confirm_password = request.form.get('confirm_password')
        first_name = request.form.get('first_name')
        last_name = request.form.get('last_name')
        phone = request.form.get('phone')
        
        # Validate input
        if not all([username, email, password, confirm_password, first_name, last_name, phone]):
            flash('All fields are required', 'danger')
            return redirect(url_for('register'))
        
        if password != confirm_password:
            flash('Passwords do not match', 'danger')
            return redirect(url_for('register'))
        
        # Check if username or email already exists
        existing_user = User.query.filter((User.username == username) | (User.email == email)).first()
        if existing_user:
            flash('Username or email already exists', 'danger')
            return redirect(url_for('register'))
        
        # Create new user
        new_user = User(
            username=username,
            email=email,
            password_hash=generate_password_hash(password),
            first_name=first_name,
            last_name=last_name,
            phone=phone,
            is_admin=False
        )
        
        db.session.add(new_user)
        db.session.commit()
        
        # Log in the new user
        session['user_id'] = new_user.id
        session['username'] = new_user.username
        session['is_admin'] = new_user.is_admin
        
        flash('Registration successful! You are now logged in.', 'success')
        return redirect(url_for('index'))
    
    return render_template('register.html')

@app.route('/login', methods=['GET', 'POST'])
def login():
    """Handle user login"""
    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')
        
        # For demo purposes, use hardcoded admin credentials
        if username == 'admin' and password == 'admin123':
            session['user_id'] = 1
            session['username'] = username
            session['is_admin'] = True
            flash('Login successful!', 'success')
            return redirect(url_for('admin_dashboard'))
        
        # Check database for user
        user = User.query.filter_by(username=username).first()
        if user and check_password_hash(user.password_hash, password):
            session['user_id'] = user.id
            session['username'] = user.username
            session['is_admin'] = user.is_admin
            flash('Login successful!', 'success')
            if user.is_admin:
                return redirect(url_for('admin_dashboard'))
            else:
                return redirect(url_for('index'))
        
        flash('Invalid username or password', 'danger')
        return redirect(url_for('login'))
    
    return render_template('login.html')

@app.route('/logout')
def logout():
    """Handle user logout"""
    session.clear()
    flash('You have been logged out', 'info')
    return redirect(url_for('index'))

@app.route('/profile')
def profile():
    """User profile page"""
    if 'user_id' not in session:
        flash('Please login to view your profile', 'warning')
        return redirect(url_for('login'))
    
    user = User.query.get(session['user_id'])
    if not user:
        flash('User not found', 'danger')
        return redirect(url_for('index'))
    
    vehicles = Vehicle.query.filter_by(user_id=user.id).all()
    
    return render_template('profile.html', user=user, vehicles=vehicles)

@app.route('/profile/update', methods=['POST'])
def update_profile():
    """Update user profile information"""
    if 'user_id' not in session:
        flash('Please login to update your profile', 'warning')
        return redirect(url_for('login'))
    
    user = User.query.get(session['user_id'])
    if not user:
        flash('User not found', 'danger')
        return redirect(url_for('index'))
    
    # Update user information
    user.first_name = request.form.get('first_name')
    user.last_name = request.form.get('last_name')
    user.email = request.form.get('email')
    user.phone = request.form.get('phone')
    
    db.session.commit()
    flash('Profile updated successfully', 'success')
    return redirect(url_for('profile'))

@app.route('/profile/password', methods=['POST'])
def change_password():
    """Change user password"""
    if 'user_id' not in session:
        flash('Please login to change your password', 'warning')
        return redirect(url_for('login'))
    
    user = User.query.get(session['user_id'])
    if not user:
        flash('User not found', 'danger')
        return redirect(url_for('index'))
    
    current_password = request.form.get('current_password')
    new_password = request.form.get('new_password')
    confirm_password = request.form.get('confirm_password')
    
    # Validate input
    if not all([current_password, new_password, confirm_password]):
        flash('All fields are required', 'danger')
        return redirect(url_for('profile'))
    
    if new_password != confirm_password:
        flash('New passwords do not match', 'danger')
        return redirect(url_for('profile'))
    
    # Check current password
    if not check_password_hash(user.password_hash, current_password):
        flash('Current password is incorrect', 'danger')
        return redirect(url_for('profile'))
    
    # Update password
    user.password_hash = generate_password_hash(new_password)
    db.session.commit()
    
    flash('Password changed successfully', 'success')
    return redirect(url_for('profile'))

@app.route('/vehicles/add', methods=['POST'])
def add_vehicle():
    """Add a new vehicle to user account"""
    if 'user_id' not in session:
        flash('Please login to add a vehicle', 'warning')
        return redirect(url_for('login'))
    
    license_plate = request.form.get('license_plate')
    make = request.form.get('make')
    model = request.form.get('model')
    color = request.form.get('color')
    
    # Validate input
    if not all([license_plate, make, model, color]):
        flash('All fields are required', 'danger')
        return redirect(url_for('profile'))
    
    # Check if vehicle already exists
    existing_vehicle = Vehicle.query.filter_by(user_id=session['user_id'], license_plate=license_plate).first()
    if existing_vehicle:
        flash('A vehicle with this license plate already exists in your account', 'danger')
        return redirect(url_for('profile'))
    
    # Create new vehicle
    new_vehicle = Vehicle(
        license_plate=license_plate,
        make=make,
        model=model,
        color=color,
        user_id=session['user_id']
    )
    
    db.session.add(new_vehicle)
    db.session.commit()
    
    flash('Vehicle added successfully', 'success')
    return redirect(url_for('profile'))

@app.route('/vehicles/<int:vehicle_id>/edit', methods=['POST'])
def edit_vehicle(vehicle_id):
    """Edit an existing vehicle"""
    if 'user_id' not in session:
        flash('Please login to edit a vehicle', 'warning')
        return redirect(url_for('login'))
    
    vehicle = Vehicle.query.get_or_404(vehicle_id)
    
    # Check if user owns this vehicle
    if vehicle.user_id != session['user_id']:
        flash('You do not have permission to edit this vehicle', 'danger')
        return redirect(url_for('profile'))
    
    license_plate = request.form.get('license_plate')
    make = request.form.get('make')
    model = request.form.get('model')
    color = request.form.get('color')
    
    # Validate input
    if not all([license_plate, make, model, color]):
        flash('All fields are required', 'danger')
        return redirect(url_for('profile'))
    
    # Update vehicle
    vehicle.license_plate = license_plate
    vehicle.make = make
    vehicle.model = model
    vehicle.color = color
    
    db.session.commit()
    
    flash('Vehicle updated successfully', 'success')
    return redirect(url_for('profile'))

@app.route('/vehicles/<int:vehicle_id>/delete', methods=['POST'])
def delete_vehicle(vehicle_id):
    """Delete a vehicle"""
    if 'user_id' not in session:
        flash('Please login to delete a vehicle', 'warning')
        return redirect(url_for('login'))
    
    vehicle = Vehicle.query.get_or_404(vehicle_id)
    
    # Check if user owns this vehicle
    if vehicle.user_id != session['user_id']:
        flash('You do not have permission to delete this vehicle', 'danger')
        return redirect(url_for('profile'))
    
    # Check if vehicle is used in any active bookings
    active_bookings = Booking.query.filter_by(vehicle_id=vehicle.id, is_active=True).first()
    if active_bookings:
        flash('This vehicle cannot be deleted as it has active bookings', 'danger')
        return redirect(url_for('profile'))
    
    db.session.delete(vehicle)
    db.session.commit()
    
    flash('Vehicle deleted successfully', 'success')
    return redirect(url_for('profile'))

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/video_feed')
def video_feed():
    return Response(generate_frames(), mimetype='multipart/x-mixed-replace; boundary=frame')

@app.route('/spaces')
def get_spaces():
    """Return JSON data about parking spaces"""
    return jsonify(space_status)

@app.route('/book', methods=['GET', 'POST'])
def book_space():
    # Get user information if logged in
    user = None
    user_vehicles = []
    if 'user_id' in session:
        user = User.query.get(session['user_id'])
        if user:
            user_vehicles = Vehicle.query.filter_by(user_id=user.id).all()
    
    if request.method == 'POST':
        selection_mode = request.form.get('selection_mode', 'manual')
        user_name = request.form.get('user_name')
        user_email = request.form.get('user_email')
        license_plate = request.form.get('license_plate')
        duration_hours = int(request.form.get('duration', 1))
        
        # Check if adding a new vehicle
        new_license_plate = request.form.get('new_license_plate')
        if license_plate == 'new' and new_license_plate:
            license_plate = new_license_plate
            
            # Add the new vehicle to the user's account if logged in
            if user:
                vehicle_make = request.form.get('vehicle_make')
                vehicle_model = request.form.get('vehicle_model')
                vehicle_color = request.form.get('vehicle_color')
                
                new_vehicle = Vehicle(
                    license_plate=license_plate,
                    make=vehicle_make,
                    model=vehicle_model,
                    color=vehicle_color,
                    user_id=user.id
                )
                db.session.add(new_vehicle)
                db.session.commit()
                flash(f'New vehicle {license_plate} added to your account', 'success')
        
        # Validate input
        if not all([user_name, user_email, license_plate]):
            flash('Name, email, and license plate are required', 'danger')
            return redirect(url_for('book_space'))
        
        # Handle space selection based on mode
        if selection_mode == 'auto':
            # Automatically select the best available space
            available_spaces = []
            for idx, status in space_status.items():
                if status.get('is_available', False):
                    space_id = status['id']
                    zone = status.get('zone', 'General')
                    hourly_rate = status.get('hourly_rate', 150.00)  # Default rate in INR
                    available_spaces.append({
                        'id': space_id,
                        'zone': zone,
                        'hourly_rate': hourly_rate
                    })
            
            if not available_spaces:
                flash('No parking spaces are currently available', 'danger')
                return redirect(url_for('book_space'))
            
            # Sort spaces by preference (you can customize this logic)
            # Here we're prioritizing General spaces with lower rates
            available_spaces.sort(key=lambda x: (x['zone'] != 'General', x['hourly_rate']))
            
            # Select the first available space
            space_id = available_spaces[0]['id']
        else:
            # Manual selection
            space_id = request.form.get('space_id')
            if not space_id:
                flash('Please select a parking space', 'danger')
                return redirect(url_for('book_space'))
        
        # Check if space exists and is available
        space = ParkingSpace.query.get(space_id)
        if not space:
            flash('Invalid parking space selected', 'danger')
            return redirect(url_for('book_space'))
            
        # Check if space is already booked
        active_booking = Booking.query.filter_by(parking_space_id=space_id, is_active=True).first()
        if active_booking:
            flash('This space is already booked', 'danger')
            return redirect(url_for('book_space'))
            
        # Create booking
        start_time = datetime.now()
        end_time = start_time + timedelta(hours=duration_hours)
        
        # Calculate price
        total_price = space.hourly_rate * duration_hours
        
        # Check if user is logged in
        user_id = session.get('user_id')
        vehicle_id = None
        
        if user_id:
            # Check if the vehicle exists for this user
            vehicle = Vehicle.query.filter_by(user_id=user_id, license_plate=license_plate).first()
            if vehicle:
                vehicle_id = vehicle.id
        
        # Generate booking reference
        booking_reference = Booking.generate_reference()
        
        booking = Booking(
            booking_reference=booking_reference,
            user_id=user_id,
            user_name=user_name,
            user_email=user_email,
            vehicle_id=vehicle_id,
            license_plate=license_plate,
            start_time=start_time,
            end_time=end_time,
            parking_space_id=space_id,
            total_price=total_price,
            payment_status='Pending',
            selection_method='Auto' if selection_mode == 'auto' else 'Manual'
        )
        
        # Booking is not active until payment is completed
        booking.is_active = False
        
        db.session.add(booking)
        db.session.commit()
        
        # Redirect directly to payment page
        return redirect(url_for('payment.checkout', booking_id=booking.id))
        
    # GET request - show booking form with available spaces
    spaces = []
    for idx, status in space_status.items():
        if status.get('is_available', False):
            spaces.append({
                'id': status['id'],
                'label': f"P{idx+1:03d}",
                'zone': status.get('zone', 'General'),
                'hourly_rate': status.get('hourly_rate', 150.00)  # Default rate in INR
            })
    
    # Get user information if logged in
    user = None
    user_vehicles = []
    if 'user_id' in session:
        user = User.query.get(session['user_id'])
        if user:
            user_vehicles = Vehicle.query.filter_by(user_id=user.id).all()
    
    return render_template('booking.html', spaces=spaces, user=user, user_vehicles=user_vehicles)

@app.route('/bookings')
def view_bookings():
    """View all active bookings"""
    # Get current time
    current_time = datetime.now()
    
    # If user is logged in, show only their bookings
    if 'user_id' in session:
        # Get active bookings
        active_bookings = Booking.query.filter_by(
            user_id=session['user_id'], 
            is_active=True
        ).all()
        
        # Get recently expired bookings (within the last 24 hours)
        expired_time = current_time - timedelta(hours=24)
        expired_bookings = Booking.query.filter(
            Booking.user_id == session['user_id'],
            Booking.is_active == True,
            Booking.end_time < current_time,
            Booking.end_time > expired_time
        ).all()
        
        # Combine both lists
        bookings = active_bookings + expired_bookings
    else:
        # For demo purposes, show all bookings if not logged in
        bookings = Booking.query.filter_by(is_active=True).all()
    
    return render_template('bookings.html', bookings=bookings)

@app.route('/booking/<string:reference>')
def booking_details(reference):
    """View details of a specific booking"""
    booking = Booking.query.filter_by(booking_reference=reference).first_or_404()
    
    # Check if user has permission to view this booking
    if 'user_id' in session and booking.user_id and booking.user_id != session['user_id']:
        if not session.get('is_admin', False):
            flash('You do not have permission to view this booking', 'danger')
            return redirect(url_for('view_bookings'))
    
    return render_template('booking_details.html', booking=booking)

@app.route('/booking/confirmation/<int:booking_id>')
def booking_confirmation(booking_id):
    """Show booking confirmation page"""
    booking = Booking.query.get_or_404(booking_id)
    
    # Check if user has permission to view this booking
    if 'user_id' in session and booking.user_id and booking.user_id != session['user_id']:
        if not session.get('is_admin', False):
            flash('You do not have permission to view this booking', 'danger')
            return redirect(url_for('view_bookings'))
    
    return render_template('booking_confirmation.html', booking=booking)

@app.route('/cancel/<int:booking_id>', methods=['POST'])
def cancel_booking(booking_id):
    """Cancel a booking"""
    booking = Booking.query.get_or_404(booking_id)
    
    # Check if user has permission to cancel this booking
    if 'user_id' in session and booking.user_id and booking.user_id != session['user_id']:
        if not session.get('is_admin', False):
            flash('You do not have permission to cancel this booking', 'danger')
            return redirect(url_for('view_bookings'))
    
    booking.is_active = False
    db.session.commit()
    
    # Simple cancellation without payment handling
    flash('Booking cancelled successfully', 'success')
    
    return redirect(url_for('view_bookings'))

@app.route('/admin/spaces', methods=['GET'])
def admin_spaces():
    """Admin page to view and manage parking spaces"""
    # Check if user is admin
    if not session.get('is_admin', False):
        flash('You do not have permission to access this page', 'danger')
        return redirect(url_for('index'))
    
    spaces = ParkingSpace.query.all()
    return render_template('admin_spaces.html', spaces=spaces)

@app.route('/admin/run-picker', methods=['POST'])
def run_space_picker():
    """Run the parking space picker tool"""
    # Check if user is admin
    if not session.get('is_admin', False):
        flash('You do not have permission to access this feature', 'danger')
        return redirect(url_for('index'))
    
    import subprocess
    try:
        subprocess.Popen(['python', 'parkingspacepicker.py'])
        flash('Parking space picker launched. Please check your desktop for the application window.', 'success')
    except Exception as e:
        flash(f'Error launching parking space picker: {str(e)}', 'danger')
    return redirect(url_for('admin_spaces'))

@app.route('/admin/dashboard')
def admin_dashboard():
    """Admin dashboard with statistics and management options"""
    # Check if user is admin
    if not session.get('is_admin', False):
        flash('You do not have permission to access this page', 'danger')
        return redirect(url_for('index'))
    
    # Get statistics
    total_spaces = ParkingSpace.query.count()
    active_bookings = Booking.query.filter_by(is_active=True, payment_status='Paid').count()
    pending_payments = Booking.query.filter_by(payment_status='Pending').count()
    total_users = User.query.count()
    total_revenue = db.session.query(db.func.sum(Payment.amount)).filter_by(status='Completed').scalar() or 0
    
    # Get recent bookings
    recent_bookings = Booking.query.order_by(Booking.created_at.desc()).limit(10).all()
    
    # Get space utilization by zone
    space_by_zone_query = db.session.query(
        ParkingSpace.zone, 
        db.func.count(ParkingSpace.id)
    ).group_by(ParkingSpace.zone).all()
    
    # Convert Row objects to a dictionary for JSON serialization
    space_by_zone = []
    for zone, count in space_by_zone_query:
        space_by_zone.append({
            'zone': zone,
            'count': count
        })
    
    return render_template(
        'admin/dashboard.html', 
        total_spaces=total_spaces,
        active_bookings=active_bookings,
        pending_payments=pending_payments,
        total_users=total_users,
        total_revenue=total_revenue,
        recent_bookings=recent_bookings,
        space_by_zone=space_by_zone
    )

@app.route('/admin/users')
def admin_users():
    """Admin page to manage users"""
    # Check if user is admin
    if not session.get('is_admin', False):
        flash('You do not have permission to access this page', 'danger')
        return redirect(url_for('index'))
    
    users = User.query.all()
    return render_template('admin/users.html', users=users)

@app.route('/admin/bookings')
def admin_bookings():
    """Admin page to manage all bookings"""
    # Check if user is admin
    if not session.get('is_admin', False):
        flash('You do not have permission to access this page', 'danger')
        return redirect(url_for('index'))
    
    bookings = Booking.query.order_by(Booking.created_at.desc()).all()
    return render_template('admin/bookings.html', bookings=bookings)

@app.route('/admin/reports')
def admin_reports():
    """Admin page to view reports"""
    # Check if user is admin
    if not session.get('is_admin', False):
        flash('You do not have permission to access this page', 'danger')
        return redirect(url_for('index'))
    
    # Get date range from query parameters
    from_date = request.args.get('from_date', (datetime.now() - timedelta(days=30)).strftime('%Y-%m-%d'))
    to_date = request.args.get('to_date', datetime.now().strftime('%Y-%m-%d'))
    
    # Convert to datetime objects
    from_datetime = datetime.strptime(from_date, '%Y-%m-%d')
    to_datetime = datetime.strptime(to_date, '%Y-%m-%d') + timedelta(days=1)  # Include the end date
    
    # Get bookings in date range
    bookings = Booking.query.filter(
        Booking.created_at >= from_datetime,
        Booking.created_at <= to_datetime
    ).all()
    
    # Payment functionality removed
    payments = []
    total_revenue = 0
    total_refunds = 0
    
    return render_template(
        'admin/reports.html',
        bookings=bookings,
        payments=payments,
        total_revenue=total_revenue,
        total_refunds=total_refunds,
        from_date=from_date,
        to_date=to_date
    )

@app.route('/api/space_status')
def api_space_status():
    """API endpoint to get current space status"""
    return jsonify({
        'timestamp': datetime.now().isoformat(),
        'spaces': space_status
    })

@app.route('/api/booking', methods=['POST'])
def api_create_booking():
    """API endpoint to create a booking"""
    data = request.json
    
    # Validate required fields
    required_fields = ['space_id', 'user_name', 'user_email', 'license_plate', 'duration_hours']
    for field in required_fields:
        if field not in data:
            return jsonify({'error': f'Missing required field: {field}'}), 400
    
    space_id = data['space_id']
    user_name = data['user_name']
    user_email = data['user_email']
    license_plate = data['license_plate']
    duration_hours = int(data['duration_hours'])
    
    # Check if space exists and is available
    space = ParkingSpace.query.get(space_id)
    if not space:
        return jsonify({'error': 'Invalid parking space ID'}), 400
        
    # Check if space is already booked
    active_booking = Booking.query.filter_by(parking_space_id=space_id, is_active=True).first()
    if active_booking:
        return jsonify({'error': 'This space is already booked'}), 400
        
    # Create booking
    start_time = datetime.now()
    end_time = start_time + timedelta(hours=duration_hours)
    
    # Calculate price
    total_price = space.hourly_rate * duration_hours
    
    # Generate booking reference
    booking_reference = Booking.generate_reference()
    
    booking = Booking(
        booking_reference=booking_reference,
        user_name=user_name,
        user_email=user_email,
        license_plate=license_plate,
        start_time=start_time,
        end_time=end_time,
        parking_space_id=space_id,
        total_price=total_price,
        payment_status='Paid'
    )
    
    # Mark booking as active
    booking.is_active = True
    
    db.session.add(booking)
    db.session.commit()
    
    return jsonify({
        'success': True,
        'booking_id': booking.id,
        'booking_reference': booking.booking_reference,
        'total_price': booking.total_price,
        'message': 'Booking created successfully'
    })

# Error handlers
@app.errorhandler(404)
def page_not_found(e):
    return render_template('errors/404.html'), 404

@app.errorhandler(500)
def server_error(e):
    return render_template('errors/500.html'), 500

if __name__ == '__main__':
    app.run(debug=True)
