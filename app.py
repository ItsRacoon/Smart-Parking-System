from flask import Flask, render_template, Response, request, redirect, url_for, jsonify, flash
import cv2
import pickle
import cvzone
import numpy as np
import os
from datetime import datetime, timedelta
from models import db, ParkingSpace, Booking

app = Flask(__name__)
app.config['SECRET_KEY'] = os.urandom(24)
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///parking.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

db.init_app(app)

# Create database tables
with app.app_context():
    db.create_all()
    # Initialize parking spaces from CarParkPos if not already in database
    spaces_count = ParkingSpace.query.count()
    if spaces_count == 0:
        with open('CarParkPos', 'rb') as f:
            posList = pickle.load(f)
        for i, pos in enumerate(posList):
            x, y = pos
            space = ParkingSpace(position_x=x, position_y=y, space_id=f'P{i+1:03d}')
            db.session.add(space)
        db.session.commit()

cap = cv2.VideoCapture('carPark.mp4')
with open('CarParkPos', 'rb') as f:
    posList = pickle.load(f)

width, height = 107, 48

# Dictionary to store space status
space_status = {}

def checkParkingSpace(imgPro, img):
    spaceCounter = 0
    free_spaces = []
    
    # Get all active bookings
    with app.app_context():
        active_bookings = Booking.query.filter_by(is_active=True).all()
        booked_spaces = [booking.parking_space_id for booking in active_bookings]
        all_spaces = ParkingSpace.query.all()
        space_mapping = {(space.position_x, space.position_y): space.id for space in all_spaces}
    
    for i, pos in enumerate(posList):
        x, y = pos
        imgCrop = imgPro[y:y + height, x:x + width]
        count = cv2.countNonZero(imgCrop)
        
        # Check if space is physically empty (by computer vision)
        is_empty = count < 900
        
        # Check if space is booked
        space_id = space_mapping.get((x, y))
        is_booked = space_id in booked_spaces
        
        # Update space status
        space_status[i] = {
            'id': space_id,
            'position': (x, y),
            'is_empty': is_empty,
            'is_booked': is_booked,
            'is_available': is_empty and not is_booked
        }
        
        if is_empty and not is_booked:
            color = (0, 255, 0)  # Green for available
            thickness = 5
            spaceCounter += 1
            free_spaces.append(i)
        elif is_empty and is_booked:
            color = (255, 165, 0)  # Orange for booked but empty
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
    if request.method == 'POST':
        space_id = request.form.get('space_id')
        user_name = request.form.get('user_name')
        user_email = request.form.get('user_email')
        license_plate = request.form.get('license_plate')
        duration_hours = int(request.form.get('duration', 1))
        
        # Validate input
        if not all([space_id, user_name, user_email, license_plate]):
            flash('All fields are required')
            return redirect(url_for('book_space'))
        
        # Check if space exists and is available
        space = ParkingSpace.query.get(space_id)
        if not space:
            flash('Invalid parking space selected')
            return redirect(url_for('book_space'))
            
        # Check if space is already booked
        active_booking = Booking.query.filter_by(parking_space_id=space_id, is_active=True).first()
        if active_booking:
            flash('This space is already booked')
            return redirect(url_for('book_space'))
            
        # Create booking
        start_time = datetime.now()
        end_time = start_time + timedelta(hours=duration_hours)
        
        booking = Booking(
            user_name=user_name,
            user_email=user_email,
            license_plate=license_plate,
            start_time=start_time,
            end_time=end_time,
            parking_space_id=space_id
        )
        
        db.session.add(booking)
        db.session.commit()
        
        flash(f'Space booked successfully until {end_time.strftime("%Y-%m-%d %H:%M")}')
        return redirect(url_for('index'))
        
    # GET request - show booking form with available spaces
    spaces = []
    for idx, status in space_status.items():
        if status.get('is_available', False):
            spaces.append({
                'id': status['id'],
                'label': f"P{idx+1:03d}"
            })
    
    return render_template('booking.html', spaces=spaces)

@app.route('/bookings')
def view_bookings():
    """View all active bookings"""
    bookings = Booking.query.filter_by(is_active=True).all()
    return render_template('bookings.html', bookings=bookings)

@app.route('/cancel/<int:booking_id>', methods=['POST'])
def cancel_booking(booking_id):
    """Cancel a booking"""
    booking = Booking.query.get_or_404(booking_id)
    booking.is_active = False
    db.session.commit()
    flash('Booking cancelled successfully')
    return redirect(url_for('view_bookings'))

@app.route('/admin/spaces', methods=['GET'])
def admin_spaces():
    """Admin page to view and manage parking spaces"""
    spaces = ParkingSpace.query.all()
    return render_template('admin_spaces.html', spaces=spaces)

@app.route('/admin/run-picker', methods=['POST'])
def run_space_picker():
    """Run the parking space picker tool"""
    import subprocess
    try:
        subprocess.Popen(['python', 'parkingspacepicker.py'])
        flash('Parking space picker launched. Please check your desktop for the application window.')
    except Exception as e:
        flash(f'Error launching parking space picker: {str(e)}', 'error')
    return redirect(url_for('admin_spaces'))

if __name__ == '__main__':
    app.run(debug=True)
