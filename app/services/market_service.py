import logging
import json
import requests
from datetime import datetime, timedelta
from app.services.smartapi_service import _SMARTAPI_SESSIONS

# Global state for market data
VIX_CACHE = {'value': None, 'timestamp': None}
VIX_HISTORY = []  # List of (timestamp, vix_value) tuples
SCRIP_MASTER_CACHE = {}

def get_current_vix_value():
    """Get current INDIA VIX value from SmartAPI with 5-minute caching"""
    global VIX_CACHE, VIX_HISTORY
    
    try:
        # Check cache first (5 minute expiry)
        if VIX_CACHE['value'] and VIX_CACHE['timestamp']:
            age = (datetime.now() - VIX_CACHE['timestamp']).total_seconds()
            if age < 300:  # 5 minutes
                return VIX_CACHE['value']
        
        # Fetch INDIA VIX from SmartAPI (token 99926017)
        # Get any active client for API call
        active_client = None
        for clientcode in _SMARTAPI_SESSIONS:
            if _SMARTAPI_SESSIONS[clientcode].get('active'):
                active_client = _SMARTAPI_SESSIONS[clientcode]['api']
                break
        
        if not active_client:
            logging.warning("No active SmartAPI session for VIX fetch")
            return None
        
        # Fetch India VIX using LTP quote
        # Note: SmartAPI ltpData takes exchange, tradingsymbol, symboltoken
        vix_data = active_client.ltpData("NSE", "India VIX", "99926017")
        
        if vix_data and vix_data.get('status') and vix_data.get('data'):
            current_vix = float(vix_data['data']['ltp'])
            VIX_CACHE = {
                'value': current_vix,
                'timestamp': datetime.now()
            }
            
            # Store in history for momentum calculation
            VIX_HISTORY.append((datetime.now(), current_vix))
            # Keep only last 60 minutes of data
            VIX_HISTORY = [(ts, val) for ts, val in VIX_HISTORY 
                          if (datetime.now() - ts).total_seconds() < 3600]
            
            logging.info(f"[VIX] Fetched from SmartAPI: {current_vix:.2f}")
            return current_vix
        
        return None
        
    except Exception as e:
        logging.error(f"Error fetching VIX from SmartAPI: {e}")
        return None

def get_vix_momentum():
    """
    Calculate VIX momentum/slope from recent history
    Returns: ('rising', 'falling', 'stable', 'unknown')
    """
    global VIX_HISTORY
    
    if len(VIX_HISTORY) < 3:
        return 'unknown'
    
    try:
        # Get last 3 VIX values
        recent = VIX_HISTORY[-3:]
        values = [v for _, v in recent]
        
        # Calculate simple slope
        first_val = values[0]
        last_val = values[-1]
        change_pct = ((last_val - first_val) / first_val) * 100
        
        if change_pct > 2:
            return 'rising'
        elif change_pct < -2:
            return 'falling'
        else:
            return 'stable'
            
    except Exception as e:
        logging.error(f"VIX momentum calculation error: {e}")
        return 'unknown'

def detect_market_regime(vix_value, trend_strength):
    """
    Detect current market regime
    Returns: (regime, confidence, strategy_recommendation)
    """
    try:
        if vix_value > 25:
            return ('high_vol', 0.9, "Wider stops, bigger targets, reduce size")
        elif vix_value < 12:
            return ('low_vol', 0.9, "Tighter stops, quicker exits")
        elif trend_strength > 70:
            return ('trending', 0.8, "Trade with trend, let winners run")
        else:
            return ('choppy', 0.7, "Quick scalps, tight stops, selective")
            
    except Exception as e:
        logging.error(f"Market regime detection error: {e}")
        return ('unknown', 0, "Use standard strategy")

def check_trend_direction(candles_data):
    """
    Check trend direction using EMA crossover
    Returns: ('bullish', 'bearish', 'neutral')
    """
    try:
        if not candles_data or len(candles_data) < 21:
            return 'neutral'
        
        closes = [float(c[4]) for c in candles_data[-21:]]
        
        # Calculate EMA9 and EMA21
        ema9 = closes[-9:]
        ema21 = closes
        
        ema9_val = sum(ema9) / len(ema9)
        ema21_val = sum(ema21) / len(ema21)
        
        if ema9_val > ema21_val * 1.002:
            return 'bullish'
        elif ema9_val < ema21_val * 0.998:
            return 'bearish'
        else:
            return 'neutral'
            
    except Exception as e:
        logging.error(f"Trend direction check error: {e}")
        return 'neutral'

def calculate_vix_based_thresholds(vix_value):
    """Calculate trailing SL thresholds based on VIX"""
    if vix_value is None:
        return {'breakeven_threshold': 15.0, 'trail_threshold': 25.0}
    
    if vix_value < 12:
        return {'breakeven_threshold': 10.0, 'trail_threshold': 15.0}
    elif vix_value < 15:
        return {'breakeven_threshold': 15.0, 'trail_threshold': 25.0}
    elif vix_value < 20:
        return {'breakeven_threshold': 20.0, 'trail_threshold': 40.0}
    elif vix_value < 25:
        return {'breakeven_threshold': 30.0, 'trail_threshold': 65.0}
    else:
        return {'breakeven_threshold': 40.0, 'trail_threshold': 80.0}

def calculate_vix_based_profit_target(vix_value):
    """Calculate profit target - FIXED AT 10%"""
    return 10.0

def check_volume_confirmation(symboltoken, clientcode):
    """Volume Confirmation - Placeholder"""
    return (True, "Volume check pending (needs historical data API)", 1.0)

def check_breakout_confirmation(clientcode, symbol, current_price, breakout_level, direction='bullish'):
    """Breakout Confirmation"""
    try:
        buffer = breakout_level * 0.002  # 0.2% buffer
        
        if direction == 'bullish' and current_price > (breakout_level + buffer):
            return (True, f"[OK] Breakout confirmed: {current_price:.0f} > {breakout_level:.0f}")
        elif direction == 'bearish' and current_price < (breakout_level - buffer):
            return (True, f"[OK] Breakdown confirmed: {current_price:.0f} < {breakout_level:.0f}")
        else:
            return (False, f"Waiting for clear break (need 0.2% buffer)")
            
    except Exception as e:
        logging.error(f"Breakout confirmation error: {e}")
        return (True, f"Breakout check error: {str(e)}")

def check_multi_timeframe_confirmation(symbol='NIFTY'):
    """Multi-Timeframe Confirmation - Placeholder"""
    return (True, "Multi-TF check pending (needs multiple interval data)", {})

def calculate_iv_percentile(symbol, strike, expiry, current_iv):
    """IV Percentile Ranking - Placeholder"""
    return (50, "IV ranking pending (needs 30-day IV history database)")

def calculate_support_resistance_levels(candles_data):
    """Support/Resistance Levels - Enhanced calculation"""
    try:
        if not candles_data or len(candles_data) < 20:
            return {}
        
        recent_20 = candles_data[-20:]
        highs = [c[2] for c in recent_20]
        lows = [c[3] for c in recent_20]
        closes = [c[4] for c in recent_20]
        
        last_high = recent_20[-1][2]
        last_low = recent_20[-1][3]
        last_close = recent_20[-1][4]
        
        pivot = (last_high + last_low + last_close) / 3
        r1 = 2 * pivot - last_low
        r2 = pivot + (last_high - last_low)
        r3 = r1 + (last_high - last_low)
        s1 = 2 * pivot - last_high
        s2 = pivot - (last_high - last_low)
        s3 = s1 - (last_high - last_low)
        
        swing_high = max(highs)
        swing_low = min(lows)
        diff = swing_high - swing_low
        
        fib_levels = {
            'fib_0': swing_high,
            'fib_23.6': swing_high - (diff * 0.236),
            'fib_38.2': swing_high - (diff * 0.382),
            'fib_50': swing_high - (diff * 0.5),
            'fib_61.8': swing_high - (diff * 0.618),
            'fib_100': swing_low
        }
        
        recent_levels = {
            'swing_high': swing_high,
            'swing_low': swing_low,
            'prev_day_high': highs[-2] if len(highs) > 1 else last_high,
            'prev_day_low': lows[-2] if len(lows) > 1 else last_low
        }
        
        return {
            'pivots': {'pivot': pivot, 'r1': r1, 'r2': r2, 'r3': r3, 's1': s1, 's2': s2, 's3': s3},
            'fibonacci': fib_levels,
            'recent': recent_levels
        }
        
    except Exception as e:
        logging.error(f"Support/Resistance calculation error: {e}")
        return {}

def find_symbol_token(tradingsymbol, clientcode):
    """Find symbol token from local scrip master for given trading symbol"""
    global SCRIP_MASTER_CACHE
    try:
        if tradingsymbol in SCRIP_MASTER_CACHE:
            return SCRIP_MASTER_CACHE[tradingsymbol]
        
        scrip_master_path = 'scrip_master.json'
        
        try:
            with open(scrip_master_path, 'r', encoding='utf-8') as f:
                scrip_data = json.load(f)
            
            logging.info(f"Loaded {len(scrip_data)} symbols from scrip master")
            
            tradingsymbol_upper = tradingsymbol.upper()
            
            # Exact match
            for item in scrip_data:
                if item.get('symbol', '').upper() == tradingsymbol_upper or item.get('name', '').upper() == tradingsymbol_upper:
                    if item.get('exch_seg') == 'NFO':
                        token = item.get('token')
                        result = {
                            'token': token,
                            'symbol': item.get('symbol'),
                            'name': item.get('name'),
                            'expiry': item.get('expiry'),
                            'strike': item.get('strike'),
                            'lotsize': item.get('lotsize')
                        }
                        SCRIP_MASTER_CACHE[tradingsymbol] = result
                        logging.info(f"Found token for {tradingsymbol}: {token}")
                        return result
            
            # Partial match
            for item in scrip_data:
                symbol = item.get('symbol', '').upper()
                if tradingsymbol_upper in symbol and item.get('exch_seg') == 'NFO':
                    token = item.get('token')
                    result = {
                        'token': token,
                        'symbol': item.get('symbol'),
                        'name': item.get('name'),
                        'expiry': item.get('expiry'),
                        'strike': item.get('strike'),
                        'lotsize': item.get('lotsize')
                    }
                    SCRIP_MASTER_CACHE[tradingsymbol] = result
                    logging.info(f"Found token for {tradingsymbol}: {token} (partial match: {symbol})")
                    return result
            
            logging.error(f"Could not find token for {tradingsymbol} in scrip master")
            return None
            
        except FileNotFoundError:
            logging.error(f"Scrip master file not found: {scrip_master_path}")
            return None
        
    except Exception as e:
        logging.error(f"Error finding symbol token: {e}", exc_info=True)
        return None

def get_market_quotes_batch(clientcode, exchange_tokens, mode='FULL'):
    """Fetch market quotes for multiple symbols in ONE API call"""
    try:
        session_id = None
        for sid, sdata in _SMARTAPI_SESSIONS.items():
            if sdata.get('clientcode') == clientcode:
                session_id = sid
                break
        
        if not session_id:
            logging.error(f"No session found for {clientcode}")
            return None
        
        smartapi = _SMARTAPI_SESSIONS[session_id]['api']
        jwt_token = _SMARTAPI_SESSIONS[session_id]['tokens'].get('jwtToken', '')
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
            "mode": mode,
            "exchangeTokens": exchange_tokens
        }
        
        response = requests.post(url, headers=headers, json=payload, timeout=5)
        data = response.json()
        
        if data.get('status') and data.get('data'):
            return data['data']
        else:
            logging.error(f"Batch quote fetch failed: {data.get('message')}")
            return None
            
    except Exception as e:
        logging.error(f"Error fetching batch quotes: {e}")
        return None

def check_liquidity_filter(symboltoken, clientcode, min_oi=5000):
    """
    Check option liquidity via Historical OI Data API.
    """
    try:
        # Placeholder - allow trade until API integrated
        return (True, "OI check pending (API integration needed)", 0)
    except Exception as e:
        logging.error(f"Liquidity filter error: {e}")
        return (True, f"OI check error: {str(e)}", 0)

def check_spread_filter(symboltoken, clientcode, max_spread_pct=3.0):
    """
    Check bid-ask spread - reject if > 3% (bad liquidity)
    """
    try:
        # In production: Fetch bid/ask from market depth
        # For now, simulate spread check
        spread_pct = 1.5  # Placeholder (typical ATM spread)
        
        if spread_pct > max_spread_pct:
            return (False, f"🚫 SPREAD: {spread_pct:.1f}% > {max_spread_pct}% (poor execution)", spread_pct)
        
        return (True, f"Spread OK ({spread_pct:.1f}%)", spread_pct)
    except:
        return (True, "Spread check skipped", 0.0)
