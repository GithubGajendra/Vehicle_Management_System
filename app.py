from flask import Flask, render_template, request, flash, redirect, url_for, session
from extensions import db
from werkzeug.security import generate_password_hash, check_password_hash
import os
from datetime import datetime
from zoneinfo import ZoneInfo
from models import User, ParkingLot, ParkingSpot, Booking

# base directory setup
basedir = os.path.abspath(os.path.dirname(__file__))

app = Flask(__name__)

# configuration of sqlite db
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///' + os.path.join(basedir, 'database.db')
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
app.config['SECRET_KEY'] = 'demo_key_vpark_app'

# initializing the database
db.init_app(app)

with app.app_context():
    print("Creating database tables...")
    # Create tables using models.py file
    db.create_all()
    print("Database tables created.")

    # Checking if the admin already exists
    if User.query.filter_by(role='admin').first() is None:
        print("Creating admin user...")
        hashed_password = generate_password_hash('parkingadmin', method='pbkdf2:sha256')
        admin = User(
            fullname='Admin_Gajendra',
            email='admin@vparkapp.xyz',
            password=hashed_password,
            vehicle_number='N/A',
            role='admin'
        )
        db.session.add(admin)
        db.session.commit()
        print("Admin user created successfully.")
    else:
        print("Admin user already exists.")

@app.route('/')
def home():
    return render_template('index.html')


@app.route('/login', methods=['GET', 'POST'])
def login_page():
    if request.method == 'POST':
        email = request.form.get('email')
        password = request.form.get('password')

        user = User.query.filter_by(email=email).first()

        if not user or not check_password_hash(user.password, password):
            flash('Incorrect login credentials! Please try again or sign up.', "danger")
            return redirect(url_for('login_page'))

        session['user_id'] = user.id
        session['user_role'] = user.role

        if user.role == 'admin':
            return redirect(url_for('admin_dashboard'))
        else:
            return redirect(url_for('user_dashboard'))

    return render_template('login.html')


@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        fullname = request.form.get('fullname')
        email = request.form.get('email')
        password = request.form.get('password')
        vehicle_number = request.form.get('vehicle_number')

        user = User.query.filter_by(email=email).first()
        if user:
            flash('User already exists with the same email', "danger")
            return redirect('/login')

        new_user = User(
            fullname=fullname,
            email=email,
            password=generate_password_hash(password, method='pbkdf2:sha256'),
            vehicle_number=vehicle_number
        )
        db.session.add(new_user)
        db.session.commit()

        flash('Registration Successful! Now you can park your car by logging in.', "success")
        return redirect('/login')

    return render_template('register.html')


@app.route('/choice')
def choice():
    return render_template('choice.html')


@app.route('/logout')
def logout():
    session.clear()
    flash('You have been logged out.', "success")
    return redirect(url_for('home'))


@app.route('/admin_dashboard', methods=['GET', 'POST'])
def admin_dashboard():
    if 'user_role' not in session or session['user_role'] != 'admin':
        flash('You must be an admin to view this page.', "danger")
        return redirect(url_for('login_page'))

    if request.method == 'POST':
        name = request.form.get('name')
        capacity = int(request.form.get('capacity'))
        price = float(request.form.get('price'))
        address = request.form.get('address')
        pincode = request.form.get('pincode')

        new_lot = ParkingLot(name=name, capacity=capacity, price=price, address=address, pincode=pincode)
        db.session.add(new_lot)
        db.session.commit()

        for i in range(capacity):
            spot = ParkingSpot(lotid=new_lot.id, spotnumber=f"S{i}")
            db.session.add(spot)

        db.session.commit()
        flash(f'Parking lot "{name}" and its {capacity} spots have been created successfully!', "success")
        return redirect(url_for('admin_dashboard'))

    all_lots = ParkingLot.query.order_by(ParkingLot.id).all()
    completed_bookings = Booking.query.filter(Booking.end_time != None).order_by(Booking.end_time.desc()).all()

    total_available_spots = ParkingSpot.query.filter_by(status='Available').count()
    total_occupied_spots = ParkingSpot.query.filter_by(status='Occupied').count()
    total_existing_lots = ParkingLot.query.count()
    occupied_bookings = Booking.query.filter_by(end_time=None).all()

    return render_template(
        'admin_dashboard.html', 
        lots=all_lots, 
        bookings=completed_bookings,
        total_available_spots=total_available_spots,
        total_occupied_spots=total_occupied_spots,
        total_existing_lots=total_existing_lots,
        occupied_bookings = occupied_bookings
        )


@app.route('/user_dashboard')
def user_dashboard():
    if 'user_id' not in session or session['user_role'] != 'user':
        flash('Please log in to view this page.', "danger")
        return redirect(url_for('login_page'))

    user_id = session['user_id']
    user = User.query.get(user_id)

    active_booking = Booking.query.filter_by(user_id=user_id, end_time=None).first()
    available_lots = ParkingLot.query.filter(ParkingLot.spots.any(status='Available')).all()
    past_bookings = Booking.query.filter(
        Booking.user_id == user_id, Booking.end_time != None
    ).order_by(Booking.start_time.desc()).all()

    return render_template('user_dashboard.html',
                           user=user,
                           active_booking=active_booking,
                           available_lots=available_lots,
                           past_bookings=past_bookings)


@app.route('/book_spot/<int:lotid>')
def book_spot(lotid):
    if 'user_id' not in session or session['user_role'] != 'user':
        flash('You must be logged in to book a spot.', "danger")
        return redirect(url_for('login_page'))

    user_id = session['user_id']

    if Booking.query.filter_by(user_id=user_id, end_time=None).first():
        flash('You already have an active booking. Please release it before booking another.', "danger")
        return redirect(url_for('user_dashboard'))

    spot = ParkingSpot.query.filter_by(lotid=lotid, status='Available').first()
    ist_now = datetime.now(ZoneInfo("Asia/Kolkata"))

    if spot:
        spot.status = 'Occupied'
        new_booking = Booking(spot_id=spot.id, user_id=user_id, start_time=ist_now)
        db.session.add(new_booking)
        db.session.commit()
        flash(f'Successfully booked Spot ID {spot.id} in {spot.lot.name}!', "success")
    else:
        flash('Sorry, no spots are available in this lot at the moment.', "danger")

    return redirect(url_for('user_dashboard'))


@app.route('/release_spot/<int:booking_id>')
def release_spot(booking_id):
    if 'user_id' not in session or session['user_role'] != 'user':
        flash('You must be logged in to perform this action.', "danger")
        return redirect(url_for('login_page'))

    booking = Booking.query.get(booking_id)

    if booking and booking.user_id == session['user_id']:
        booking.end_time = datetime.now(ZoneInfo("Asia/Kolkata"))
        spot = ParkingSpot.query.get(booking.spot_id)

        # Calculate the duration of parking in hours

        start = booking.start_time
        end = booking.end_time

        if start.tzinfo is None:
            start = start.replace(tzinfo=ZoneInfo("Asia/Kolkata"))
        if end.tzinfo is None:
            end = end.replace(tzinfo=ZoneInfo("Asia/Kolkata"))

        duration = end - start
        hours_parked = duration.total_seconds() / 3600
        
        # Calculate the total cost based on the lot's price
        total_cost = hours_parked * spot.lot.price
        
        # Store the final cost in the booking record
        booking.cost = total_cost

        spot.status = 'Available'
        db.session.commit()
        flash(f'Spot {spot.id} has been released. Total cost: ₹{total_cost:.2f}. Thank you!', "success")
    else:
        flash('Error: Could not find your booking.', "danger")

    return redirect(url_for('user_dashboard'))

@app.route('/edit_lot/<int:lot_id>', methods=['GET', 'POST'])
def edit_lot(lot_id):
    if 'user_role' not in session or session['user_role'] != 'admin':
        flash('Unauthorized access.', "danger")
        return redirect(url_for('login_page'))

    lot = ParkingLot.query.get_or_404(lot_id)

    if request.method == 'POST':
        new_capacity = int(request.form.get('capacity'))
        existing_spots = ParkingSpot.query.filter_by(lotid=lot.id).order_by(ParkingSpot.id).all()
        current_count = len(existing_spots)

        lot.name = request.form.get('name')
        lot.price = float(request.form.get('price'))
        lot.address = request.form.get('address')
        lot.pincode = request.form.get('pincode')
        lot.capacity = new_capacity

        if new_capacity > current_count:
            # Add new spots
            for i in range(current_count, new_capacity):
                spot = ParkingSpot(lotid=lot.id, spotnumber=f"S{i}", status='Available')
                db.session.add(spot)

        elif new_capacity < current_count:
            # Only delete extra spots if they are available
            excess_spots = existing_spots[new_capacity:]
            for spot in reversed(excess_spots):
                if spot.status == 'Available':
                    db.session.delete(spot)
                else:
                    flash(f"Cannot delete Spot {spot.spotnumber} because it's currently occupied.", "danger")
                    db.session.rollback()
                    return redirect(url_for('edit_lot', lot_id=lot.id))

        db.session.commit()
        flash('Lot updated and spot count synced successfully.', "success")
        return redirect(url_for('admin_dashboard'))

    return render_template('edit_lot.html', lot=lot)

@app.route('/lot_spots/<int:lot_id>')
def view_lot_spots(lot_id):
    if 'user_role' not in session or session['user_role'] != 'admin':
        flash('Unauthorized access.', "danger")
        return redirect(url_for('login_page'))

    lot = ParkingLot.query.get_or_404(lot_id)
    spots = ParkingSpot.query.filter_by(lotid=lot.id).order_by(ParkingSpot.id).all()

    return render_template('view_spots.html', lot=lot, spots=spots)



@app.route('/delete_lot/<int:lot_id>', methods=['POST'])
def delete_lot(lot_id):
    if 'user_role' not in session or session['user_role'] != 'admin':
        flash('Unauthorized access.', "danger")
        return redirect(url_for('login_page'))

    lot = ParkingLot.query.get_or_404(lot_id)

    
    for spot in lot.spots:
        if spot.status != 'Available':
            flash("lot can not be deleted. as one or more spots are occupied.", "danger")
            return redirect(url_for('admin_dashboard'))
    
    # Delete related spots and bookings
    for spot in lot.spots:
        Booking.query.filter_by(spot_id=spot.id).delete()
        db.session.delete(spot)
    
    db.session.delete(lot)
    db.session.commit()
    flash('Parking lot deleted successfully.', "success")
    return redirect(url_for('admin_dashboard'))

@app.route('/view_users')
def view_users():
    if 'user_role' not in session or session['user_role'] != 'admin':
        flash('Unauthorized access.', "danger")
        return redirect(url_for('login_page'))

    users = User.query.all()
    user_bookings = {}

    for user in users:
        booking = Booking.query.filter_by(user_id=user.id, end_time=None).first()
        if booking:
            spot = booking.spot
            lot_name = spot.lot.name if spot and spot.lot else "Unknown Lot"
            lot_id = spot.lot.id if spot and spot.lot else "Unknown Lot"
            spot_number = spot.spotnumber if spot else "Unknown Spot"
            user_bookings[user.id] = {
                "spot_number": spot_number,
                "lot_name": lot_name,
                "lot_id": lot_id
            }
        else:
            user_bookings[user.id] = {
                "spot_number": "No Active Booking",
                "lot_name": "-",
                "lot_id": "-"
            }

    return render_template('view_users.html', users=users, user_bookings=user_bookings)






if __name__ == '__main__':
    app.run(debug=True)
