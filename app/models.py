from werkzeug.security import generate_password_hash, check_password_hash
from flask_login import UserMixin
from app.extensions import db
from datetime import datetime # Import datetime for date fields

class User(db.Model, UserMixin):
    """
    User model for authentication and linking trips.
    Updated to include fields for a secure Digital Tourist ID.
    """
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=False)
    password_hash = db.Column(db.String(128))
    username = db.Column(db.String(80), unique=True, nullable=True)
    profile_image = db.Column(db.String(150), nullable=False, default='default.jpg')
    phone_number = db.Column(db.String(20), nullable=True)
    # New fields for the Smart Tourist Safety system
    kyc_type = db.Column(db.String(50), nullable=True) 
    kyc_id = db.Column(db.String(100), unique=True, nullable=True)
    emergency_contact_name = db.Column(db.String(100), nullable=True)
    emergency_contact_number = db.Column(db.String(20), nullable=True)
    emergency_contact_email = db.Column(db.String(120), nullable=True)
    
    id_valid_until = db.Column(db.DateTime, nullable=True)
    safety_score = db.Column(db.Float, default=0.0)
    is_real_time_tracking_enabled = db.Column(db.Boolean, default=False)
    role = db.Column(db.String(50), default='tourist')
    preferred_language = db.Column(db.String(10), default='en')
    
    # Additional safety fields
    check_in_location = db.Column(db.String(200), nullable=True)
    expected_checkout_date = db.Column(db.DateTime, nullable=True)
    device_id = db.Column(db.String(100), nullable=True)  # For mobile app identification
    
    # Relationships
    trips = db.relationship('Trip', backref='user', lazy=True)
    
    def set_password(self, password):
        """Hashes the password and stores it."""
        self.password_hash = generate_password_hash(password)
    
    def check_password(self, password):
        """Checks if the provided password matches the hashed password."""
        return check_password_hash(self.password_hash, password)
    
    def __repr__(self):
        return f'<User {self.email}>'
# Add this to the end of your models.py file
class SOSAlert(db.Model):
    """Store SOS/Panic button alerts"""
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    location_lat = db.Column(db.Float, nullable=True)
    location_lng = db.Column(db.Float, nullable=True)
    message = db.Column(db.Text, nullable=True)
    timestamp = db.Column(db.DateTime, default=datetime.utcnow)
    status = db.Column(db.String(20), default='active')  # active, resolved, false_alarm
    
    # Relationship
    user = db.relationship('User', backref='sos_alerts')
    
    def __repr__(self):
        return f'<SOSAlert {self.id}: {self.user.name} at {self.timestamp}>'

class Trip(db.Model):
    """
    Trip model to store main trip details.
    """
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(150), nullable=False)
    destination = db.Column(db.String(150), nullable=False)
    start_date = db.Column(db.String(20), nullable=False)
    end_date = db.Column(db.String(20), nullable=False)
    budget = db.Column(db.Float, default=0.0)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    # Safety-related fields
    risk_assessment = db.Column(db.String(20), default='low')  # low, medium, high
    is_high_risk_area = db.Column(db.Boolean, default=False)
    requires_guide = db.Column(db.Boolean, default=False)
    
    # Relationships
    itinerary_items = db.relationship('ItineraryItem', backref='trip', lazy=True)
    trip_note = db.relationship('TripNote', backref='trip', uselist=False, lazy=True)
    packing_items = db.relationship('PackingItem', backref='trip', lazy=True)
    
    def __repr__(self):
        return f'<Trip {self.title}>'

class ItineraryItem(db.Model):
    """
    Model for storing individual itinerary items for a trip.
    """
    id = db.Column(db.Integer, primary_key=True)
    trip_id = db.Column(db.Integer, db.ForeignKey('trip.id'), nullable=False)
    date = db.Column(db.Date, nullable=False)
    time = db.Column(db.String(10), nullable=True)
    description = db.Column(db.Text, nullable=False)
    
    def __repr__(self):
        return f'<ItineraryItem {self.description} on {self.date} for Trip {self.trip_id}>'

class TripNote(db.Model):
    """
    Model for storing notes associated with a specific trip.
    """
    id = db.Column(db.Integer, primary_key=True)
    trip_id = db.Column(db.Integer, db.ForeignKey('trip.id'), unique=True, nullable=False)
    content = db.Column(db.Text, nullable=True)
    
    def __repr__(self):
        return f'<TripNote for Trip {self.trip_id}>'

class PackingItem(db.Model):
    """
    Model for storing individual packing list items associated with a specific trip.
    """
    id = db.Column(db.Integer, primary_key=True)
    trip_id = db.Column(db.Integer, db.ForeignKey('trip.id'), nullable=False)
    item_name = db.Column(db.String(100), nullable=False)
    is_packed = db.Column(db.Boolean, default=False)
    is_ai_generated = db.Column(db.Boolean, default=False)  # FIXED: Added missing field
    
    def __repr__(self):
        return f'<PackingItem {self.item_name} for Trip {self.trip_id}>'

# Enhanced Safety System Models
class SafetyAlert(db.Model):
    """
    Model for logging all safety-related incidents and alerts.
    """
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    alert_type = db.Column(db.String(50), nullable=False) # e.g., 'Panic', 'Geo-fence', 'Anomaly'
    timestamp = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)
    latitude = db.Column(db.Float, nullable=False)
    longitude = db.Column(db.Float, nullable=False)
    status = db.Column(db.String(50), default='pending') # e.g., 'Pending', 'Acknowledged', 'Resolved'
    details = db.Column(db.Text, nullable=True)
    
    # Enhanced fields for better tracking
    severity_level = db.Column(db.String(20), default='medium')  # low, medium, high, critical
    response_time = db.Column(db.Integer, nullable=True)  # Response time in minutes
    assigned_officer_id = db.Column(db.Integer, db.ForeignKey('authority_user.id'), nullable=True)
    resolution_notes = db.Column(db.Text, nullable=True)
    
    # Relationship to the User who triggered the alert
    user = db.relationship('User', backref='safety_alerts', lazy=True)
    assigned_officer = db.relationship('AuthorityUser', backref='handled_alerts', lazy=True)
    
    def __repr__(self):
        return f'<SafetyAlert {self.alert_type} for User {self.user_id} at {self.timestamp}>'

class LocationHistory(db.Model):
    """
    Model for real-time tracking, used for AI anomaly detection and historical data.
    """
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    timestamp = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)
    latitude = db.Column(db.Float, nullable=False)
    longitude = db.Column(db.Float, nullable=False)
    
    # Enhanced location tracking fields
    accuracy = db.Column(db.Float, nullable=True)  # GPS accuracy in meters
    altitude = db.Column(db.Float, nullable=True)
    speed = db.Column(db.Float, nullable=True)  # Speed in m/s
    battery_level = db.Column(db.Integer, nullable=True)  # Device battery percentage
    is_manual_checkin = db.Column(db.Boolean, default=False)  # Manual vs automatic location
    
    # Relationship to the User
    user = db.relationship('User', backref='location_history', lazy=True)
    
    def __repr__(self):
        return f'<LocationHistory for User {self.user_id} at {self.timestamp}>'

class IoTDevice(db.Model):
    """
    Model for storing information about wearable devices and IoT sensors.
    """
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    device_type = db.Column(db.String(50), nullable=False) # e.g., 'Smart Band', 'GPS Tag', 'Panic Button'
    serial_number = db.Column(db.String(100), unique=True, nullable=False)
    is_active = db.Column(db.Boolean, default=True)
    
    # Enhanced IoT fields
    battery_level = db.Column(db.Integer, default=100)
    last_heartbeat = db.Column(db.DateTime, nullable=True)
    firmware_version = db.Column(db.String(20), nullable=True)
    assigned_date = db.Column(db.DateTime, default=datetime.utcnow)
    return_date = db.Column(db.DateTime, nullable=True)
    
    # Relationship to the User
    user = db.relationship('User', backref='iot_devices', lazy=True)
    
    def __repr__(self):
        return f'<IoTDevice {self.serial_number} for User {self.user_id}>'

# New Models for Enhanced Safety System
class AuthorityUser(db.Model):
    """
    Model for police and tourism department officials.
    """
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=False)
    password_hash = db.Column(db.String(128))
    employee_id = db.Column(db.String(50), unique=True, nullable=False)
    
    # Authority-specific fields
    department = db.Column(db.String(50), nullable=False)  # 'police', 'tourism', 'emergency'
    rank = db.Column(db.String(50), nullable=True)
    station_id = db.Column(db.String(50), nullable=True)
    jurisdiction_area = db.Column(db.String(200), nullable=True)
    contact_number = db.Column(db.String(20), nullable=False)
    
    # Access control
    is_active = db.Column(db.Boolean, default=True)
    access_level = db.Column(db.String(20), default='officer')  # officer, supervisor, admin
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    last_login = db.Column(db.DateTime, nullable=True)
    
    def set_password(self, password):
        """Hashes the password and stores it."""
        self.password_hash = generate_password_hash(password)
    
    def check_password(self, password):
        """Checks if the provided password matches the hashed password."""
        return check_password_hash(self.password_hash, password)
    
    def __repr__(self):
        return f'<AuthorityUser {self.name} - {self.department}>'

class GeoFence(db.Model):
    """
    Model for defining geo-fenced areas and their risk levels.
    """
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    description = db.Column(db.Text, nullable=True)
    
    # Geographic boundaries
    center_latitude = db.Column(db.Float, nullable=False)
    center_longitude = db.Column(db.Float, nullable=False)
    radius = db.Column(db.Float, nullable=False)  # Radius in meters
    
    # Risk and access control
    risk_level = db.Column(db.String(20), default='medium')  # low, medium, high, restricted
    zone_type = db.Column(db.String(30), default='general')  # tourist_zone, restricted, emergency, medical
    access_permissions = db.Column(db.String(100), default='all')  # all, guided_only, restricted
    
    # Administrative fields
    is_active = db.Column(db.Boolean, default=True)
    created_by = db.Column(db.Integer, db.ForeignKey('authority_user.id'), nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Alert settings
    send_entry_alert = db.Column(db.Boolean, default=True)
    send_exit_alert = db.Column(db.Boolean, default=False)
    alert_message = db.Column(db.Text, nullable=True)
    
    created_by_user = db.relationship('AuthorityUser', backref='created_geofences', lazy=True)
    
    def __repr__(self):
        return f'<GeoFence {self.name} - {self.risk_level}>'

class TouristStatus(db.Model):
    """
    Model for tracking current status of tourists in the system.
    """
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False, unique=True)
    
    # Current status tracking
    current_status = db.Column(db.String(20), default='active')  # active, missing, found, emergency, inactive
    last_location_update = db.Column(db.DateTime, nullable=True)
    last_seen_latitude = db.Column(db.Float, nullable=True)
    last_seen_longitude = db.Column(db.Float, nullable=True)
    
    # Assignment and case management
    assigned_officer_id = db.Column(db.Integer, db.ForeignKey('authority_user.id'), nullable=True)
    case_number = db.Column(db.String(50), nullable=True, unique=True)
    priority_level = db.Column(db.String(20), default='normal')  # low, normal, high, critical
    
    # Timestamps
    status_changed_at = db.Column(db.DateTime, default=datetime.utcnow)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Additional tracking fields
    missed_checkins = db.Column(db.Integer, default=0)
    last_checkin_time = db.Column(db.DateTime, nullable=True)
    expected_checkin_time = db.Column(db.DateTime, nullable=True)
    
    # Relationships
    user = db.relationship('User', backref='status_record', uselist=False, lazy=True)
    assigned_officer = db.relationship('AuthorityUser', backref='assigned_tourists', lazy=True)
    
    def __repr__(self):
        return f'<TouristStatus User:{self.user_id} Status:{self.current_status}>'

class EmergencyContact(db.Model):
    """
    Model for storing multiple emergency contacts for tourists.
    """
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    
    # Contact information
    name = db.Column(db.String(100), nullable=False)
    relationship = db.Column(db.String(50), nullable=False)  # family, friend, colleague, etc.
    phone_number = db.Column(db.String(20), nullable=False)
    email = db.Column(db.String(120), nullable=True)
    address = db.Column(db.Text, nullable=True)
    
    # Priority and preferences
    priority_level = db.Column(db.Integer, default=1)  # 1 = primary, 2 = secondary, etc.
    is_active = db.Column(db.Boolean, default=True)
    notification_preferences = db.Column(db.String(50), default='both')  # sms, email, both, call
    
    # Timestamps
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationship
    user = db.relationship('User', backref='emergency_contacts', lazy=True)
    
    def __repr__(self):
        return f'<EmergencyContact {self.name} for User {self.user_id}>'

class IncidentReport(db.Model):
    """
    Model for detailed incident reporting and case management.
    """
    id = db.Column(db.Integer, primary_key=True)
    case_number = db.Column(db.String(50), unique=True, nullable=False)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    
    # Incident details
    incident_type = db.Column(db.String(50), nullable=False)  # missing, accident, theft, medical, etc.
    severity = db.Column(db.String(20), default='medium')  # low, medium, high, critical
    status = db.Column(db.String(30), default='open')  # open, investigating, resolved, closed
    
    # Location information
    incident_latitude = db.Column(db.Float, nullable=True)
    incident_longitude = db.Column(db.Float, nullable=True)
    incident_location_description = db.Column(db.Text, nullable=True)
    
    # Case management
    reported_by = db.Column(db.Integer, db.ForeignKey('authority_user.id'), nullable=True)
    assigned_to = db.Column(db.Integer, db.ForeignKey('authority_user.id'), nullable=True)
    incident_description = db.Column(db.Text, nullable=False)
    actions_taken = db.Column(db.Text, nullable=True)
    resolution_notes = db.Column(db.Text, nullable=True)
    
    # Timestamps
    incident_datetime = db.Column(db.DateTime, nullable=False)
    reported_datetime = db.Column(db.DateTime, default=datetime.utcnow)
    resolved_datetime = db.Column(db.DateTime, nullable=True)
    
    # Relationships
    user = db.relationship('User', backref='incident_reports', lazy=True)
    reported_by_officer = db.relationship('AuthorityUser', foreign_keys=[reported_by], backref='reported_incidents', lazy=True)
    assigned_officer = db.relationship('AuthorityUser', foreign_keys=[assigned_to], backref='assigned_incidents', lazy=True)
    
    def __repr__(self):
        return f'<IncidentReport {self.case_number} - {self.incident_type}>'

class SystemConfiguration(db.Model):
    """
    Model for storing system-wide configuration settings.
    """
    id = db.Column(db.Integer, primary_key=True)
    config_key = db.Column(db.String(100), unique=True, nullable=False)
    config_value = db.Column(db.Text, nullable=False)
    config_type = db.Column(db.String(20), default='string')  # string, integer, boolean, json
    description = db.Column(db.Text, nullable=True)
    
    # Administrative fields
    is_active = db.Column(db.Boolean, default=True)
    last_modified_by = db.Column(db.Integer, db.ForeignKey('authority_user.id'), nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    last_modified_by_user = db.relationship('AuthorityUser', backref='config_changes', lazy=True)
    
    def __repr__(self):
        return f'<SystemConfiguration {self.config_key}: {self.config_value}>'
