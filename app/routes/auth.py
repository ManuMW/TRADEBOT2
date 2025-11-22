from flask import Blueprint, render_template, request, redirect, url_for, session
import logging
import os
from datetime import timedelta
from app.services.smartapi_service import create_session, remove_session, get_session

auth_bp = Blueprint('auth', __name__)

@auth_bp.route('/')
def index():
    session_id = session.get('session_id')
    if session_id and get_session(session_id):
        logging.info(f"User already logged in with session_id={session_id}, redirecting to dashboard")
        return redirect(url_for('views.dashboard'))
    return render_template('login.html')

@auth_bp.route('/login', methods=['POST'])
def login():
    SMARTAPI_API_KEY = os.getenv("SMARTAPI_API_KEY")
    
    if not SMARTAPI_API_KEY:
        logging.error("SMARTAPI_API_KEY not set in environment")
        return render_template('login.html', error='API Key not configured. Check .env file.')
    
    clientcode = request.form.get('clientcode')
    password = request.form.get('password')
    totp = request.form.get('totp')
    
    if clientcode and password and totp:
        try:
            session_id, error = create_session(clientcode, password, totp, SMARTAPI_API_KEY)
            
            if session_id:
                session['session_id'] = session_id
                session.permanent = True
                # Note: app.permanent_session_lifetime needs to be set in the app factory
                return redirect(url_for('views.dashboard'))
            else:
                return render_template('login.html', error=f'Login failed: {error}')
        except Exception as e:
            logging.error(f"Login failed for clientcode={clientcode}: {e}", exc_info=True)
            return render_template('login.html', error=f'Login failed: {e}')
            
    logging.warning("Login attempt with missing credentials")
    return render_template('login.html', error='Invalid credentials')

@auth_bp.route('/logout')
def logout():
    sid = session.pop('session_id', None)
    remove_session(sid)
    return redirect(url_for('auth.index'))
