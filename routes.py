import os
from datetime import datetime, timedelta
from flask import render_template, request, redirect, url_for, flash, jsonify, session
from werkzeug.security import generate_password_hash, check_password_hash
from app import app, db
from models import Admin, Student, Motorcycle, ParkingSlot, Reservation
import logging

# Initialize parking slots if none exist
def initialize_data():
    # Create admin if not exists
    admin = Admin.query.filter_by(username='admin').first()
    if not admin:
        admin = Admin(
            username='admin',
            password_hash=generate_password_hash('admin12345')
        )
        db.session.add(admin)
        
    # Create parking slots if not exist
    if ParkingSlot.query.count() == 0:
        for i in range(1, 31):  # Create 30 parking slots
            slot = ParkingSlot(slot_number=i)
            db.session.add(slot)
    
    db.session.commit()

# Initialize data when app starts
with app.app_context():
    initialize_data()

# Homepage route
@app.route('/')
def index():
    # Get available parking slots
    parking_slots = ParkingSlot.query.all()
    return render_template('index.html', parking_slots=parking_slots)

# Get available slots for a specific date and time
@app.route('/get_available_slots', methods=['POST'])
def get_available_slots():
    reservation_date = request.form.get('reservation_date')
    start_time = request.form.get('start_time')
    end_time = request.form.get('end_time')
    
    if not reservation_date or not start_time or not end_time:
        return jsonify({'error': 'Missing required fields'}), 400
    
    # Convert to datetime objects
    date_obj = datetime.strptime(reservation_date, '%Y-%m-%d').date()
    start_time_obj = datetime.strptime(start_time, '%H:%M').time()
    end_time_obj = datetime.strptime(end_time, '%H:%M').time()
    
    # Get all slots
    all_slots = ParkingSlot.query.all()
    
    # Find reservations that overlap with the requested time slot
    overlapping_reservations = Reservation.query.filter(
        Reservation.reservation_date == date_obj,
        Reservation.status.in_(['pending', 'confirmed', 'checked_in']),
        ((Reservation.start_time <= start_time_obj) & (Reservation.end_time > start_time_obj)) |
        ((Reservation.start_time < end_time_obj) & (Reservation.end_time >= end_time_obj)) |
        ((Reservation.start_time >= start_time_obj) & (Reservation.end_time <= end_time_obj))
    ).all()
    
    # Get IDs of slots that are already reserved
    reserved_slot_ids = [r.parking_slot_id for r in overlapping_reservations]
    
    # Filter available slots
    available_slots = [{"id": slot.id, "number": slot.slot_number} 
                      for slot in all_slots if slot.id not in reserved_slot_ids]
    
    return jsonify(available_slots)

# Process reservation form
@app.route('/reserve', methods=['POST'])
def reserve():
    try:
        # Personal info
        name = request.form.get('name')
        year = request.form.get('year')
        program = request.form.get('program')
        section = request.form.get('section')
        email = request.form.get('email')
        
        # Motorcycle info
        motorcycle_description = request.form.get('motorcycle_description')
        plate_number = request.form.get('plate_number')
        
        # Reservation info
        reservation_date = request.form.get('reservation_date')
        start_time = request.form.get('start_time')
        end_time = request.form.get('end_time')
        slot_id = request.form.get('slot_id')
        
        if not all([name, year, program, section, email, motorcycle_description, 
                   plate_number, reservation_date, start_time, end_time, slot_id]):
            flash('All fields are required.', 'danger')
            return redirect(url_for('index'))
        
        # Convert form data to appropriate types
        reservation_date = datetime.strptime(reservation_date, '%Y-%m-%d').date()
        start_time = datetime.strptime(start_time, '%H:%M').time()
        end_time = datetime.strptime(end_time, '%H:%M').time()
        slot_id = int(slot_id)
        
        # Check if student exists by email
        student = Student.query.filter_by(email=email).first()
        if not student:
            # Create new student
            student = Student(
                name=name,
                year=year,
                program=program,
                section=section,
                email=email
            )
            db.session.add(student)
            db.session.flush()  # Flush to get the ID
        
        # Check if motorcycle exists by plate number
        motorcycle = Motorcycle.query.filter_by(plate_number=plate_number).first()
        if not motorcycle:
            # Create new motorcycle
            motorcycle = Motorcycle(
                description=motorcycle_description,
                plate_number=plate_number,
                student_id=student.id
            )
            db.session.add(motorcycle)
            db.session.flush()  # Flush to get the ID
        
        # Create reservation
        reservation = Reservation(
            student_id=student.id,
            motorcycle_id=motorcycle.id,
            parking_slot_id=slot_id,
            reservation_date=reservation_date,
            start_time=start_time,
            end_time=end_time,
            status='pending'  # Initial status
        )
        
        db.session.add(reservation)
        db.session.commit()
        
        flash('Reservation submitted successfully! Waiting for admin confirmation.', 'success')
        return redirect(url_for('index'))
    
    except Exception as e:
        db.session.rollback()
        logging.error(f"Error creating reservation: {str(e)}")
        flash(f'An error occurred: {str(e)}', 'danger')
        return redirect(url_for('index'))

# Admin login page
@app.route('/admin/login', methods=['GET', 'POST'])
def admin_login():
    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')
        
        admin = Admin.query.filter_by(username=username).first()
        
        if admin and check_password_hash(admin.password_hash, password):
            session['admin_logged_in'] = True
            flash('Login successful!', 'success')
            return redirect(url_for('admin_dashboard'))
        else:
            flash('Invalid username or password.', 'danger')
    
    return render_template('admin_login.html')

# Admin logout
@app.route('/admin/logout')
def admin_logout():
    session.pop('admin_logged_in', None)
    flash('Logged out successfully.', 'success')
    return redirect(url_for('admin_login'))

# Check if admin is logged in
def admin_required(func):
    def wrapper(*args, **kwargs):
        if not session.get('admin_logged_in'):
            flash('Please log in first.', 'danger')
            return redirect(url_for('admin_login'))
        return func(*args, **kwargs)
    wrapper.__name__ = func.__name__
    return wrapper

# Admin dashboard
@app.route('/admin')
@admin_required
def admin_dashboard():
    # Get all reservations grouped by status
    pending_reservations = Reservation.query.filter_by(status='pending').order_by(Reservation.created_at.desc()).all()
    confirmed_reservations = Reservation.query.filter_by(status='confirmed').order_by(Reservation.created_at.desc()).all()
    checked_in_reservations = Reservation.query.filter_by(status='checked_in').order_by(Reservation.created_at.desc()).all()
    completed_reservations = Reservation.query.filter_by(status='completed').order_by(Reservation.created_at.desc()).all()
    
    return render_template('admin.html', 
                          pending_reservations=pending_reservations,
                          confirmed_reservations=confirmed_reservations,
                          checked_in_reservations=checked_in_reservations,
                          completed_reservations=completed_reservations)

# Update reservation status
@app.route('/admin/update_status/<int:reservation_id>', methods=['POST'])
@admin_required
def update_status(reservation_id):
    status = request.form.get('status')
    
    if not status:
        flash('Status is required.', 'danger')
        return redirect(url_for('admin_dashboard'))
    
    reservation = Reservation.query.get_or_404(reservation_id)
    reservation.status = status
    
    # Update timestamps based on status
    if status == 'checked_in':
        reservation.checked_in_at = datetime.utcnow()
    elif status == 'completed':
        reservation.checked_out_at = datetime.utcnow()
    
    db.session.commit()
    flash(f'Reservation status updated to {status}.', 'success')
    return redirect(url_for('admin_dashboard'))

# API to get reservation details
@app.route('/get_reservation/<int:reservation_id>')
def get_reservation(reservation_id):
    reservation = Reservation.query.get_or_404(reservation_id)
    student = Student.query.get(reservation.student_id)
    motorcycle = Motorcycle.query.get(reservation.motorcycle_id)
    parking_slot = ParkingSlot.query.get(reservation.parking_slot_id)
    
    data = {
        'id': reservation.id,
        'student_name': student.name,
        'student_email': student.email,
        'motorcycle_description': motorcycle.description,
        'plate_number': motorcycle.plate_number,
        'slot_number': parking_slot.slot_number,
        'reservation_date': reservation.reservation_date.strftime('%Y-%m-%d'),
        'start_time': reservation.start_time.strftime('%H:%M'),
        'end_time': reservation.end_time.strftime('%H:%M'),
        'status': reservation.status,
        'created_at': reservation.created_at.strftime('%Y-%m-%d %H:%M:%S'),
    }
    
    if reservation.checked_in_at:
        data['checked_in_at'] = reservation.checked_in_at.strftime('%Y-%m-%d %H:%M:%S')
    
    if reservation.checked_out_at:
        data['checked_out_at'] = reservation.checked_out_at.strftime('%Y-%m-%d %H:%M:%S')
    
    return jsonify(data)

# Error handlers
@app.errorhandler(404)
def page_not_found(e):
    return render_template('error.html', error='Page not found'), 404

@app.errorhandler(500)
def server_error(e):
    return render_template('error.html', error='Server error occurred'), 500
