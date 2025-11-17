# Quick Reference - New Trading Features

## [TARGET] IMMEDIATE IMPACT FEATURES

### 1. Trailing Stop Loss
**What**: Automatically moves stop loss upward as profit increases  
**When**: +10% profit → SL to breakeven, +20% → SL to +10%, +30% → SL to +15%  
**Why**: Locks in profits without manual intervention  
**Watch For**: Log entries like `[TRAIL SL] Moved SL: Rs.115 → Rs.120 (22% profit)`

### 2. Time-of-Day Adjustments
**What**: Changes SL/target distances based on time  
**When**: Opening (9:15-10:30) = wider stops, Midday (10:30-14:00) = tighter stops  
**Why**: Opening has 2x volatility vs midday  
**Watch For**: Log entries like `[TIME] TIME PHASE: OPENING_VOLATILITY | SL×1.25 | Target×1.15`

### 3. Consecutive Loss Protection
**What**: Stops trading after 3 losses in a row  
**When**: Automatically after 3rd loss  
**Why**: Prevents emotional revenge trading  
**Watch For**: `[WARNING] Consecutive losses: 3/3 - PAUSING TRADING`

### 4. Profit Protect Mode
**What**: Reduces risk after making Rs.5,000+ profit  
**When**: Automatically when daily profit hits Rs.5,000  
**Why**: Don't give back big gains  
**Watch For**: `[STOP] PROFIT PROTECT: REDUCE_RISK mode (drawback 25%)`

### 5. 3-Tier Partial Exits
**What**: Closes position in 3 steps instead of 2  
**When**: Target 1 (33%), Target 2 (33%), Final (34%)  
**Why**: Smoother profit taking, better average exit price  
**Watch For**: `[3-TIER SCALE] TARGET_1: Closed 25/75 lots (33%)`

---

## [STATS] MONITORING NEW FEATURES

### Check Trailing Stops Are Working:
```bash
# Look for these log entries:
[TRAIL SL] Moved SL to breakeven at 10.5% profit
[TRAIL SL] VIX-based trailing: Rs.115 → Rs.125 (21% profit)
```

### Check Time-of-Day Adjustments:
```bash
# Opening session should show wider stops:
[TIME] TIME PHASE: OPENING_VOLATILITY | SL×1.25 | Target×1.15
Adjusted SL: Rs.110 → Rs.115 (wider for volatility)

# Midday should show tighter stops:
[TIME] TIME PHASE: MIDDAY_CALM | SL×0.85 | Target×1.0
Adjusted SL: Rs.110 → Rs.93.50 (tighter for calm)
```

### Check Loss Streak Protection:
```bash
# After 3 losses:
[WARNING] Consecutive losses: 3/3 - PAUSING TRADING
[X] Trade blocked: Consecutive loss limit reached

# After a win:
[DONE] WIN | Loss streak RESET: 3 → 0
```

### Check Profit Protect Mode:
```bash
# When daily profit hits Rs.5,000:
[STOP] PROFIT PROTECT: Peak profit Rs.5,200 | Protected capital: Rs.1,560 (30%)

# When giving back profits:
[STOP] PROFIT PROTECT: Gave back 25% from peak - REDUCE_RISK mode
Position size reduced by 50%

# When giving back too much:
[STOP] PROFIT PROTECT: Gave back 40% of peak profit - STOP_TRADING
```

### Check Pattern Performance:
```bash
# On every exit:
[[DONE] WIN] Position closed: target_1 | Pattern: bullish_breakout
[UP] Best pattern: bullish_breakout (75% WR, 8 trades)

# In logs:
[PATTERN STATS] bullish_breakout: 6W/2L (75% WR) | Avg: Rs.+245
```

---

## [CONFIG] TUNING PARAMETERS (If Needed)

### Trailing Stop Thresholds (Line ~2870):
```python
# Current: 10%, 20%, 30%
# Aggressive: 5%, 10%, 15%
# Conservative: 15%, 25%, 35%
```

### Time-of-Day Multipliers (Line ~2904):
```python
# Current:
OPENING: SL×1.25, Target×1.15
MIDDAY: SL×0.85, Target×1.0
CLOSING: SL×1.1, Target×1.05

# More aggressive (tighter stops):
OPENING: SL×1.1, Target×1.2
MIDDAY: SL×0.7, Target×1.0
CLOSING: SL×1.0, Target×1.1
```

### Consecutive Loss Limit (Line ~2857):
```python
# Current: 3 losses
# More lenient: 4-5 losses
# Stricter: 2 losses
```

### Profit Protect Threshold (Line ~3050):
```python
# Current: Rs.5,000 peak profit
# Higher: Rs.10,000 (for larger accounts)
# Lower: Rs.3,000 (for smaller accounts)
```

### Breakout Confirmation Buffer (Line ~3104):
```python
# Current: 0.2% buffer
# Stricter: 0.3-0.5% (fewer trades, higher quality)
# Looser: 0.1% (more trades, more noise)
```

---

## [DEBUG] TROUBLESHOOTING

### Feature Not Triggering?

**Trailing Stops Not Moving:**
```python
# Check if profit reached threshold
# Current price must be > entry + 10%
# Look for: update_trailing_stop() in logs
```

**Loss Streak Not Resetting:**
```python
# Verify update_loss_streak() is called in close_position()
# Check CONSECUTIVE_LOSSES dictionary
# Should reset to 0 on any win
```

**Time Adjustments Not Applied:**
```python
# Check system time is within market hours (9:15-15:30)
# Verify get_time_of_day_adjustment() returns correct phase
# Look for "[TIME] TIME PHASE" in logs
```

**Profit Protect Not Activating:**
```python
# Check PEAK_DAILY_PROFIT[clientcode] value
# Must reach Rs.5,000+ to activate
# Verify check_profit_protect_mode() called pre-entry
```

---

## [UP] EXPECTED LOG OUTPUT (Example Trade)

### Entry:
```
[NEW TRADE] Setup #1: NIFTY 18500 CE BULLISH
[PRE-ENTRY CHECKS] Starting validation...
[DONE] PASS: Max loss today (Rs.3,200 / Rs.5,000)
[DONE] PASS: Circuit breaker OK
[DONE] PASS: Loss streak: 0/3
[DONE] PASS: Profit protect: NORMAL mode
[TIME] TIME PHASE: OPENING_VOLATILITY | SL×1.25 | Target×1.15
[DONE] PASS: Breakout confirmation (18520 >= 18500 + 0.2%)
[POSITION SIZING] 5-stage pipeline:
  Base: 50 lots
  Kelly: 50 lots (WR:65%, R:R 1.8)
  Greeks: 42 lots (Delta: 0.55 → 0.85x)
  Time: 42 lots (no adjustment in opening)
  Protect: 42 lots (normal mode)
  FINAL: 42 lots
[ENTRY] Order placed: 42 lots @ Rs.120 (planned Rs.118)
[ENTRY] Order verified: 42 lots @ Rs.121.50 (slippage: +1.3%)
[TRAIL INIT] Initialized trailing stop: SL=Rs.115
```

### Monitoring (Every minute):
```
Monitoring Trade 12345: Current=Rs.133, Entry=Rs.121.50, Profit=+9.5%, SL=Rs.115
[TRAIL SL] Moved SL to breakeven at +10.2% profit: Rs.115 → Rs.121.50
Monitoring Trade 12345: Current=Rs.145, Entry=Rs.121.50, Profit=+19.3%, SL=Rs.121.50
[TRAIL SL] Trailing at +20% profit: Rs.121.50 → Rs.133.50 (+10% above entry)
Monitoring Trade 12345: Current=Rs.158, Entry=Rs.121.50, Profit=+30.0%, SL=Rs.133.50
[TRAIL SL] Trailing at +30% profit: Rs.133.50 → Rs.139.50 (+15% above entry)
```

### Partial Exit (Target 1):
```
[T1] TARGET 1 HIT - Booking 33% profit
[3-TIER SCALE] TARGET_1: Closed 14/42 lots (33%) at Rs.155 | Remaining: 28 (67%)
Monitoring Trade 12345: Current=Rs.162, Entry=Rs.121.50, Profit=+33.3%, SL=Rs.139.50
```

### Partial Exit (Target 2):
```
[T2] TARGET 2 HIT - Booking another 33%
[3-TIER SCALE] TARGET_2: Closed 14/42 lots (33%) at Rs.165 | Remaining: 14 (33%)
Monitoring Trade 12345: Current=Rs.170, Entry=Rs.121.50, Profit=+39.9%, SL=Rs.139.50
```

### Final Exit:
```
[T3] TARGET 3 HIT - Closing remaining position
[DONE] WIN Position closed: target_3 | Pattern: bullish_breakout
  Entry: Rs.121.50 × 42 = Rs.5,103
  Exit (weighted avg): Rs.163 × 42 = Rs.6,846
  P&L: Rs.+1,743 (+34.2%)
  Exit Slippage: 0.08% (Rs.11)
[UP] Best pattern: bullish_breakout (80% WR, 10 trades)
[STATS] Today: Rs.+2,890 | 70% WR | 8 trades
```

---

## [TARGET] QUICK WINS TO LOOK FOR

### Week 1:
- [x] Trailing stops move automatically (check logs)
- [x] Time adjustments apply (wider stops in morning)
- [x] 3-tier exits execute smoothly
- [x] Loss streak counter works (resets on win)

### Week 2:
- [ ] Win rate improves by 5%+ (better confirmations)
- [ ] Average profit per trade increases (trailing stops)
- [ ] Max drawdown decreases (loss limits + profit protect)
- [ ] Pattern stats show clear winners/losers

### Month 1:
- [ ] Identify 2-3 best performing patterns (focus on these)
- [ ] Identify worst pattern (avoid or modify)
- [ ] Determine best time-of-day for trading
- [ ] Fine-tune parameters based on results

---

## [TIP] PRO TIPS

### 1. Trust the System
- Don't manually override trailing stops
- Let loss streak protection work (avoid revenge trading)
- Accept profit protect mode (preserve gains)

### 2. Monitor Pattern Performance
- After 20+ trades, check which patterns win most
- Consider reducing/eliminating losing patterns
- Double down on winning patterns

### 3. Review Time-of-Day Performance
- Some traders do better in opening volatility
- Some do better in midday calm
- Adjust trading schedule based on data

### 4. Analyze Exit Timing
- Are time-based exits helping or hurting?
- Are 3-tier exits better than 2-tier?
- Review weighted average exit prices

### 5. Track Protection Activations
- How often does loss streak trigger? (should be rare)
- How often does profit protect trigger? (good problem!)
- Are thresholds set correctly for your style?

---

## [CONTACT] NEED HELP?

### Check Logs First:
```bash
# Search for specific feature:
grep "TRAIL SL" logs/trading.log
grep "PROFIT PROTECT" logs/trading.log
grep "3-TIER SCALE" logs/trading.log
grep "TIME PHASE" logs/trading.log
grep "Consecutive losses" logs/trading.log
```

### Common Issues:

**"Trailing stops not working"**
- Verify profit > 10% (check logs for current profit%)
- Confirm update_trailing_stop() is being called
- Check TRAILING_STOPS dictionary has entry

**"Too many loss streak triggers"**
- Consider increasing from 3 to 4-5 losses
- Review if losses are clustered (time-of-day issue?)
- Check if entry criteria need tightening

**"Profit protect activating too early"**
- Increase threshold from Rs.5,000 to Rs.10,000
- Adjust drawback percentages (25% → 30%, 40% → 50%)

**"Time adjustments seem wrong"**
- Verify system clock is correct
- Check if IST timezone is set correctly
- Review multipliers for your volatility preference

---

**Last Updated**: May 2025  
**Version**: 1.0  
**Status**: Production Ready [DONE]
