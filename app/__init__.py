import os
from flask import Flask, session
from dotenv import load_dotenv
from app.extensions import db, migrate, login_manager, mail  # ✅ ADDED mail
import os
basedir = os.path.abspath(os.path.dirname(__file__))
from app.routes.dashboard import dash_bp

# Load environment variables from .env file
load_dotenv()

def create_app():
    """
    Factory function to create and configure the Flask application.
    """
    app = Flask(__name__, template_folder='templates', static_folder='static')

    # Application Configuration
    app.config['SECRET_KEY'] = os.getenv('SECRET_KEY', 'a_very_secret_key_for_dev')
    app.config['SQLALCHEMY_DATABASE_URI'] = os.getenv('DATABASE_URL', 'sqlite:///travelbuddy.db')
    app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
    app.config['OPENROUTER_API_KEY'] = os.getenv("OPENROUTER_API_KEY")
    app.config['OPENWEATHER_API_KEY'] = os.getenv("OPENWEATHER_API_KEY") 
    app.config['UPLOAD_FOLDER'] = os.path.join(basedir, 'app', 'static', 'images', 'profiles')

    # Gmail SMTP settings (from .env)
    app.config['MAIL_SERVER'] = os.getenv("MAIL_SERVER", "smtp.gmail.com")
    app.config['MAIL_PORT'] = int(os.getenv("MAIL_PORT", 587))
    app.config['MAIL_USE_TLS'] = True
    app.config['MAIL_USE_SSL'] = False
    app.config['MAIL_USERNAME'] = os.getenv("MAIL_USERNAME")
    app.config['MAIL_PASSWORD'] = os.getenv("MAIL_PASSWORD")
    app.config['MAIL_DEFAULT_SENDER'] = (
        "TravelBuddy SOS",
        os.getenv("MAIL_USERNAME")
)

    # Configure UPLOAD_FOLDER for file uploads (e.g., trip documents, profile pictures)
    UPLOAD_FOLDER = os.path.join(os.getcwd(), 'uploads')
    os.makedirs(UPLOAD_FOLDER, exist_ok=True) 
    app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER

    # Initialize Flask extensions with the app
    db.init_app(app)
    migrate.init_app(app, db)
    login_manager.init_app(app)
    mail.init_app(app)  # ✅ ADDED THIS LINE - EMAILS NOW WORK!

    @login_manager.user_loader
    def load_user(user_id):
        from app.models import User
        return User.query.get(int(user_id))

    # Import blueprints for routes
    from app.routes.auth import auth_bp
    from app.routes.dashboard import dash_bp
    from app.routes.destination import destination_bp
    from app.routes.trips import trips_bp
    from app.routes.main import main_bp
    from app.routes.safety import safety_bp
    # Register Blueprints

    app.register_blueprint(safety_bp, url_prefix='/safety')
    app.register_blueprint(auth_bp, url_prefix='/auth')
    app.register_blueprint(dash_bp) 
    app.register_blueprint(destination_bp, url_prefix='/destination')
    app.register_blueprint(trips_bp, url_prefix='/trips') 
    app.register_blueprint(main_bp)
    
    


    @app.context_processor
    def inject_user_and_session():
        from flask_login import current_user
        return dict(current_user=current_user, session=session)

    return app
