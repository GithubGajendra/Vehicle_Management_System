from extensions import db
from datetime import datetime
from zoneinfo import ZoneInfo

# Model for user

class User(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    fullname = db.Column(db.String(150), nullable=False)
    email = db.Column(db.String(150), unique=True, nullable=False)
    password = db.Column(db.String(150), nullable=False)
    vehicle_number = db.Column(db.String(50), nullable=False)
    role = db.Column(db.String(50), nullable=False, default='user')

class Booking(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    spot_id = db.Column(db.Integer, db.ForeignKey('parking_spot.id'), nullable=False)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    start_time = db.Column(db.DateTime, nullable=False, default=lambda: datetime.now(ZoneInfo("Asia/Kolkata")))
    end_time = db.Column(db.DateTime, nullable=True)
    cost = db.Column(db.Float, nullable=True)
    spot = db.relationship('ParkingSpot', backref='bookings')
    user = db.relationship('User', backref=db.backref('bookings', lazy=True))

class ParkingLot(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(150), nullable=False) 
    price = db.Column(db.Float, nullable=False)
    address = db.Column(db.String(250), nullable=False)
    pincode = db.Column(db.String(10), nullable=False)
    capacity = db.Column(db.Integer, nullable=False) 
    spots = db.relationship('ParkingSpot', backref='lot', lazy=True)

class ParkingSpot(db.Model):
    id = db.Column(db.Integer, primary_key = True)
    lotid = db.Column(db.Integer, db.ForeignKey('parking_lot.id'), nullable=False)
    status = db.Column(db.String(20), nullable=False, default='Available')
    spotnumber = db.Column(db.String(10), nullable=False)
    