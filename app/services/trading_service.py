import logging
from datetime import datetime
from queue import Queue

# Global state for trading
ACTIVE_TRADES = {}  # {clientcode: {trade_id: {entry_price, stop_loss, target, quantity, status}}}
DAILY_TRADE_PLAN = {}  # Store generated trade plan
TRADE_PLAN_HISTORY = {}  # {clientcode: [{id, plan, trades, generated_at, selected}]}
AUTO_TRADING_ENABLED = {}  # {clientcode: True/False}
PARSED_TRADE_SETUPS = {}  # {clientcode: [{parsed trade setup}]}
PRICE_MONITOR_THREAD = None
WEBSOCKET_CONNECTIONS = {}  # {clientcode: websocket_instance}
LIVE_PRICE_CACHE = {}  # {symboltoken: {ltp, timestamp}}
MONITORING_INTERVAL = 60  # Seconds
PRICE_UPDATE_QUEUE = Queue()  # Queue for WebSocket price updates
CLOSED_TRADE_EXTREMES = {}  # {clientcode: {symbol: {'high': price, 'low': price}}}
TRAILING_STOPS = {}  # {clientcode: {trade_id: {'initial_sl': X, 'trailing_sl': Y, 'peak_profit_pct': Z}}}
POSITION_ENTRY_TIME = {}  # {clientcode: {trade_id: entry_timestamp}}
TRADE_PATTERN_STATS = {}  # {clientcode: {pattern_type: {wins, losses, pnl}}}

def get_time_of_day_adjustment():
    """
    Time-of-Day Volatility Adjustment
    Returns: (sl_multiplier, target_multiplier, description)
    """
    now = datetime.now()
    current_time = now.time()
    
    # Define time windows
    opening_start = now.replace(hour=9, minute=15).time()
    opening_end = now.replace(hour=10, minute=30).time()
    midday_end = now.replace(hour=14, minute=0).time()
    closing_start = now.replace(hour=14, minute=0).time()
    
    if opening_start <= current_time < opening_end:
        # 09:15-10:30: High volatility opening
        return (1.25, 1.15, "OPENING_VOLATILITY")  # Wider SL, higher targets
    elif current_time < midday_end:
        # 10:30-14:00: Mid-day calm
        return (0.85, 1.0, "MIDDAY_CALM")  # Tighter SL, standard targets
    elif closing_start <= current_time:
        # 14:00-15:30: Closing rush
        return (1.1, 1.05, "CLOSING_RUSH")  # Medium SL, quick exits
    
    return (1.0, 1.0, "STANDARD")

def adjust_position_size_by_greeks(base_quantity, delta):
    """
    Greeks-Based Position Sizing - Adjust based on Delta
    Returns: adjusted_quantity
    """
    try:
        if delta is None or delta == 0:
            return base_quantity
        
        abs_delta = abs(delta)
        
        if abs_delta > 0.7:  # Deep ITM - acts like stock
            multiplier = 0.7  # Reduce to 70%
            reason = f"High Delta ({abs_delta:.2f}) - reduced size"
        elif abs_delta < 0.3:  # Deep OTM - risky
            multiplier = 0.5  # Reduce to 50%
            reason = f"Low Delta ({abs_delta:.2f}) - very OTM, reduced size"
        else:  # Sweet spot 0.3-0.7
            multiplier = 1.0
            reason = f"Good Delta ({abs_delta:.2f}) - standard size"
        
        adjusted = int(base_quantity * multiplier)
        logging.info(f"💎 GREEKS SIZING: {reason} | {base_quantity} → {adjusted}")
        
        return adjusted
        
    except Exception as e:
        logging.error(f"Greeks sizing error: {e}")
        return base_quantity

def update_trailing_stop(clientcode, trade_id, current_price, entry_price, current_sl):
    """
    Dynamic Trailing Stop Loss
    Returns: new_stop_loss
    """
    global TRAILING_STOPS
    
    try:
        if clientcode not in TRAILING_STOPS:
            TRAILING_STOPS[clientcode] = {}
        
        if trade_id not in TRAILING_STOPS[clientcode]:
            TRAILING_STOPS[clientcode][trade_id] = {
                'initial_sl': current_sl,
                'trailing_sl': current_sl,
                'peak_profit_pct': 0
            }
        
        trade_trail = TRAILING_STOPS[clientcode][trade_id]
        
        # Calculate profit percentage
        profit_pct = ((current_price - entry_price) / entry_price) * 100
        
        # Update peak profit
        if profit_pct > trade_trail['peak_profit_pct']:
            trade_trail['peak_profit_pct'] = profit_pct
        
        # Trailing stop logic
        new_sl = trade_trail['trailing_sl']
        
        if profit_pct >= 30:  # At +30% profit
            new_sl = entry_price * 1.15  # Trail to +15%
            reason = "Profit 30%+ → Trail SL to +15%"
        elif profit_pct >= 20:  # At +20% profit
            new_sl = entry_price * 1.10  # Trail to +10%
            reason = "Profit 20%+ → Trail SL to +10%"
        elif profit_pct >= 10:  # At +10% profit
            new_sl = entry_price  # Move to breakeven
            reason = "Profit 10%+ → SL to breakeven"
        else:
            new_sl = trade_trail['initial_sl']
            reason = "Profit <10% → Keep initial SL"
        
        # Only update if new SL is higher (never lower stop loss)
        if new_sl > trade_trail['trailing_sl']:
            trade_trail['trailing_sl'] = new_sl
            logging.info(f"[UP] TRAILING STOP: Trade {trade_id} | {reason} | New SL: Rs.{new_sl:.2f}")
            return new_sl
        
        return trade_trail['trailing_sl']
        
    except Exception as e:
        logging.error(f"Trailing stop error: {e}")
        return current_sl

def check_time_based_profit_taking(clientcode, trade_id, entry_time, current_profit_pct):
    """
    Time-Based Profit Taking - Book if stagnant
    Returns: (should_exit: bool, reason: str)
    """
    global POSITION_ENTRY_TIME
    
    try:
        now = datetime.now()
        
        if clientcode not in POSITION_ENTRY_TIME:
            POSITION_ENTRY_TIME[clientcode] = {}
        
        if trade_id not in POSITION_ENTRY_TIME[clientcode]:
            POSITION_ENTRY_TIME[clientcode][trade_id] = {
                'entry_time': entry_time,
                'last_profit_update': now,
                'last_profit_pct': current_profit_pct
            }
        
        trade_time = POSITION_ENTRY_TIME[clientcode][trade_id]
        time_open = (now - trade_time['entry_time']).total_seconds() / 60  # minutes
        
        # Check if profit has changed
        if abs(current_profit_pct - trade_time['last_profit_pct']) > 1:  # Changed by 1%+
            trade_time['last_profit_update'] = now
            trade_time['last_profit_pct'] = current_profit_pct
        
        time_since_profit_change = (now - trade_time['last_profit_update']).total_seconds() / 60
        
        # Time-based exit conditions
        if time_open >= 45 and current_profit_pct > 0:  # Open 45+ min with profit
            if time_since_profit_change >= 20:  # Stagnant for 20 min
                return (True, f"[TIME] TIME EXIT: Stagnant {time_since_profit_change:.0f}min (Theta decay)")
        
        # Approaching close with profit
        if now.hour >= 15 and now.minute >= 0 and current_profit_pct > 5:  # After 3 PM
            return (True, f"[TIME] CLOSING: Book {current_profit_pct:.1f}% before 3:30 PM")
        
        return (False, f"Time OK (open {time_open:.0f}min)")
        
    except Exception as e:
        logging.error(f"Time-based profit taking error: {e}")
        return (False, f"Time check error: {str(e)}")

def track_trade_pattern_performance(clientcode, pattern_type, is_win, pnl):
    """
    Track win rate by setup type
    """
    global TRADE_PATTERN_STATS
    
    if clientcode not in TRADE_PATTERN_STATS:
        TRADE_PATTERN_STATS[clientcode] = {}
    
    if pattern_type not in TRADE_PATTERN_STATS[clientcode]:
        TRADE_PATTERN_STATS[clientcode][pattern_type] = {
            'wins': 0,
            'losses': 0,
            'total_pnl': 0,
            'win_rate': 0
        }
    
    stats = TRADE_PATTERN_STATS[clientcode][pattern_type]
    
    if is_win:
        stats['wins'] += 1
    else:
        stats['losses'] += 1
    
    stats['total_pnl'] += pnl
    total_trades = stats['wins'] + stats['losses']
    stats['win_rate'] = (stats['wins'] / total_trades * 100) if total_trades > 0 else 0
    
    logging.info(f"[STATS] PATTERN [{pattern_type}]: WR {stats['win_rate']:.0f}% ({stats['wins']}W/{stats['losses']}L) | P&L Rs.{stats['total_pnl']:,.0f}")

def get_best_performing_patterns(clientcode, min_trades=5):
    """Get highest win rate patterns"""
    global TRADE_PATTERN_STATS
    
    if clientcode not in TRADE_PATTERN_STATS:
        return []
    
    patterns = []
    for pattern, stats in TRADE_PATTERN_STATS[clientcode].items():
        total = stats['wins'] + stats['losses']
        if total >= min_trades:
            patterns.append({
                'pattern': pattern,
                'win_rate': stats['win_rate'],
                'total_trades': total,
                'pnl': stats['total_pnl']
            })
    
    patterns.sort(key=lambda x: x['win_rate'], reverse=True)
    return patterns
