from flask import Blueprint, render_template, request, redirect, url_for, flash
from flask_login import login_user, logout_user, login_required, current_user
from app.models import User
from app.extensions import db

main_bp = Blueprint('main_bp', __name__)

@main_bp.route('/')
def home():
    """Renders the home page."""
    return render_template('home.html')

@main_bp.route('/register', methods=['GET', 'POST'])
def register():
    """Handles user registration."""
    if request.method == 'POST':
        name = request.form.get('name')
        email = request.form.get('email')
        password = request.form.get('password')

        # Check if user with this email already exists
        if User.query.filter_by(email=email).first():
            flash('Email already registered.', 'danger')
            return redirect(url_for('main_bp.register'))

        # Create new user and add to database
        user = User(name=name, email=email)
        user.set_password(password) # Hash the password
        db.session.add(user)
        db.session.commit()
        flash('Registration successful. Please login.', 'success')
        return redirect(url_for('main_bp.login'))

    return render_template('register.html')

@main_bp.route('/login', methods=['GET', 'POST'])
def login():
    """Handles user login."""
    if request.method == 'POST':
        email = request.form.get('email')
        password = request.form.get('password')
        user = User.query.filter_by(email=email).first()

        # Authenticate user
        if user and user.check_password(password):
            login_user(user) # Log the user in with Flask-Login
            flash('Login successful.', 'success')
            # Redirect to the dashboard after successful login
            return redirect(url_for('dashboard.show_dashboard'))
        else:
            flash('Invalid email or password.', 'danger')
            return redirect(url_for('main_bp.login'))

    return render_template('login.html')

@main_bp.route('/logout')
@login_required
def logout():
    """Logs out the current user."""
    logout_user() # Log the user out with Flask-Login
    flash('You have been logged out.', 'info')
    return render_template('logout.html') # Redirect to the logout confirmation page, which will have a link back to home
