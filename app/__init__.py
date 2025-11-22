from flask import Flask
from dotenv import load_dotenv
from datetime import timedelta
from app.database import init_db
from app.utils.helpers import setup_logging
from app.routes.auth import auth_bp
from app.routes.views import views_bp
from app.routes.api import api_bp

def create_app():
    # Load environment variables
    load_dotenv()
    
    # Setup logging
    setup_logging()
    
    # Initialize database
    init_db()
    
    app = Flask(__name__, 
                template_folder='../templates',
                static_folder='../static')
    
    app.secret_key = 'replace_this_with_a_secure_key'
    app.permanent_session_lifetime = timedelta(days=1)
    
    # Register Blueprints
    app.register_blueprint(auth_bp)
    app.register_blueprint(views_bp)
    app.register_blueprint(api_bp, url_prefix='/api')
    
    return app
