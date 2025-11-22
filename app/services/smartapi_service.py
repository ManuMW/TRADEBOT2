import os
import pickle
import logging
import uuid
from datetime import datetime, timedelta
from SmartApi import SmartConnect

# Global session manager for SmartApi
_SMARTAPI_SESSIONS = {}
SESSION_FILE = 'sessions.pkl'

def load_sessions():
    global _SMARTAPI_SESSIONS
    try:
        if os.path.exists(SESSION_FILE):
            with open(SESSION_FILE, 'rb') as f:
                _SMARTAPI_SESSIONS = pickle.load(f)
            logging.info(f"Loaded {len(_SMARTAPI_SESSIONS)} persisted sessions")
    except Exception as e:
        logging.error(f"Failed to load sessions: {e}")
        _SMARTAPI_SESSIONS = {}

def save_sessions():
    try:
        with open(SESSION_FILE, 'wb') as f:
            pickle.dump(_SMARTAPI_SESSIONS, f)
        logging.info(f"Saved {len(_SMARTAPI_SESSIONS)} sessions")
    except Exception as e:
        logging.error(f"Failed to save sessions: {e}")

# Initialize sessions on module load
load_sessions()

def get_session(session_id):
    return _SMARTAPI_SESSIONS.get(session_id)

def create_session(clientcode, password, totp, api_key):
    logging.info(f"Attempting login for clientcode={clientcode}")
    smartApi = SmartConnect(api_key)
    
    # Call generateSession and log raw response
    data = smartApi.generateSession(clientcode, password, totp)
    logging.info(f"SmartAPI response type: {type(data)}, content: {data}")
    
    # Check if login was successful
    if not data or (isinstance(data, dict) and data.get('status') == False):
        error_msg = data.get('message', 'Login failed') if isinstance(data, dict) else 'Empty response from SmartAPI'
        logging.error(f"Login rejected for clientcode={clientcode}: {error_msg}")
        return None, error_msg
    
    # Extract tokens and set them explicitly
    tokens = data.get('data', {}) if isinstance(data, dict) else {}
    jwt_token = tokens.get('jwtToken')
    refresh_token = tokens.get('refreshToken')
    feed_token = tokens.get('feedToken')
    
    if jwt_token:
        smartApi.setAccessToken(jwt_token)
        logging.info(f"Set access token for clientcode={clientcode}")
    if refresh_token:
        smartApi.setRefreshToken(refresh_token)
    if feed_token:
        smartApi.setFeedToken(feed_token)
    
    session_id = uuid.uuid4().hex
    _SMARTAPI_SESSIONS[session_id] = {
        'api': smartApi,
        'clientcode': clientcode,
        'tokens': tokens,
        'login_time': datetime.now()
    }
    save_sessions()
    logging.info(f"Login successful for clientcode={clientcode}, session_id={session_id}, tokens extracted")
    return session_id, None

def remove_session(session_id):
    if session_id and session_id in _SMARTAPI_SESSIONS:
        del _SMARTAPI_SESSIONS[session_id]
        save_sessions()
