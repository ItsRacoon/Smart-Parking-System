from flask import Blueprint, render_template, request, redirect, url_for, flash, session, jsonify, current_app
from models import db, Booking, Payment, User
from datetime import datetime
import razorpay
import os
import json
import hmac
import hashlib
import uuid
from dotenv import load_dotenv
from mail_service import send_booking_confirmation

# Load environment variables from .env file
load_dotenv()

payment = Blueprint('payment', __name__)

# Initialize Razorpay client with keys from environment variables
RAZORPAY_KEY_ID = os.environ.get('RAZORPAY_KEY_ID')
RAZORPAY_KEY_SECRET = os.environ.get('RAZORPAY_KEY_SECRET')

client = razorpay.Client(auth=(RAZORPAY_KEY_ID, RAZORPAY_KEY_SECRET))

@payment.route('/checkout/<int:booking_id>', methods=['GET'])
def checkout(booking_id):
    """Show checkout page for a booking"""
    # Check if booking exists
    booking = Booking.query.get_or_404(booking_id)
    
    # Check if user has permission to view this booking
    if 'user_id' in session and booking.user_id and booking.user_id != session['user_id']:
        if not session.get('is_admin', False):
            flash('You do not have permission to access this booking', 'danger')
            return redirect(url_for('view_bookings'))
    
    # Check if booking is already paid
    if booking.payment_status == 'Paid':
        flash('This booking has already been paid for', 'info')
        return redirect(url_for('booking_confirmation', booking_id=booking.id))
    
    # Get user details
    user = None
    if booking.user_id:
        user = User.query.get(booking.user_id)
    
    # Create Razorpay order
    amount = int(booking.total_price * 100)  # Convert to paise (smallest Indian currency unit)
    
    order_data = {
        'amount': amount,
        'currency': 'INR',
        'receipt': f'booking_{booking.id}',
        'notes': {
            'booking_id': booking.id,
            'space_id': booking.parking_space.space_id,
            'user_email': booking.user_email
        }
    }
    
    try:
        order = client.order.create(data=order_data)
        
        # Save order details to database
        try:
            payment = Payment(
                booking_id=booking.id,
                amount=booking.total_price,
                payment_method='Razorpay',
                transaction_id=order['id'],
                payment_id=None,  # Will be set after payment
                status='Pending',
                payment_date=datetime.now(),
                currency='INR',
                payment_data=json.dumps(order)
            )
        except Exception as e:
            # Fallback for older database schema
            print(f"Error creating payment with new schema: {str(e)}")
            payment = Payment(
                booking_id=booking.id,
                amount=booking.total_price,
                payment_method='Razorpay',
                transaction_id=order['id'],
                status='Pending',
                payment_date=datetime.now()
            )
        db.session.add(payment)
        db.session.commit()
        
        return render_template(
            'payment/checkout.html',
            booking=booking,
            user=user,
            razorpay_key_id=RAZORPAY_KEY_ID,
            order=order,
            callback_url=url_for('payment.verify_payment', _external=True)
        )
    except Exception as e:
        flash(f'Error creating payment: {str(e)}', 'danger')
        return redirect(url_for('booking_details', reference=booking.booking_reference))

@payment.route('/verify', methods=['POST'])
def verify_payment():
    """Verify Razorpay payment callback"""
    try:
        # Get payment data from request
        payment_id = request.form.get('razorpay_payment_id')
        order_id = request.form.get('razorpay_order_id')
        signature = request.form.get('razorpay_signature')
        
        # Verify signature
        data = f'{order_id}|{payment_id}'
        generated_signature = hmac.new(
            RAZORPAY_KEY_SECRET.encode(),
            data.encode(),
            hashlib.sha256
        ).hexdigest()
        
        if generated_signature != signature:
            # Invalid signature
            flash('Invalid payment signature', 'danger')
            return redirect(url_for('index'))
        
        # Get payment details from database
        payment = Payment.query.filter_by(transaction_id=order_id).first()
        if not payment:
            flash('Payment not found', 'danger')
            return redirect(url_for('index'))
        
        # Update payment status
        payment.status = 'Completed'
        try:
            payment.payment_id = payment_id
        except Exception as e:
            print(f"Could not set payment_id: {str(e)}")
        payment.payment_date = datetime.now()
        
        # Update booking payment status and activate the booking
        try:
            booking = Booking.query.get(payment.booking_id)
            booking.payment_status = 'Paid'
            booking.is_active = True
            
            # Log the payment activation
            print(f"Booking {booking.booking_reference} activated after payment {payment_id}")
        except Exception as e:
            print(f"Error updating booking status: {str(e)}")
            flash('Payment was successful, but there was an error updating your booking. Please contact support.', 'warning')
        
        db.session.commit()
        
        # Send confirmation email with QR code
        try:
            email_sent = send_booking_confirmation(booking.id)
            if email_sent:
                flash('Payment successful! A confirmation email with your ticket has been sent.', 'success')
            else:
                flash('Payment successful! However, there was an issue sending the confirmation email.', 'warning')
        except Exception as e:
            current_app.logger.error(f"Error sending confirmation email: {str(e)}")
            flash('Payment successful! However, there was an issue sending the confirmation email.', 'warning')
        
        # Redirect to receipt page
        return redirect(url_for('payment.receipt', booking_id=booking.id))
    except Exception as e:
        flash(f'Error verifying payment: {str(e)}', 'danger')
        return redirect(url_for('index'))

@payment.route('/receipt/<int:booking_id>')
def receipt(booking_id):
    """Show payment receipt"""
    booking = Booking.query.get_or_404(booking_id)
    payment = Payment.query.filter_by(booking_id=booking.id).first_or_404()
    
    # Check if user has permission to view this receipt
    if 'user_id' in session and booking.user_id and booking.user_id != session['user_id']:
        if not session.get('is_admin', False):
            flash('You do not have permission to view this receipt', 'danger')
            return redirect(url_for('view_bookings'))
    
    return render_template('payment/receipt.html', booking=booking, payment=payment)

@payment.route('/webhook', methods=['POST'])
def webhook():
    """Handle Razorpay webhook events"""
    # Get webhook data
    webhook_data = request.json
    
    # Verify webhook signature
    webhook_signature = request.headers.get('X-Razorpay-Signature')
    if not webhook_signature:
        return jsonify({'status': 'error', 'message': 'Missing webhook signature'}), 400
    
    # Verify signature
    generated_signature = hmac.new(
        RAZORPAY_KEY_SECRET.encode(),
        request.data,
        hashlib.sha256
    ).hexdigest()
    
    if generated_signature != webhook_signature:
        return jsonify({'status': 'error', 'message': 'Invalid webhook signature'}), 400
    
    # Process webhook event
    event = webhook_data.get('event')
    
    if event == 'payment.authorized':
        # Payment was authorized
        payment_id = webhook_data['payload']['payment']['entity']['id']
        order_id = webhook_data['payload']['payment']['entity']['order_id']
        
        # Update payment status
        payment = Payment.query.filter_by(transaction_id=order_id).first()
        if payment:
            payment.status = 'Completed'
            try:
                payment.payment_id = payment_id
            except Exception as e:
                print(f"Could not set payment_id in webhook: {str(e)}")
            payment.payment_date = datetime.now()
            
            # Update booking payment status and activate the booking
            try:
                booking = Booking.query.get(payment.booking_id)
                booking.payment_status = 'Paid'
                booking.is_active = True
                
                # Log the webhook activation
                print(f"Webhook: Booking {booking.booking_reference} activated after payment {payment_id}")
                
                # Send confirmation email with QR code
                try:
                    email_sent = send_booking_confirmation(booking.id)
                    if email_sent:
                        print(f"Webhook: Confirmation email sent for booking {booking.booking_reference}")
                    else:
                        print(f"Webhook: Failed to send confirmation email for booking {booking.booking_reference}")
                except Exception as e:
                    print(f"Webhook: Error sending confirmation email: {str(e)}")
            except Exception as e:
                print(f"Error updating booking status in webhook: {str(e)}")
            
            db.session.commit()
    
    elif event == 'payment.failed':
        # Payment failed
        order_id = webhook_data['payload']['payment']['entity']['order_id']
        
        # Update payment status
        payment = Payment.query.filter_by(transaction_id=order_id).first()
        if payment:
            payment.status = 'Failed'
            db.session.commit()
    
    return jsonify({'status': 'success'}), 200