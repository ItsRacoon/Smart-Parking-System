from flask import Blueprint, render_template, current_app, url_for
from flask_mail import Mail, Message
from models import Booking, ParkingSpace, User
import qrcode
from io import BytesIO
import base64
import os
from datetime import datetime

# Initialize Blueprint
mail_service = Blueprint('mail_service', __name__)

# Initialize Mail
mail = Mail()

# Add a route to test QR code generation
@mail_service.route('/test_qr_code')
def test_qr_code():
    try:
        test_data = "TEST-QR-CODE-123"
        qr_code = generate_qr_code(test_data)
        if qr_code:
            return f"""
            <html>
            <body>
                <h1>QR Code Test</h1>
                <p>QR code generated successfully!</p>
                <img src="data:image/png;base64,{qr_code}" width="200" height="200">
            </body>
            </html>
            """
        else:
            return "Failed to generate QR code", 500
    except Exception as e:
        return f"Error: {str(e)}", 500

def init_mail(app):
    """Initialize the mail extension with the Flask app"""
    # Configure Flask-Mail
    app.config['MAIL_SERVER'] = os.environ.get('MAIL_SERVER', 'smtp.gmail.com')
    app.config['MAIL_PORT'] = int(os.environ.get('MAIL_PORT', 587))
    app.config['MAIL_USE_TLS'] = os.environ.get('MAIL_USE_TLS', 'True').lower() in ['true', '1', 't']
    app.config['MAIL_USE_SSL'] = os.environ.get('MAIL_USE_SSL', 'False').lower() in ['true', '1', 't']
    app.config['MAIL_USERNAME'] = os.environ.get('MAIL_USERNAME', '')
    app.config['MAIL_PASSWORD'] = os.environ.get('MAIL_PASSWORD', '')
    app.config['MAIL_DEFAULT_SENDER'] = os.environ.get('MAIL_DEFAULT_SENDER', 'noreply@smartparking.com')
    
    # Initialize mail with app
    mail.init_app(app)
    
    # Register blueprint
    app.register_blueprint(mail_service)
    
    # Log mail configuration
    app.logger.info("Mail service initialized")

def generate_qr_code(data):
    """Generate a QR code as a base64 encoded image"""
    try:
        # Use the simpler qrcode.make approach which handles PIL internally
        import qrcode
        from PIL import Image
        
        # Create QR code directly
        img = qrcode.make(data)
        
        # Save QR code to BytesIO object
        buffer = BytesIO()
        img.save(buffer, format="PNG")
        buffer.seek(0)
        
        # Encode as base64 string
        qr_base64 = base64.b64encode(buffer.getvalue()).decode('utf-8')
        
        # Log success
        current_app.logger.info(f"QR code generated successfully, length: {len(qr_base64)}")
        
        # Verify the base64 string is not empty
        if not qr_base64:
            current_app.logger.error("Generated QR code base64 string is empty")
            return ""
            
        return qr_base64
    except ImportError as e:
        current_app.logger.error(f"Missing required library: {str(e)}")
        return ""
    except Exception as e:
        current_app.logger.error(f"Error generating QR code: {str(e)}")
        return ""

def send_booking_confirmation(booking_id):
    """Send booking confirmation email with QR code"""
    try:
        # Get booking details
        booking = Booking.query.get(booking_id)
        if not booking:
            current_app.logger.error(f"Booking {booking_id} not found")
            return False
        
        # Get parking space details
        parking_space = ParkingSpace.query.get(booking.parking_space_id)
        if not parking_space:
            current_app.logger.error(f"Parking space {booking.parking_space_id} not found")
            return False
        
        # Use a simpler approach for QR code data - just the booking reference
        # This is more likely to work reliably in all email clients
        qr_data_str = f"SMART-PARKING-BOOKING:{booking.booking_reference}"
        
        current_app.logger.info(f"Generating QR code for booking {booking.booking_reference}")
        
        # Generate QR code
        qr_code = generate_qr_code(qr_data_str)
        
        # Log the result
        if qr_code:
            current_app.logger.info(f"QR code generated successfully for booking {booking.booking_reference}")
        else:
            current_app.logger.error(f"Failed to generate QR code for booking {booking.booking_reference}")
            # Continue without QR code
        
        # Create email message
        subject = f"Smart Parking Confirmation - Booking #{booking.booking_reference}"
        
        # Get user details if available
        user_name = booking.user_name
        if booking.user_id:
            user = User.query.get(booking.user_id)
            if user:
                user_name = f"{user.first_name} {user.last_name}"
        
        # Create HTML message with inline QR code
        html_body = render_template(
            'email/booking_confirmation.html',
            booking=booking,
            parking_space=parking_space,
            user_name=user_name,
            qr_code=qr_code
        )
        
        # Create plain text message as fallback
        text_body = f"""
        Smart Parking Confirmation - Booking #{booking.booking_reference}
        
        Dear {user_name},
        
        Thank you for your booking at Smart Parking. Your booking details are:
        
        Booking Reference: {booking.booking_reference}
        Parking Space: {parking_space.space_id} ({parking_space.zone})
        Vehicle: {booking.license_plate}
        Start Time: {booking.start_time.strftime('%Y-%m-%d %H:%M')}
        End Time: {booking.end_time.strftime('%Y-%m-%d %H:%M')}
        Total Price: ₹{booking.total_price:.2f}
        
        Please show the QR code in the HTML version of this email when you arrive at the parking lot.
        
        Thank you for choosing Smart Parking!
        """
        
        # Create message
        msg = Message(
            subject=subject,
            recipients=[booking.user_email],
            body=text_body,
            html=html_body
        )
        
        # Send email
        mail.send(msg)
        
        current_app.logger.info(f"Confirmation email sent for booking {booking.booking_reference}")
        return True
    
    except Exception as e:
        current_app.logger.error(f"Error sending confirmation email: {str(e)}")
        return False