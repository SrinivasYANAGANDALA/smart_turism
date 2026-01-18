from flask import Blueprint, render_template, redirect, url_for, request, flash
from flask_login import login_user, logout_user, login_required
from app.models import User, TouristStatus, EmergencyContact
from app.extensions import db, login_manager
import hashlib
from datetime import datetime, timedelta
from app.utils import send_email

auth_bp = Blueprint('auth', __name__)

@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))

@auth_bp.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        # Basic information
        name = request.form['name']
        email = request.form['email']
        username = request.form['username']
        password = request.form['password']
        
        # KYC and safety information
        kyc_type = request.form.get('kyc_type', '')
        kyc_id = request.form.get('kyc_id', '')
        visit_duration = int(request.form.get('visit_duration', 7))
        preferred_language = request.form.get('preferred_language', 'en')
        destination_area = request.form.get('destination_area', '')
        
        # Emergency contact information
        emergency_contact_name = request.form.get('emergency_contact_name', '')
        emergency_contact_number = request.form.get('emergency_contact_number', '')
        emergency_relationship = request.form.get('emergency_relationship', '')
        emergency_email = request.form.get('emergency_email', '')
        
        # Safety preferences
        agree_safety = bool(request.form.get('agree_safety'))
        agree_tracking = bool(request.form.get('agree_tracking'))

        # Validation
        if User.query.filter_by(email=email).first():
            flash('Email already registered.', 'danger')
            return redirect(url_for('auth.register'))
            
        if User.query.filter_by(username=username).first():
            flash('Username already taken.', 'danger')
            return redirect(url_for('auth.register'))
        
        # Generate Digital Tourist ID if KYC provided
        digital_id = username
        if kyc_type and kyc_id:
            digital_id = generate_digital_tourist_id(kyc_id, name)
        
        # Set ID validity period
        id_valid_until = datetime.utcnow() + timedelta(days=visit_duration)
        
        # Create user with enhanced safety fields
        new_user = User(
            name=name,
            email=email,
            username=digital_id,
            kyc_type=kyc_type,
            kyc_id=kyc_id,
            emergency_contact_name=emergency_contact_name,
            emergency_contact_number=emergency_contact_number,
            id_valid_until=id_valid_until,
            preferred_language=preferred_language,
            role='tourist',
            safety_score=100.0,
            is_real_time_tracking_enabled=agree_tracking,
            check_in_location=destination_area,
            expected_checkout_date=id_valid_until
        )
        new_user.set_password(password)
        
        try:
            db.session.add(new_user)
            db.session.flush()  # Get the user ID
            
            # Create detailed emergency contact if provided
            if emergency_contact_name and emergency_contact_number:
                emergency_contact = EmergencyContact(
                    user_id=new_user.id,
                    name=emergency_contact_name,
                    relationship=emergency_relationship or 'emergency',
                    phone_number=emergency_contact_number,
                    email=emergency_email,
                    priority_level=1,
                    is_active=True,
                    notification_preferences='both'
                )
                db.session.add(emergency_contact)
            
            # Initialize tourist status
            tourist_status = TouristStatus(
                user_id=new_user.id,
                current_status='active',
                priority_level='normal',
                expected_checkin_time=datetime.utcnow() + timedelta(hours=24),
                created_at=datetime.utcnow()
            )
            db.session.add(tourist_status)
            
            db.session.commit()
            
            # ✅ SEND SINGLE REGISTRATION EMAIL (FIXED)
            subject = "✅ Welcome to SafeTrip - Registration Successful"
            body = (
                f"Hi {name},\n\n"
                f"🎉 Your SafeTrip account is ready!\n\n"
                f"Login ID: {digital_id}\n"
                f"Email: {email}\n"
                f"Destination: {destination_area}\n"
                f"Valid until: {id_valid_until.strftime('%Y-%m-%d')}\n\n"
                f"✅ SOS button, real-time tracking, and emergency alerts are active.\n"
                f"Safe travels!"
            )
            try:
                send_email(subject, [email], body)
                print(f"✅ Registration email sent to {email}")
            except Exception as e:
                print(f"❌ Registration email failed: {e}")
            
            # Success message based on registration type
            if kyc_type and kyc_id:
                flash(
                    f'🆔 Digital Tourist ID "{digital_id}" created successfully! '
                    f'Your account includes enhanced safety features. Please login to continue.',
                    'success'
                )
            else:
                flash(
                    'Registration successful! '
                    'Consider adding KYC information in your profile for enhanced safety features.',
                    'success'
                )
            
            return redirect(url_for('auth.login'))
            
        except Exception as e:
            db.session.rollback()
            flash('Registration failed. Please try again.', 'danger')
            print(f"Registration error: {e}")  # For debugging
            
    return render_template('register.html')

def generate_digital_tourist_id(kyc_id, name):
    """Generate blockchain-style digital tourist ID"""
    timestamp = str(int(datetime.utcnow().timestamp()))
    data = f"{kyc_id}{name}{timestamp}"
    hash_object = hashlib.sha256(data.encode())
    return f"DT{hash_object.hexdigest()[:12].upper()}"

@auth_bp.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        email = request.form.get('email')
        password = request.form.get('password')
        login_type = request.form.get('login_type', 'tourist')  # Get login type
        remember_me = request.form.get('remember_me')
        
        user = User.query.filter_by(email=email).first()
        
        if user and user.check_password(password):
            # Verify user role matches login type
            if login_type == 'admin' and user.role != 'admin':
                flash('Access denied. Admin credentials required.', 'danger')
                return render_template('login.html')
            elif login_type == 'tourist' and user.role == 'admin':
                flash('Please use Admin login for administrator accounts.', 'warning')
                return render_template('login.html')
            
            login_user(user, remember=bool(remember_me))
            
            # Redirect based on role
            if user.role == 'admin':
                flash(f'Welcome back, {user.name}! Admin panel ready.', 'success')
                return redirect(url_for('dashboard.admin_dashboard'))
            else:
                flash(f'Welcome back, {user.name}!', 'success')
                return redirect(url_for('dashboard.show_dashboard'))
        else:
            flash('Invalid email or password. Please try again.', 'danger')
    
    return render_template('login.html')

@auth_bp.route('/logout')
@login_required  
def logout():
    logout_user()
    flash('You have been logged out safely. Thank you for using our Smart Tourist Safety System!', 'info')
    return redirect(url_for('main_bp.logout'))
