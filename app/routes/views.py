from flask import Blueprint, render_template, redirect, url_for, session
from app.services.smartapi_service import get_session

views_bp = Blueprint('views', __name__)

def check_auth():
    if 'session_id' not in session:
        return False
    # Optional: Check if session exists in memory
    # if not get_session(session['session_id']):
    #     return False
    return True

@views_bp.before_request
def require_login():
    # List of endpoints that don't require login (if any in this blueprint)
    pass

@views_bp.route('/dashboard')
def dashboard():
    if not check_auth():
        return redirect(url_for('auth.index'))
    return render_template('dashboard.html')

@views_bp.route('/view/profile')
def view_profile():
    if not check_auth():
        return redirect(url_for('auth.index'))
    return render_template('view.html', title='Profile', api_endpoint='/api/profile')

@views_bp.route('/view/marketdata')
def view_marketdata():
    if not check_auth():
        return redirect(url_for('auth.index'))
    return render_template('view.html', title='Market Data (NIFTY 50)', api_endpoint='/api/marketdata')

@views_bp.route('/view/rms')
def view_rms():
    if not check_auth():
        return redirect(url_for('auth.index'))
    return render_template('view.html', title='RMS / Funds', api_endpoint='/api/rms')

@views_bp.route('/view/orders')
def view_orders():
    if not check_auth():
        return redirect(url_for('auth.index'))
    return render_template('view.html', title='Order Book', api_endpoint='/api/orders/book')

@views_bp.route('/view/trades')
def view_trades():
    if not check_auth():
        return redirect(url_for('auth.index'))
    return render_template('view.html', title='Trade Book', api_endpoint='/api/orders/trades')

@views_bp.route('/view/optionchain')
def view_optionchain():
    if not check_auth():
        return redirect(url_for('auth.index'))
    return render_template('optionchain.html')

@views_bp.route('/view/scriphelper')
def view_scriphelper():
    if not check_auth():
        return redirect(url_for('auth.index'))
    return render_template('scriphelper.html')

@views_bp.route('/view/user_analysis')
def view_user_analysis():
    if not check_auth():
        return redirect(url_for('auth.index'))
    return render_template('user_analysis.html')
