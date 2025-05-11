from flask import Blueprint, render_template, request, redirect, url_for, flash, session
from models import db, Booking, Payment
from datetime import datetime
import uuid

payment = Blueprint('payment', __name__)

@payment.route('/checkout/<int:booking_id>', methods=['GET', 'POST'])
def checkout(booking_id):
    """Process payment for a booking"""
    # Get the booking
    booking = Booking.query.get_or_404(booking_id)
    
    # Check if booking is already paid
    if booking.payment_status == 'Paid':
        flash('This booking has already been paid for', 'info')
        return redirect(url_for('booking_confirmation', booking_id=booking.id))
    
    if request.method == 'POST':
        # Process payment (in a real app, this would integrate with a payment gateway)
        payment_method = request.form.get('payment_method', 'Credit Card')
        card_number = request.form.get('card_number')
        card_name = request.form.get('card_name')
        
        # Simple validation
        if payment_method == 'Credit Card' and (not card_number or not card_name):
            flash('Please provide all payment details', 'danger')
            return render_template('payment/checkout.html', booking=booking)
        
        # Create payment record
        payment = Payment(
            booking_id=booking.id,
            amount=booking.total_price,
            payment_method=payment_method,
            transaction_id=str(uuid.uuid4()),
            payment_date=datetime.now()
        )
        
        # Update booking status
        booking.payment_status = 'Paid'
        booking.is_active = True
        
        db.session.add(payment)
        db.session.commit()
        
        flash('Payment successful!', 'success')
        return redirect(url_for('booking_confirmation', booking_id=booking.id))
    
    return render_template('payment/checkout.html', booking=booking)

@payment.route('/receipt/<int:booking_id>')
def receipt(booking_id):
    """Show payment receipt"""
    booking = Booking.query.get_or_404(booking_id)
    payment = Payment.query.filter_by(booking_id=booking.id).first_or_404()
    
    return render_template('payment/receipt.html', booking=booking, payment=payment)