from flask import Blueprint, jsonify, request, session
import requests
import logging
import os
from datetime import datetime, timedelta
from app.services.smartapi_service import get_session
from app.database import store_data

api_bp = Blueprint('api', __name__)

def get_valid_session():
    session_id = session.get('session_id')
    if not session_id:
        return None
    return get_session(session_id)

@api_bp.route('/marketdata')
def marketdata():
    user_session = get_valid_session()
    if not user_session:
        logging.warning("Marketdata access without valid session")
        return jsonify({'status': False, 'message': 'Not logged in'}), 401
    
    smartApi = user_session['api']
    jwt_token = user_session['tokens'].get('jwtToken', '')
    if jwt_token.startswith('Bearer '):
        jwt_token = jwt_token[7:]
        
    url = "https://apiconnect.angelone.in/rest/secure/angelbroking/market/v1/quote/"
    headers = {
        'Authorization': f'Bearer {jwt_token}',
        'Content-Type': 'application/json',
        'Accept': 'application/json',
        'X-UserType': 'USER',
        'X-SourceID': 'WEB',
        'X-ClientLocalIP': 'CLIENT_LOCAL_IP',
        'X-ClientPublicIP': 'CLIENT_PUBLIC_IP',
        'X-MACAddress': 'MAC_ADDRESS',
        'X-PrivateKey': os.getenv('SMARTAPI_API_KEY')
    }
    payload = {
        "mode": "FULL",
        "exchangeTokens": {"NSE": ["99926000"]}
    }
    try:
        r = requests.post(url, json=payload, headers=headers, timeout=10)
        data = r.json()
        # Store in database
        clientcode = user_session['clientcode']
        store_data(clientcode, '/api/marketdata', 'marketdata', data)
    except Exception as e:
        logging.error(f"Marketdata error: {e}")
        return jsonify({'status': False, 'message': str(e)}), 500
        
    summary = {}
    buy_depth = []
    sell_depth = []
    try:
        fetched = data.get('data', {}).get('fetched', [])
        if fetched:
            md = fetched[0]
            summary = {
                "ltp": md.get("ltp"),
                "netChange": md.get("netChange"),
                "percentChange": md.get("percentChange"),
                "open": md.get("open"),
                "high": md.get("high"),
                "low": md.get("low"),
                "close": md.get("close"),
                "tradeVolume": md.get("tradeVolume"),
                "exchFeedTime": md.get("exchFeedTime"),
                "exchTradeTime": md.get("exchTradeTime"),
                "upperCircuit": md.get("upperCircuit"),
                "lowerCircuit": md.get("lowerCircuit"),
            }
            buy_depth = md.get("depth", {}).get("buy", [])
            sell_depth = md.get("depth", {}).get("sell", [])
    except Exception:
        pass
    return jsonify({
        "status": True,
        "summary": summary,
        "buy_depth": buy_depth,
        "sell_depth": sell_depth,
        "raw": data
    })

@api_bp.route('/marketdata/custom', methods=['POST'])
def marketdata_custom():
    user_session = get_valid_session()
    if not user_session:
        logging.warning("Custom marketdata access without valid session")
        return jsonify({'status': False, 'message': 'Not logged in'}), 401
    
    jwt_token = user_session['tokens'].get('jwtToken', '')
    if jwt_token.startswith('Bearer '):
        jwt_token = jwt_token[7:]
    
    url = "https://apiconnect.angelone.in/rest/secure/angelbroking/market/v1/quote/"
    headers = {
        'Authorization': f'Bearer {jwt_token}',
        'Content-Type': 'application/json',
        'Accept': 'application/json',
        'X-UserType': 'USER',
        'X-SourceID': 'WEB',
        'X-ClientLocalIP': 'CLIENT_LOCAL_IP',
        'X-ClientPublicIP': 'CLIENT_PUBLIC_IP',
        'X-MACAddress': 'MAC_ADDRESS',
        'X-PrivateKey': os.getenv('SMARTAPI_API_KEY')
    }
    
    payload = request.get_json()
    if not payload:
        return jsonify({'status': False, 'message': 'Invalid request body'}), 400
    
    try:
        logging.info(f"Custom market data request: {payload}")
        r = requests.post(url, json=payload, headers=headers, timeout=10)
        data = r.json()
        logging.info(f"Custom market data response: success={data.get('status')}")
    except Exception as e:
        logging.error(f"Custom marketdata error: {e}")
        return jsonify({'status': False, 'message': str(e)}), 500
    
    return jsonify(data)

@api_bp.route('/scrip/search', methods=['POST'])
def scrip_search():
    user_session = get_valid_session()
    if not user_session:
        return jsonify({'status': False, 'message': 'Not logged in'}), 401
    
    body = request.get_json() or {}
    symbol = body.get('symbol', 'NIFTY').upper()
    option_type = body.get('option_type', 'CE')
    strike = body.get('strike')
    show_all_expiries = body.get('show_all_expiries', False)
    cache_range = body.get('cache_range', True)
    
    try:
        response = requests.get(
            'https://margincalculator.angelbroking.com/OpenAPI_File/files/OpenAPIScripMaster.json',
            timeout=30
        )
        response.raise_for_status()
        scrips = response.json()
        
        options = [
            s for s in scrips
            if s.get('exch_seg') == 'NFO'
            and s.get('name') == symbol
            and s.get('instrumenttype') == 'OPTIDX'
            and s.get('symbol', '').endswith(option_type)
        ]
        
        if not options:
            return jsonify({
                'status': False,
                'message': f'No {option_type} options found for {symbol} in scrip master'
            })
            
        for opt in options:
            symbol_str = opt.get('symbol', '')
            expiry_str = opt.get('expiry', '')
            
            try:
                expiry_date = datetime.strptime(expiry_str, '%d%b%Y')
                date_part = expiry_date.strftime('%d%b%y').upper()
                
                remaining = symbol_str.replace(symbol, '', 1)
                
                if remaining.endswith('CE'):
                    remaining = remaining[:-2]
                elif remaining.endswith('PE'):
                    remaining = remaining[:-2]
                
                if remaining.startswith(date_part):
                    strike_str = remaining[len(date_part):]
                    opt['parsed_strike'] = float(strike_str) if strike_str.isdigit() else 0.0
                else:
                    opt['parsed_strike'] = 0.0
            except:
                opt['parsed_strike'] = float(opt.get('strike', 0))
        
        today = datetime.now()
        
        for opt in options:
            try:
                expiry_str = opt.get('expiry', '')
                opt['expiry_date'] = datetime.strptime(expiry_str, '%d%b%Y')
                opt['days_to_expiry'] = (opt['expiry_date'] - today).days
            except:
                opt['expiry_date'] = None
                opt['days_to_expiry'] = 9999
        
        options = [o for o in options if o['days_to_expiry'] >= 0]
        options.sort(key=lambda x: (x['days_to_expiry'], x['parsed_strike']))
        
        cached_options = []
        if strike:
            strike_float = float(strike)
            closest_expiry_days = options[0]['days_to_expiry']
            closest_options = [o for o in options if o['days_to_expiry'] == closest_expiry_days]
            all_strikes = sorted(set([o['parsed_strike'] for o in closest_options]))
            
            if strike_float in all_strikes:
                strike_index = all_strikes.index(strike_float)
            else:
                strike_index = min(range(len(all_strikes)), key=lambda i: abs(all_strikes[i] - strike_float))
            
            if cache_range:
                start_idx = max(0, strike_index - 3)
                end_idx = min(len(all_strikes), strike_index + 4)
                cached_strikes = all_strikes[start_idx:end_idx]
                cached_options = [o for o in closest_options if o['parsed_strike'] in cached_strikes]
            else:
                cached_options = [o for o in closest_options if o['parsed_strike'] == all_strikes[strike_index]]
            
            if not cached_options:
                return jsonify({
                    'status': False,
                    'message': f'Strike {strike_float} not found.'
                })
            
            options = cached_options
        
        if options:
            if show_all_expiries:
                result_options = options[:50]
            else:
                closest_expiry_days = options[0]['days_to_expiry']
                result_options = [o for o in options if o['days_to_expiry'] == closest_expiry_days][:50]
            
            result = []
            for opt in result_options:
                result.append({
                    'token': opt.get('token'),
                    'symbol': opt.get('symbol'),
                    'name': opt.get('name'),
                    'strike': opt['parsed_strike'],
                    'expiry': opt.get('expiry'),
                    'days_to_expiry': opt['days_to_expiry'],
                    'lotsize': opt.get('lotsize'),
                    'option_type': option_type
                })
            
            unique_expiries = sorted(set([o['expiry'] for o in options]))
            result_strikes = [o.get('parsed_strike', float(o.get('strike', 0))) for o in result]
            
            return jsonify({
                'status': True,
                'message': f'Found {len(result)} options',
                'data': result,
                'closest_expiry': options[0].get('expiry'),
                'days_to_expiry': options[0]['days_to_expiry'],
                'available_expiries': unique_expiries[:5],
                'strike_range': {
                    'min': min([o.get('parsed_strike', float(o.get('strike', 0))) for o in options]),
                    'max': max([o.get('parsed_strike', float(o.get('strike', 0))) for o in options])
                },
                'cached_strikes': sorted(set(result_strikes)) if strike else None
            })
        else:
            return jsonify({'status': False, 'message': 'No active options found'})
    
    except Exception as e:
        logging.error(f"Scrip search error: {e}", exc_info=True)
        return jsonify({'status': False, 'message': str(e)}), 500

@api_bp.route('/optionchain', methods=['POST'])
def optionchain():
    user_session = get_valid_session()
    if not user_session:
        return jsonify({'status': False, 'message': 'Not logged in'}), 401
    
    smartApi = user_session['api']
    clientcode = user_session['clientcode']
    jwt_token = user_session['tokens'].get('jwtToken', '')
    if jwt_token.startswith('Bearer '):
        jwt_token = jwt_token[7:]
    
    body = request.get_json() or {}
    exchange = body.get('exchange', 'NFO')
    symboltoken = body.get('symboltoken')
    interval = body.get('interval', 'ONE_DAY')
    fromdate = body.get('fromdate')
    todate = body.get('todate')
    
    if not symboltoken:
        return jsonify({'status': False, 'message': 'symboltoken is required'}), 400
    
    if not fromdate or not todate:
        todate = datetime.now().strftime('%Y-%m-%d %H:%M')
        fromdate = (datetime.now() - timedelta(days=7)).strftime('%Y-%m-%d %H:%M')
    
    try:
        headers = {
            'Authorization': f'Bearer {jwt_token}',
            'Content-Type': 'application/json',
            'Accept': 'application/json',
            'X-UserType': 'USER',
            'X-SourceID': 'WEB',
            'X-ClientLocalIP': '',
            'X-ClientPublicIP': '',
            'X-MACAddress': '',
            'X-PrivateKey': smartApi.api_key
        }
        
        payload = {
            "exchange": exchange,
            "symboltoken": symboltoken,
            "interval": interval,
            "fromdate": fromdate,
            "todate": todate
        }
        
        response = requests.post(
            'https://apiconnect.angelone.in/rest/secure/angelbroking/historical/v1/getOIData',
            headers=headers,
            json=payload,
            timeout=10
        )
        
        response.raise_for_status()
        result = response.json()
        store_data(clientcode, '/api/optionchain', 'optionchain', result)
        return jsonify(result)
        
    except Exception as e:
        logging.error(f"Option chain error: {e}")
        return jsonify({'status': False, 'message': str(e)}), 500

@api_bp.route('/profile')
def profile():
    user_session = get_valid_session()
    if not user_session:
        return jsonify({'status': False, 'message': 'Not logged in'}), 401
    
    jwt_token = user_session['tokens'].get('jwtToken', '')
    if jwt_token.startswith('Bearer '):
        jwt_token = jwt_token[7:]
    
    url = "https://apiconnect.angelone.in/rest/secure/angelbroking/user/v1/getProfile"
    headers = {
        'Authorization': f'Bearer {jwt_token}',
        'Content-Type': 'application/json',
        'Accept': 'application/json',
        'X-UserType': 'USER',
        'X-SourceID': 'WEB',
        'X-ClientLocalIP': 'CLIENT_LOCAL_IP',
        'X-ClientPublicIP': 'CLIENT_PUBLIC_IP',
        'X-MACAddress': 'MAC_ADDRESS',
        'X-PrivateKey': os.getenv('SMARTAPI_API_KEY')
    }
    try:
        r = requests.get(url, headers=headers, timeout=10)
        data = r.json()
        clientcode = user_session['clientcode']
        store_data(clientcode, '/api/profile', 'profile', data)
        return jsonify(data)
    except Exception as e:
        logging.error(f"Profile error: {e}")
        return jsonify({'status': False, 'message': str(e)}), 500

@api_bp.route('/rms')
def rms():
    user_session = get_valid_session()
    if not user_session:
        return jsonify({'status': False, 'message': 'Not logged in'}), 401
    
    jwt_token = user_session['tokens'].get('jwtToken', '')
    if jwt_token.startswith('Bearer '):
        jwt_token = jwt_token[7:]
    
    url = "https://apiconnect.angelone.in/rest/secure/angelbroking/user/v1/getRMS"
    headers = {
        'Authorization': f'Bearer {jwt_token}',
        'Content-Type': 'application/json',
        'Accept': 'application/json',
        'X-UserType': 'USER',
        'X-SourceID': 'WEB',
        'X-ClientLocalIP': 'CLIENT_LOCAL_IP',
        'X-ClientPublicIP': 'CLIENT_PUBLIC_IP',
        'X-MACAddress': 'MAC_ADDRESS',
        'X-PrivateKey': os.getenv('SMARTAPI_API_KEY')
    }
    try:
        r = requests.get(url, headers=headers, timeout=10)
        data = r.json()
        clientcode = user_session['clientcode']
        store_data(clientcode, '/api/rms', 'rms', data)
        return jsonify(data)
    except Exception as e:
        logging.error(f"RMS error: {e}")
        return jsonify({'status': False, 'message': str(e)}), 500

@api_bp.route('/orders/book')
def order_book():
    user_session = get_valid_session()
    if not user_session:
        return jsonify({'status': False, 'message': 'Not logged in'}), 401
    
    jwt_token = user_session['tokens'].get('jwtToken', '')
    if jwt_token.startswith('Bearer '):
        jwt_token = jwt_token[7:]
    
    url = 'https://apiconnect.angelone.in/rest/secure/angelbroking/order/v1/getOrderBook'
    headers = {
        'Authorization': f'Bearer {jwt_token}',
        'Content-Type': 'application/json',
        'Accept': 'application/json',
        'X-UserType': 'USER',
        'X-SourceID': 'WEB',
        'X-ClientLocalIP': 'CLIENT_LOCAL_IP',
        'X-ClientPublicIP': 'CLIENT_PUBLIC_IP',
        'X-MACAddress': 'MAC_ADDRESS',
        'X-PrivateKey': os.getenv('SMARTAPI_API_KEY')
    }
    try:
        r = requests.get(url, headers=headers)
        data = r.json()
        clientcode = user_session['clientcode']
        store_data(clientcode, '/api/orders/book', 'orders', data)
        return jsonify(data)
    except Exception as e:
        logging.error(f"Order book error: {e}")
        return jsonify({'status': False, 'message': str(e)}), 500

@api_bp.route('/orders/trades')
def trade_book():
    user_session = get_valid_session()
    if not user_session:
        return jsonify({'status': False, 'message': 'Not logged in'}), 401
    
    jwt_token = user_session['tokens'].get('jwtToken', '')
    if jwt_token.startswith('Bearer '):
        jwt_token = jwt_token[7:]
    
    url = 'https://apiconnect.angelone.in/rest/secure/angelbroking/order/v1/getTradeBook'
    headers = {
        'Authorization': f'Bearer {jwt_token}',
        'Content-Type': 'application/json',
        'Accept': 'application/json',
        'X-UserType': 'USER',
        'X-SourceID': 'WEB',
        'X-ClientLocalIP': 'CLIENT_LOCAL_IP',
        'X-ClientPublicIP': 'CLIENT_PUBLIC_IP',
        'X-MACAddress': 'MAC_ADDRESS',
        'X-PrivateKey': os.getenv('SMARTAPI_API_KEY')
    }
    try:
        r = requests.get(url, headers=headers)
        data = r.json()
        clientcode = user_session['clientcode']
        store_data(clientcode, '/api/orders/trades', 'trades', data)
        return jsonify(data)
    except Exception as e:
        logging.error(f"Trade book error: {e}")
        return jsonify({'status': False, 'message': str(e)}), 500
