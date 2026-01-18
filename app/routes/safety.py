from flask import Blueprint, render_template, request, jsonify, flash, redirect, url_for
from flask_login import login_required, current_user
from app.models import SafetyAlert, LocationHistory, GeoFence, TouristStatus
from app.extensions import db
from datetime import datetime, timedelta
import math
from app.utils import send_email

safety_bp = Blueprint('safety', __name__)

# --------------------------------------------------
# SAFETY DASHBOARD
# --------------------------------------------------
@safety_bp.route('/safety_dashboard')
@login_required
def safety_dashboard():
    recent_alerts = SafetyAlert.query.filter_by(user_id=current_user.id)\
        .order_by(SafetyAlert.timestamp.desc()).limit(10).all()

    status = TouristStatus.query.filter_by(user_id=current_user.id).first()

    recent_locations = LocationHistory.query.filter_by(user_id=current_user.id)\
        .order_by(LocationHistory.timestamp.desc()).limit(20).all()

    total_alerts = SafetyAlert.query.filter_by(user_id=current_user.id).count()
    active_alerts = SafetyAlert.query.filter_by(user_id=current_user.id, status='pending').count()

    return render_template(
        'safety_dashboard.html',
        alerts=recent_alerts,
        status=status,
        locations=recent_locations,
        safety_score=current_user.safety_score,
        total_alerts=total_alerts,
        active_alerts=active_alerts
    )

# --------------------------------------------------
# 🚨 PANIC BUTTON (SOS EMAIL SENT HERE)
# --------------------------------------------------
@safety_bp.route('/api/panic_button', methods=['POST'])
@login_required
def panic_button():
    try:
        data = request.get_json()
        latitude = float(data.get('latitude', 0))
        longitude = float(data.get('longitude', 0))
        no_location = data.get('no_location', False)

        alert = SafetyAlert(
            user_id=current_user.id,
            alert_type='Panic',
            latitude=latitude,
            longitude=longitude,
            severity_level='critical',
            status='pending',
            details=f'SOS activated by {current_user.name}'
        )
        db.session.add(alert)

        status = TouristStatus.query.filter_by(user_id=current_user.id).first()
        if status:
            status.current_status = 'emergency'
            status.priority_level = 'critical'
            status.last_seen_latitude = latitude
            status.last_seen_longitude = longitude
            status.status_changed_at = datetime.utcnow()
        else:
            status = TouristStatus(
                user_id=current_user.id,
                current_status='emergency',
                priority_level='critical',
                last_seen_latitude=latitude,
                last_seen_longitude=longitude
            )
            db.session.add(status)

        db.session.commit()

        nearest_station = find_nearest_police_station(latitude, longitude)

        # ✅ SEND SOS EMAIL TO PROFILE EMERGENCY EMAIL
        if current_user.emergency_contact_email:
            location_str = (
                f"Latitude: {latitude}, Longitude: {longitude}"
                if not no_location else "Location not available"
            )

            sos_body = f"""
🚨 EMERGENCY SOS ALERT 🚨

Name: {current_user.name}
Phone: {current_user.phone_number}

📍 Location:
{location_str}

⏰ Time:
{datetime.utcnow().strftime('%Y-%m-%d %H:%M UTC')}

🚓 Nearest Police Station:
{nearest_station['name']}
Contact: {nearest_station['contact']}
Distance: {nearest_station['distance']} km

PLEASE RESPOND IMMEDIATELY.
— TravelBuddy Safety System
"""

            send_email(
                subject="🚨 SOS ALERT - TravelBuddy",
                recipients=[current_user.emergency_contact_email],
                body=sos_body
            )

            print(f"✅ SOS email sent to {current_user.emergency_contact_email}")
        else:
            print("❌ No emergency contact email found")

        return jsonify({
            'success': True,
            'message': 'SOS alert triggered successfully'
        })

    except Exception as e:
        print(f"❌ SOS ERROR: {e}")
        return jsonify({'success': False, 'message': 'SOS failed'}), 500


# --------------------------------------------------
# LOCATION UPDATE
# --------------------------------------------------
@safety_bp.route('/api/location_update', methods=['POST'])
@login_required
def location_update():
    if not current_user.is_real_time_tracking_enabled:
        return jsonify({'error': 'Tracking disabled'}), 403

    try:
        data = request.get_json()
        latitude = float(data.get('latitude'))
        longitude = float(data.get('longitude'))

        location = LocationHistory(
            user_id=current_user.id,
            latitude=latitude,
            longitude=longitude,
            timestamp=datetime.utcnow()
        )
        db.session.add(location)

        status = TouristStatus.query.filter_by(user_id=current_user.id).first()
        if status:
            status.last_location_update = datetime.utcnow()
            status.last_seen_latitude = latitude
            status.last_seen_longitude = longitude

        db.session.commit()

        return jsonify({'success': True})

    except Exception as e:
        print(f"❌ Location error: {e}")
        return jsonify({'success': False}), 500


# --------------------------------------------------
# HELPERS
# --------------------------------------------------
def calculate_distance(lat1, lon1, lat2, lon2):
    R = 6371000
    φ1, φ2 = math.radians(lat1), math.radians(lat2)
    Δφ = math.radians(lat2 - lat1)
    Δλ = math.radians(lon2 - lon1)

    a = math.sin(Δφ / 2) ** 2 + math.cos(φ1) * math.cos(φ2) * math.sin(Δλ / 2) ** 2
    return R * 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))


def find_nearest_police_station(lat, lon):
    return {
        'name': 'Central Police Station',
        'contact': '+91-361-2345678',
        'distance': 2.5
    }
