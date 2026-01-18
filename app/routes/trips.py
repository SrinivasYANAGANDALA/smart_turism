from flask import Blueprint, render_template, request, redirect, url_for, flash
from flask_login import login_required, current_user
from datetime import datetime, timedelta

from app.models import db, Trip
from app.utils import send_email

trips_bp = Blueprint('trips', __name__)

# --------------------------------------------------
# DASHBOARD
# --------------------------------------------------
@trips_bp.route('/dashboard')
@login_required
def dashboard():
    trips = Trip.query.filter_by(user_id=current_user.id).order_by(Trip.start_date).all()
    next_trip = trips[0] if trips else None

    return render_template(
        'dashboard.html',
        user=current_user,
        trips=trips,
        next_trip=next_trip
    )

# --------------------------------------------------
# CREATE TRIP  ✅ EMAIL
# --------------------------------------------------
@trips_bp.route('/trip/new', methods=['GET', 'POST'])
@login_required
def create_trip():
    if request.method == 'POST':
        try:
            title = request.form['title']
            destination = request.form['destination']
            start_date = datetime.strptime(request.form['start_date'], '%Y-%m-%d')
            end_date = datetime.strptime(request.form['end_date'], '%Y-%m-%d')
            budget = float(request.form['budget'])

            new_trip = Trip(
                title=title,
                destination=destination,
                start_date=start_date,
                end_date=end_date,
                budget=budget,
                user_id=current_user.id
            )

            db.session.add(new_trip)
            db.session.commit()

            email_body = f"""
✈️ TRIP CREATED SUCCESSFULLY!

Hello {current_user.name},

Your trip has been successfully created in TravelBuddy.

🧳 TRIP DETAILS
Title: {title}
Destination: {destination}
Dates: {start_date.strftime('%Y-%m-%d')} → {end_date.strftime('%Y-%m-%d')}
Budget: ₹{budget}

🛡️ SAFETY FEATURES ACTIVE
• SOS Emergency Button
• Emergency Contact Alerts
• Real-time Location Tracking

We’ll notify you again when your trip date is near.

Have a safe and happy journey 🌍
— TravelBuddy Safety Team
"""

            send_email(
                subject="✈️ Trip Created - TravelBuddy",
                recipients=[current_user.email],
                body=email_body
            )

            flash("Trip created successfully! Email sent.", "success")
            return redirect(url_for('trips.dashboard'))

        except Exception as e:
            db.session.rollback()
            print("❌ CREATE TRIP ERROR:", e)
            flash("Failed to create trip.", "danger")

    return render_template('create_trip.html')

# --------------------------------------------------
# EDIT TRIP  ✅ EMAIL
# --------------------------------------------------
@trips_bp.route('/trip/edit/<int:trip_id>', methods=['GET', 'POST'])
@login_required
def edit_trip(trip_id):
    trip = Trip.query.get_or_404(trip_id)

    if trip.user_id != current_user.id:
        flash("Unauthorized access.", "danger")
        return redirect(url_for('trips.dashboard'))

    if request.method == 'POST':
        try:
            trip.title = request.form['title']
            trip.destination = request.form['destination']
            trip.start_date = datetime.strptime(request.form['start_date'], '%Y-%m-%d')
            trip.end_date = datetime.strptime(request.form['end_date'], '%Y-%m-%d')
            trip.budget = float(request.form['budget'])

            db.session.commit()

            email_body = f"""
✏️ TRIP UPDATED

Hello {current_user.name},

Your trip details have been successfully updated.

🧳 UPDATED TRIP DETAILS
Title: {trip.title}
Destination: {trip.destination}
Dates: {trip.start_date.strftime('%Y-%m-%d')} → {trip.end_date.strftime('%Y-%m-%d')}
Budget: ₹{trip.budget}

Please review your updated itinerary before departure.

— TravelBuddy Safety Team
"""

            send_email(
                subject="✏️ Trip Updated - TravelBuddy",
                recipients=[current_user.email],
                body=email_body
            )

            flash("Trip updated successfully. Email sent.", "success")
            return redirect(url_for('trips.dashboard'))

        except Exception as e:
            db.session.rollback()
            print("❌ UPDATE TRIP ERROR:", e)
            flash("Failed to update trip.", "danger")

    return render_template('edit_trip.html', trip=trip)

# --------------------------------------------------
# DELETE TRIP  ✅ EMAIL
# --------------------------------------------------
@trips_bp.route('/trip/delete/<int:trip_id>', methods=['POST'])
@login_required
def delete_trip(trip_id):
    trip = Trip.query.get_or_404(trip_id)

    if trip.user_id != current_user.id:
        flash("Unauthorized access.", "danger")
        return redirect(url_for('trips.dashboard'))

    try:
        email_body = f"""
🗑️ TRIP DELETED

Hello {current_user.name},

Your trip has been removed from TravelBuddy.

🧳 TRIP DETAILS
Title: {trip.title}
Destination: {trip.destination}
Dates: {trip.start_date.strftime('%Y-%m-%d')} → {trip.end_date.strftime('%Y-%m-%d')}

If this was a mistake, you can create a new trip anytime.

— TravelBuddy Safety Team
"""

        send_email(
            subject="🗑️ Trip Deleted - TravelBuddy",
            recipients=[current_user.email],
            body=email_body
        )

        db.session.delete(trip)
        db.session.commit()

        flash("Trip deleted successfully. Email sent.", "success")

    except Exception as e:
        db.session.rollback()
        print("❌ DELETE TRIP ERROR:", e)
        flash("Failed to delete trip.", "danger")

    return redirect(url_for('trips.dashboard'))

# --------------------------------------------------
# TRIP START REMINDER (CALL DAILY / CRON)
# --------------------------------------------------
def send_trip_start_reminders():
    """
    Call this function once per day (cron / scheduler)
    Sends reminder email 1 day before trip start
    """
    tomorrow = datetime.utcnow().date() + timedelta(days=1)

    trips = Trip.query.filter(
        Trip.start_date >= tomorrow,
        Trip.start_date < tomorrow + timedelta(days=1)
    ).all()

    for trip in trips:
        user = trip.user

        email_body = f"""
⏰ TRIP STARTING SOON!

Hello {user.name},

Your trip is starting tomorrow.

🧳 TRIP DETAILS
Title: {trip.title}
Destination: {trip.destination}
Start Date: {trip.start_date.strftime('%Y-%m-%d')}

🛡️ Safety Reminder:
• Keep SOS button ready
• Ensure emergency contact is updated
• Carry important documents

Have a safe journey 🌍
— TravelBuddy Safety Team
"""

        send_email(
            subject="⏰ Trip Starting Tomorrow - TravelBuddy",
            recipients=[user.email],
            body=email_body
        )
