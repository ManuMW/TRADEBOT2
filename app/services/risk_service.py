import logging
import os
import requests
from datetime import datetime, timedelta
from app.services.smartapi_service import _SMARTAPI_SESSIONS

# Global state for risk management
DAILY_STATS = {}  # {clientcode: {date: {pnl, trades_count, wins, losses, commissions, slippage}}}
KELLY_MULTIPLIER = {}  # {clientcode: multiplier}
INITIAL_CAPITAL = {}  # {clientcode: starting_capital}
FLASH_CRASH_CACHE = {}  # {clientcode: [price_snapshots]}
OPENING_PRICE_CACHE = {}  # {clientcode: opening_price}
CONSECUTIVE_LOSSES = {}  # {clientcode: count}
PEAK_DAILY_PROFIT = {}  # {clientcode: peak_profit}

def get_available_capital_from_profile(clientcode):
    """Fetch available capital from Angel One RMS API"""
    try:
        # Find session for this client
        session_id = None
        for sid, sdata in _SMARTAPI_SESSIONS.items():
            if sdata.get('clientcode') == clientcode:
                session_id = sid
                break
        
        if not session_id:
            logging.warning(f"No session found for {clientcode}, using default capital")
            return 15000
        
        jwt_token = _SMARTAPI_SESSIONS[session_id]['tokens'].get('jwtToken', '')
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
        
        r = requests.get(url, headers=headers, timeout=10)
        data = r.json()
        
        if data.get('status') and data.get('data'):
            rms_data = data['data']
            available_cash = float(rms_data.get('net', 0))
            
            if available_cash > 0:
                logging.info(f"[CAPITAL] Fetched from RMS for {clientcode}: Rs.{available_cash:,.2f}")
                return available_cash
            else:
                logging.warning(f"RMS returned zero/negative capital for {clientcode}, using default")
                return 15000
        else:
            logging.warning(f"RMS API failed for {clientcode}: {data.get('message', 'Unknown error')}")
            return 15000
            
    except Exception as e:
        logging.error(f"Error fetching capital from RMS for {clientcode}: {e}")
        return 15000

def initialize_daily_stats(clientcode, starting_capital=None):
    """Initialize daily statistics for risk tracking with dynamic capital from RMS"""
    global DAILY_STATS, INITIAL_CAPITAL
    today = datetime.now().date().isoformat()
    
    if starting_capital is None:
        starting_capital = get_available_capital_from_profile(clientcode)
        logging.info(f"[CAPITAL] Using RMS capital: Rs.{starting_capital:,.2f}")
    
    if clientcode not in DAILY_STATS:
        DAILY_STATS[clientcode] = {}
    
    if today not in DAILY_STATS[clientcode]:
        DAILY_STATS[clientcode][today] = {
            'pnl': 0.0,
            'trades_count': 0,
            'wins': 0,
            'losses': 0,
            'commissions': 0.0,
            'slippage': 0.0,
            'starting_capital': starting_capital,
            'gross_profit': 0.0,
            'gross_loss': 0.0,
            'max_drawdown': 0.0,
            'peak_capital': starting_capital
        }
        INITIAL_CAPITAL[clientcode] = starting_capital
        logging.info(f"[STATS] Daily stats initialized for {clientcode}: Capital Rs.{starting_capital:,.0f}")

def check_daily_loss_circuit_breaker(clientcode, loss_limit_pct=10.0):
    global DAILY_STATS, INITIAL_CAPITAL
    today = datetime.now().date().isoformat()
    
    if clientcode not in DAILY_STATS or today not in DAILY_STATS[clientcode]:
        return (True, "No stats available", 0.0)
    
    stats = DAILY_STATS[clientcode][today]
    starting_capital = stats.get('starting_capital', INITIAL_CAPITAL.get(clientcode, 15000))
    current_pnl = stats['pnl']
    loss_pct = (current_pnl / starting_capital) * 100
    
    if loss_pct < -loss_limit_pct:
        return (False, f"[STOP] CIRCUIT BREAKER: Daily loss {loss_pct:.1f}% exceeds limit -{loss_limit_pct}%", loss_pct)
    
    return (True, "Within limits", loss_pct)

def check_max_trades_limit(clientcode, max_trades=10, extended_max=15):
    global DAILY_STATS
    today = datetime.now().date().isoformat()
    
    if clientcode not in DAILY_STATS or today not in DAILY_STATS[clientcode]:
        return (True, "No trades today", 0)
    
    stats = DAILY_STATS[clientcode][today]
    trades_count = stats['trades_count']
    win_rate = stats['wins'] / max(trades_count, 1)
    
    if trades_count >= extended_max:
        return (False, f"[STOP] MAX TRADES: {trades_count}/{extended_max} trades executed today", trades_count)
    elif trades_count >= max_trades and win_rate < 0.6:
        return (False, f"[WARNING] MAX TRADES: {trades_count}/{max_trades} (win rate {win_rate*100:.0f}% < 60%)", trades_count)
    
    return (True, f"Trades: {trades_count}/{extended_max}", trades_count)

def calculate_kelly_position_size(clientcode, base_quantity):
    global DAILY_STATS, KELLY_MULTIPLIER
    today = datetime.now().date().isoformat()
    
    if clientcode not in DAILY_STATS or today not in DAILY_STATS[clientcode]:
        KELLY_MULTIPLIER[clientcode] = 1.0
        return base_quantity
    
    stats = DAILY_STATS[clientcode][today]
    total_trades = stats['trades_count']
    
    if total_trades < 3:
        KELLY_MULTIPLIER[clientcode] = 1.0
        return base_quantity
    
    win_rate = stats['wins'] / total_trades
    
    if win_rate >= 0.65:
        multiplier = 1.3
    elif win_rate >= 0.50:
        multiplier = 1.0
    elif win_rate >= 0.35:
        multiplier = 0.7
    else:
        multiplier = 0.5
    
    KELLY_MULTIPLIER[clientcode] = multiplier
    adjusted_qty = int(base_quantity * multiplier)
    
    logging.info(f"📐 Kelly sizing: Win rate {win_rate*100:.0f}% → Multiplier {multiplier:.1f}x → Qty {adjusted_qty}")
    return adjusted_qty

def check_flash_crash_protection(clientcode, current_price):
    global FLASH_CRASH_CACHE
    
    if clientcode not in FLASH_CRASH_CACHE:
        FLASH_CRASH_CACHE[clientcode] = []
    
    now = datetime.now()
    FLASH_CRASH_CACHE[clientcode].append((now, current_price))
    
    cutoff = now - timedelta(minutes=5)
    FLASH_CRASH_CACHE[clientcode] = [(ts, p) for ts, p in FLASH_CRASH_CACHE[clientcode] if ts > cutoff]
    
    if len(FLASH_CRASH_CACHE[clientcode]) < 2:
        return (True, "Insufficient data", 0.0)
    
    oldest_price = FLASH_CRASH_CACHE[clientcode][0][1]
    move_pct = abs((current_price - oldest_price) / oldest_price) * 100
    
    if move_pct > 2.0:
        return (False, f"[ALERT] FLASH MOVE: NIFTY moved {move_pct:.1f}% in 5 min (pausing)", move_pct)
    
    return (True, f"Normal volatility ({move_pct:.1f}%)", move_pct)

def check_gap_filter(clientcode, current_price):
    global OPENING_PRICE_CACHE
    now = datetime.now()
    
    if now.hour == 9 and 15 <= now.minute <= 20:
        if clientcode not in OPENING_PRICE_CACHE:
            OPENING_PRICE_CACHE[clientcode] = current_price
            logging.info(f"[STATS] Opening price captured: {current_price:.2f}")
    
    if clientcode not in OPENING_PRICE_CACHE:
        return (0.0, "Opening price not yet set")
    
    opening_price = OPENING_PRICE_CACHE[clientcode]
    gap_pct = ((current_price - opening_price) / opening_price) * 100
    
    if abs(gap_pct) > 1.0:
        direction = "GAP UP" if gap_pct > 0 else "GAP DOWN"
        return (gap_pct, f"{direction}: {abs(gap_pct):.1f}% - Momentum bias expected")
    
    return (gap_pct, "Normal opening")

def track_commission(clientcode, num_orders=1, commission_per_order=20):
    global DAILY_STATS
    today = datetime.now().date().isoformat()
    
    if clientcode not in DAILY_STATS:
        DAILY_STATS[clientcode] = {}
    if today not in DAILY_STATS[clientcode]:
        initialize_daily_stats(clientcode, 15000)
    
    total_commission = num_orders * commission_per_order
    DAILY_STATS[clientcode][today]['commissions'] += total_commission
    
    logging.info(f"[MONEY] Commission: Rs.{total_commission} ({num_orders} orders × Rs.{commission_per_order})")
    return total_commission

def update_daily_pnl(clientcode, pnl_change, is_win=None):
    global DAILY_STATS
    today = datetime.now().date().isoformat()
    
    if clientcode not in DAILY_STATS:
        DAILY_STATS[clientcode] = {}
    if today not in DAILY_STATS[clientcode]:
        initialize_daily_stats(clientcode, 15000)
    
    stats = DAILY_STATS[clientcode][today]
    stats['pnl'] += pnl_change
    stats['trades_count'] += 1
    
    if pnl_change > 0:
        stats['gross_profit'] += pnl_change
    else:
        stats['gross_loss'] += abs(pnl_change)
    
    if is_win is True:
        stats['wins'] += 1
    elif is_win is False:
        stats['losses'] += 1
    
    current_capital = stats['starting_capital'] + stats['pnl']
    if current_capital > stats['peak_capital']:
        stats['peak_capital'] = current_capital
    
    drawdown = ((stats['peak_capital'] - current_capital) / stats['peak_capital']) * 100
    if drawdown > stats['max_drawdown']:
        stats['max_drawdown'] = drawdown
    
    win_rate = stats['wins'] / max(stats['trades_count'], 1) * 100
    profit_factor = stats['gross_profit'] / max(stats['gross_loss'], 1)
    
    logging.info(f"[STATS] Daily Stats: P&L Rs.{stats['pnl']:,.0f} | Trades {stats['trades_count']} | WR {win_rate:.0f}% | PF {profit_factor:.2f} | DD {stats['max_drawdown']:.1f}%")

def get_daily_stats_summary(clientcode):
    global DAILY_STATS
    today = datetime.now().date().isoformat()
    
    if clientcode not in DAILY_STATS or today not in DAILY_STATS[clientcode]:
        return None
    
    stats = DAILY_STATS[clientcode][today]
    starting_capital = stats.get('starting_capital', 15000)
    
    return {
        'date': today,
        'pnl': stats['pnl'],
        'pnl_pct': (stats['pnl'] / starting_capital) * 100,
        'trades': stats['trades_count'],
        'wins': stats['wins'],
        'losses': stats['losses'],
        'win_rate': (stats['wins'] / max(stats['trades_count'], 1)) * 100,
        'commissions': stats['commissions'],
        'slippage': stats['slippage'],
        'net_pnl': stats['pnl'] - stats['commissions'] - stats['slippage'],
        'starting_capital': starting_capital
    }

def check_time_based_blocking():
    """
    Check if current time is in blocked trading window
    Block 2:30-3:15 PM (expiry hour chaos)
    """
    now = datetime.now()
    current_time = now.time()
    
    # Block 14:30 to 15:15 (2:30 PM to 3:15 PM)
    block_start = now.replace(hour=14, minute=30, second=0).time()
    block_end = now.replace(hour=15, minute=15, second=0).time()
    
    if block_start <= current_time <= block_end:
        return (False, f"🕐 TIME BLOCK: No new entries during 2:30-3:15 PM (expiry chaos)")
    
    return (True, "Time allowed")

def check_max_open_positions(clientcode, active_trades, max_positions=2):
    """
    Limit open positions
    """
    if not active_trades:
        return (True, "No active trades", 0)
    
    active_count = sum(1 for t in active_trades.values() if t.get('status') == 'open')
    
    if active_count >= max_positions:
        return (False, f"🚫 MAX POSITIONS: Already holding {active_count}/{max_positions} positions", active_count)
    
    return (True, f"Positions: {active_count}/{max_positions}", active_count)

def check_time_decay_filter():
    """
    Avoid buying options after 2 PM (theta decay accelerates)
    """
    now = datetime.now()
    current_time = now.time()
    
    # Block option buying after 14:00 (2:00 PM)
    cutoff_time = now.replace(hour=14, minute=0, second=0).time()
    
    if current_time >= cutoff_time:
        return (False, "[TIME] TIME DECAY: No option buying after 2 PM (theta kills premium)")
    
    return (True, "Time OK for entry")

def check_correlation_filter(clientcode, new_instrument, active_trades):
    """
    Check if holding opposite position (CE + PE simultaneously)
    """
    if not active_trades:
        return (True, "No active trades")
    
    active_instruments = []
    for trade_id, trade in active_trades.items():
        if trade.get('status') == 'open':
            instrument = trade.get('instrument', '')
            active_instruments.append(instrument)
    
    # Check if we're holding opposite side
    new_type = 'CE' if 'CE' in new_instrument else 'PE' if 'PE' in new_instrument else 'unknown'
    
    if new_type == 'CE' and any('PE' in inst for inst in active_instruments):
        return (False, "🚫 CORRELATION: Already holding PE, don't add CE (hedging reduces profit)")
    elif new_type == 'PE' and any('CE' in inst for inst in active_instruments):
        return (False, "🚫 CORRELATION: Already holding CE, don't add PE (hedging reduces profit)")
    
    return (True, "No correlation conflict")

def calculate_slippage(planned_price, actual_price, transaction_type='BUY'):
    """
    Calculate slippage between planned and actual execution price
    """
    if transaction_type == 'BUY':
        # Positive slippage = paid more than planned (bad)
        slippage_pct = ((actual_price - planned_price) / planned_price) * 100
    else:  # SELL
        # Positive slippage = received less than planned (bad)
        slippage_pct = ((planned_price - actual_price) / planned_price) * 100
    
    slippage_amount = actual_price - planned_price
    return slippage_pct, slippage_amount

def check_consecutive_loss_limit(clientcode, max_consecutive=3):
    """
    Stop trading after N consecutive losses
    """
    global CONSECUTIVE_LOSSES
    
    if clientcode not in CONSECUTIVE_LOSSES:
        CONSECUTIVE_LOSSES[clientcode] = 0
    
    streak = CONSECUTIVE_LOSSES[clientcode]
    
    if streak >= max_consecutive:
        return (False, f"[STOP] CONSECUTIVE LOSSES: {streak} losses in a row - PAUSED for emotional protection", streak)
    
    return (True, f"Loss streak: {streak}/{max_consecutive}", streak)

def update_loss_streak(clientcode, is_win):
    """Update consecutive loss counter"""
    global CONSECUTIVE_LOSSES
    
    if clientcode not in CONSECUTIVE_LOSSES:
        CONSECUTIVE_LOSSES[clientcode] = 0
    
    if is_win:
        CONSECUTIVE_LOSSES[clientcode] = 0  # Reset on win
        logging.info(f"[OK] Win! Loss streak reset for {clientcode}")
    else:
        CONSECUTIVE_LOSSES[clientcode] += 1
        logging.warning(f"[FAIL] Loss #{CONSECUTIVE_LOSSES[clientcode]} for {clientcode}")

def check_profit_protect_mode(clientcode):
    """
    Profit Protect Mode - Lock in daily profits
    """
    global PEAK_DAILY_PROFIT, DAILY_STATS
    
    today = datetime.now().date().isoformat()
    
    if clientcode not in DAILY_STATS or today not in DAILY_STATS[clientcode]:
        return (0, 0, "NO_PROFIT_YET")
    
    current_pnl = DAILY_STATS[clientcode][today]['pnl']
    
    # Track peak profit
    if clientcode not in PEAK_DAILY_PROFIT:
        PEAK_DAILY_PROFIT[clientcode] = 0
    
    if current_pnl > PEAK_DAILY_PROFIT[clientcode]:
        PEAK_DAILY_PROFIT[clientcode] = current_pnl
    
    peak = PEAK_DAILY_PROFIT[clientcode]
    
    # Profit protect rules
    if peak >= 5000:  # If made Rs.5000+ today
        drawdown_from_peak = peak - current_pnl
        drawdown_pct = (drawdown_from_peak / peak) * 100 if peak > 0 else 0
        
        if drawdown_pct > 40:  # Given back 40% of peak profit
            return (peak * 0.6, 100, "STOP_TRADING")  # Stop for the day
        elif drawdown_pct > 25:  # Given back 25%
            return (peak * 0.75, 50, "REDUCE_RISK")  # Reduce position sizes by 50%
        elif peak >= 5000:
            return (peak, 30, "PROTECT_MODE")  # Only risk 30% of profits
    
    return (0, 0, "NORMAL")

