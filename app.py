from flask import Flask, render_template, request, redirect, url_for, flash, session, jsonify
from flask_sqlalchemy import SQLAlchemy
from datetime import datetime, time, date as py_date
import os

app = Flask(__name__)
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///' + os.path.join(app.instance_path, 'parking.db')
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
app.config['SECRET_KEY'] = 'secret-key-for-parking-app'

# Ensure instance folder exists
os.makedirs(os.path.join(app.root_path, 'instance'), exist_ok=True)

db = SQLAlchemy(app)

# Models
class Bay(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    bay_number = db.Column(db.String(10), unique=True, nullable=False)
    priority_dept = db.Column(db.String(20), nullable=False)  # 'ITSM' or 'QA'

class Booking(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    bay_id = db.Column(db.Integer, db.ForeignKey('bay.id'), nullable=False)
    user_name = db.Column(db.String(100), nullable=False)
    user_dept = db.Column(db.String(20), nullable=False)
    date = db.Column(db.Date, nullable=False, default=lambda: datetime.now().date())
    is_provisional = db.Column(db.Boolean, default=False)  # True if booked in other dept's priority bay

    bay = db.relationship('Bay', backref=db.backref('bookings', lazy=True))

def init_db():
    with app.app_context():
        db.create_all()
        if Bay.query.count() == 0:
            # 4 ITSM, 3 QA
            bays = [
                Bay(bay_number='84', priority_dept='ITSM'),
                Bay(bay_number='85', priority_dept='ITSM'),
                Bay(bay_number='86', priority_dept='ITSM'),
                Bay(bay_number='17', priority_dept='ITSM'),
                Bay(bay_number='18', priority_dept='QA'),
                Bay(bay_number='19', priority_dept='QA'),
                Bay(bay_number='20', priority_dept='QA'),
            ]
            db.session.bulk_save_objects(bays)
            db.session.commit()

# Helper Functions
def is_within_booking_window():
    now = datetime.now()
    if now.weekday() >= 5:  # Saturday or Sunday
        return False
    booking_start = time(6, 0)
    booking_end = time(17, 0)
    return booking_start <= now.time() <= booking_end

def get_current_bookings():
    today = datetime.now().date()
    return Booking.query.filter_by(date=today).all()

# Routes
@app.route('/')
def index():
    if 'user_name' not in session or 'user_dept' not in session:
        return redirect(url_for('profile'))

    today_val = datetime.now().date()
    all_bays = Bay.query.all()
    bookings = {b.bay_id: b for b in get_current_bookings()}

    # Department summary
    dept_summary = {
        'ITSM': {'booked': 0, 'total': 4},
        'QA': {'booked': 0, 'total': 3}
    }
    for b in bookings.values():
        if not b.is_provisional:
            dept_summary[b.bay.priority_dept]['booked'] += 1
        else:
            # If it's provisional, it counts towards the user's department's usage of priority slots?
            # Actually BRD says "a department can only book into the other department's priority bays once it has used up all of its own priority bays for that day."
            # So if a QA user books an ITSM bay, they must have already used 3 QA bays.
            pass

    return render_template('index.html', bays=all_bays, bookings=bookings,
                           dept_summary=dept_summary, is_open=is_within_booking_window(), today=today_val)

@app.route('/book/<int:bay_id>', methods=['POST'])
def book(bay_id):
    if not is_within_booking_window():
        flash("Booking window is 6 AM - 5 PM, Mon-Fri.", "error")
        return redirect(url_for('index'))

    if 'user_name' not in session:
        return redirect(url_for('profile'))

    user_name = session['user_name']
    user_dept = session['user_dept']
    today = datetime.now().date()

    bay = Bay.query.get_or_404(bay_id)
    existing_booking = Booking.query.filter_by(bay_id=bay_id, date=today).first()

    if existing_booking:
        if existing_booking.is_provisional and existing_booking.bay.priority_dept == user_dept:
            # This should not happen if logic is correct, but let's handle it.
            # If a bay is priority for user_dept but marked provisional, it's weird.
            # More likely: it's priority for OTHER dept, and held provisionally by OTHER dept.
            pass

        if existing_booking.is_provisional and existing_booking.user_dept != user_dept and bay.priority_dept == user_dept:
            # BUMPING LOGIC
            db.session.delete(existing_booking)
            new_booking = Booking(bay_id=bay_id, user_name=user_name, user_dept=user_dept, date=today, is_provisional=False)
            db.session.add(new_booking)
            db.session.commit()
            flash(f"You have bumped a provisional booking. Slot {bay.bay_number} is now yours.", "success")
            return redirect(url_for('index'))
        else:
            flash("Slot is already booked.", "error")
            return redirect(url_for('index'))

    # Check if user can book this bay
    if bay.priority_dept == user_dept:
        # User booking their own priority bay
        new_booking = Booking(bay_id=bay_id, user_name=user_name, user_dept=user_dept, date=today, is_provisional=False)
        db.session.add(new_booking)
        db.session.commit()
        flash(f"Slot {bay.bay_number} booked successfully.", "success")
    else:
        # Cross-department booking
        # Check if all user's department priority bays are full
        my_priority_bays = Bay.query.filter_by(priority_dept=user_dept).all()
        my_priority_ids = [b.id for b in my_priority_bays]
        booked_priority_count = Booking.query.filter(Booking.bay_id.in_(my_priority_ids), Booking.date == today).count()

        if booked_priority_count < len(my_priority_bays):
            flash(f"Please book your department's priority slots first.", "error")
        else:
            new_booking = Booking(bay_id=bay_id, user_name=user_name, user_dept=user_dept, date=today, is_provisional=True)
            db.session.add(new_booking)
            db.session.commit()
            flash(f"Slot {bay.bay_number} booked provisionally.", "success")

    return redirect(url_for('index'))

@app.route('/cancel/<int:booking_id>', methods=['POST'])
def cancel(booking_id):
    booking = Booking.query.get_or_404(booking_id)
    # Basic check: only user can cancel their own?
    # Or for now, anyone since no real auth yet.
    db.session.delete(booking)
    db.session.commit()
    flash("Booking cancelled.", "success")
    return redirect(request.referrer or url_for('index'))

@app.route('/profile', methods=['GET', 'POST'])
def profile():
    if request.method == 'POST':
        session['user_name'] = request.form.get('user_name')
        session['user_dept'] = request.form.get('user_dept')
        flash("Profile updated.", "success")
        return redirect(url_for('index'))
    return render_template('profile.html')

@app.route('/bookings')
def bookings():
    if 'user_name' not in session:
        return redirect(url_for('profile'))
    user_name = session['user_name']
    today_val = datetime.now().date()
    # Show all history for this user
    my_bookings = Booking.query.filter_by(user_name=user_name).order_by(Booking.date.desc()).all()
    return render_template('bookings.html', bookings=my_bookings, today=today_val)

@app.route('/admin')
def admin_login():
    return render_template('admin_login.html')

@app.route('/admin/dashboard')
def admin_dashboard():
    all_bookings = Booking.query.order_by(Booking.date.desc()).all()
    bays = Bay.query.all()
    return render_template('admin_dashboard.html', bookings=all_bookings, bays=bays)

if __name__ == '__main__':
    init_db()
    app.run(debug=True, port=5001) # Changed port to avoid conflicts if any
