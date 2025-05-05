from datetime import datetime
from app import db

class Admin(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(64), unique=True, nullable=False)
    password_hash = db.Column(db.String(256), nullable=False)

class Student(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    year = db.Column(db.String(20), nullable=False)
    program = db.Column(db.String(100), nullable=False)
    section = db.Column(db.String(50), nullable=False)
    email = db.Column(db.String(120), nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    reservations = db.relationship('Reservation', backref='student', lazy=True)

class Motorcycle(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    description = db.Column(db.String(200), nullable=False)
    plate_number = db.Column(db.String(20), nullable=False, unique=True)
    student_id = db.Column(db.Integer, db.ForeignKey('student.id'), nullable=False)
    reservations = db.relationship('Reservation', backref='motorcycle', lazy=True)

class ParkingSlot(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    slot_number = db.Column(db.Integer, nullable=False, unique=True)
    is_available = db.Column(db.Boolean, default=True)
    reservations = db.relationship('Reservation', backref='parking_slot', lazy=True)

class Reservation(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    student_id = db.Column(db.Integer, db.ForeignKey('student.id'), nullable=False)
    motorcycle_id = db.Column(db.Integer, db.ForeignKey('motorcycle.id'), nullable=False)
    parking_slot_id = db.Column(db.Integer, db.ForeignKey('parking_slot.id'), nullable=False)
    reservation_date = db.Column(db.Date, nullable=False)
    start_time = db.Column(db.Time, nullable=False)
    end_time = db.Column(db.Time, nullable=False)
    status = db.Column(db.String(20), default='pending')  # pending, confirmed, checked_in, completed, cancelled
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    checked_in_at = db.Column(db.DateTime, nullable=True)
    checked_out_at = db.Column(db.DateTime, nullable=True)
