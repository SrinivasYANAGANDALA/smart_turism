from flask import Blueprint, render_template, request, jsonify
from flask_login import login_required, current_user
from app.models import SafetyAlert, TouristStatus, User, LocationHistory
from datetime import datetime, timedelta

authority_bp = Blueprint('authority', __name__)

@authority_bp.route('/authority_dashboard')
@login_required
def authority_dashboard():
    """Dashboard for police and tourism officials"""
    
    # Only allow authority users (you can add role checking)
    if current_user.role != 'authority':
        flash('Access denied. Authority access required.', 'danger')
        return redirect(url_for('dashboard.show_dashboard'))
    
    # Statistics
    stats = {
        'total_tourists': User.query.filter_by(role='tourist').count(),
        'active_tourists': TouristStatus.query.filter_by(current_status='active').count(),
        'emergency_cases': TouristStatus.query.filter_by(current_status='emergency').count(),
        'pending_alerts': SafetyAlert.query.filter_by(status='pending').count()
    }
    
    # Recent alerts
    recent_alerts = SafetyAlert.query.filter(
        SafetyAlert.timestamp >= datetime.utcnow() - timedelta(hours=24)
    ).order_by(SafetyAlert.timestamp.desc()).limit(20).all()
    
    return render_template('authority_dashboard.html',
                         stats=stats,
                         recent_alerts=recent_alerts)

@authority_bp.route('/tourist_details/<int:user_id>')
@login_required
def tourist_details(user_id):
    """Detailed tourist information for authorities"""
    if current_user.role != 'authority':
        flash('Access denied.', 'danger')
        return redirect(url_for('dashboard.show_dashboard'))
    
    tourist = User.query.get_or_404(user_id)
    status = TouristStatus.query.filter_by(user_id=user_id).first()
    
    alerts = SafetyAlert.query.filter_by(user_id=user_id)\
                             .order_by(SafetyAlert.timestamp.desc()).all()
    
    return render_template('tourist_details.html',
                         tourist=tourist,
                         status=status,
                         alerts=alerts)

@authority_bp.route('/api/heat_map')
@login_required
def heat_map_data():
    """API for tourist location heat map"""
    recent_locations = LocationHistory.query.filter(
        LocationHistory.timestamp >= datetime.utcnow() - timedelta(hours=6)
    ).all()
    
    data = [{
        'lat': loc.latitude,
        'lng': loc.longitude,
        'intensity': 1
    } for loc in recent_locations]
    
    return jsonify(data)
