# User Analysis Document Upload - User Guide

## Overview
You can now upload your own market analysis document (DOCX or TXT format) which will be combined with the default AI prompt to generate more informed trading decisions.

## How to Use

### Step 1: Access the Upload Page
- Navigate to: **http://localhost:5000/view/user_analysis**
- Or add a link to your dashboard navigation

### Step 2: Prepare Your Analysis Document

Create a document (Word .docx or .txt file) containing your market analysis. Include:

**Recommended Content:**
- **Market Outlook** - Your view on NIFTY direction today
  ```
  Example: "Expecting bullish momentum above 25,800. Break below 25,700 signals weakness."
  ```

- **Key Levels** - Support and resistance you're watching
  ```
  Example: 
  Support: 25,700, 25,650, 25,600
  Resistance: 25,850, 25,900, 25,950
  ```

- **Trade Preferences** - Your bias for the day
  ```
  Example: "Prefer CE options above 25,800. Avoid PE unless clear breakdown."
  ```

- **Events Impact** - How today's events might affect trading
  ```
  Example: "Fed meeting today - expect volatility after 2 PM. Book profits before event."
  ```

- **Risk Factors** - What you're cautious about
  ```
  Example: "Global markets weak. Use wider stop losses. Reduce position sizes."
  ```

### Step 3: Upload Your Document
1. Click "Choose File" button
2. Select your .docx or .txt file
3. Click "Upload Analysis"
4. Confirmation message will appear

### Step 4: Generate AI Trade Plan
- Go to AI Trade Plan generation page
- AI will now use **both**:
  - Your uploaded analysis
  - Default market data (VIX, RSI, MACD, etc.)
  - Today's performance stats
  - Technical indicators

### Step 5: Update or Delete
- **View Current Analysis** - See what's currently uploaded
- **Upload New** - Replaces previous analysis
- **Delete** - Remove analysis (AI uses only default data)

## Example Analysis Document

```
NIFTY MARKET ANALYSIS - November 17, 2025

MARKET OUTLOOK:
- Bullish bias above 25,800
- VIX around 15 suggests normal volatility
- Global cues positive (US markets up)

KEY LEVELS:
Support: 25,700 | 25,650 | 25,600
Resistance: 25,850 | 25,900 | 25,950

TRADE STRATEGY:
- Prefer CE options on dips near 25,750
- Target strikes: 25,800 CE, 25,900 CE
- Avoid PE trades unless break below 25,700
- Book profits at 15-20% in premiums

RISK FACTORS:
- RBI policy announcement at 2 PM
- Book 50% profits before announcement
- Widen stop losses to 25% due to event

TIME WINDOWS:
- Best entry: 09:30 - 10:30 (opening momentum)
- Avoid: 11:30 - 01:00 (midday lull)
- Second chance: 01:30 - 02:30 (if trend continues)

EXPIRY NOTES:
- Thursday expiry - expect higher volatility
- Time decay accelerates after 2 PM
- Close all positions by 3:15 PM
```

## How AI Uses Your Analysis

### Default Prompt (Without Your Analysis):
```
Generate intraday NIFTY options trade plan for LIVE TRADING.

CAPITAL: Rs.15,000
MAX PER TRADE: Rs.7,500

MARKET CONTEXT:
VIX: 15.2 - NORMAL VOLATILITY
TREND: BULLISH
RSI: 62.5
MACD: 0.45

[Technical indicators...]
[Option Greeks...]
```

### Enhanced Prompt (With Your Analysis):
```
Generate intraday NIFTY options trade plan for LIVE TRADING.

CAPITAL: Rs.15,000
MAX PER TRADE: Rs.7,500

MARKET CONTEXT:
VIX: 15.2 - NORMAL VOLATILITY
TREND: BULLISH
RSI: 62.5
MACD: 0.45

[Technical indicators...]
[Option Greeks...]

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
USER'S MARKET ANALYSIS:
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
File: market_analysis_nov17.docx
Uploaded: 2025-11-17 09:05

[Your complete analysis content here...]
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
```

## Benefits

1. **Personalized Trading** - AI respects your market view
2. **Better Context** - Combines your insights with technical data
3. **Consistent Strategy** - Your analysis applied to all trades today
4. **Event Awareness** - Factor in events you're tracking
5. **Risk Management** - Apply your risk preferences

## API Endpoints

For programmatic access:

### Upload Analysis
```
POST /api/analysis/upload
Content-Type: multipart/form-data
Body: file (DOCX or TXT)

Response:
{
    "status": true,
    "message": "Analysis document uploaded successfully",
    "filename": "analysis.docx",
    "content_length": 1245,
    "uploaded_at": "2025-11-17T09:05:00"
}
```

### Get Current Analysis
```
GET /api/analysis/get

Response:
{
    "status": true,
    "has_analysis": true,
    "filename": "analysis.docx",
    "content": "Your full analysis text...",
    "content_length": 1245,
    "uploaded_at": "2025-11-17T09:05:00"
}
```

### Delete Analysis
```
POST /api/analysis/delete

Response:
{
    "status": true,
    "message": "Analysis document deleted successfully"
}
```

## File Requirements

- **Formats:** .docx (Word) or .txt (Plain Text)
- **Size Limit:** No hard limit, but keep under 100KB for best performance
- **Encoding:** UTF-8 recommended for TXT files
- **Content:** Plain text only (no images, tables, or complex formatting)

## Tips for Best Results

1. **Be Specific** - Clear support/resistance levels work better than vague descriptions
2. **Use Numbers** - "Trade above 25,800" is clearer than "Trade on strength"
3. **State Bias** - Explicitly say "Bullish bias" or "Prefer PE trades"
4. **List Levels** - Bullet points and clear formatting help AI parse your intent
5. **Update Daily** - Upload fresh analysis each morning for current market view
6. **Keep It Concise** - 500-2000 words is ideal (too long dilutes key points)

## Troubleshooting

### "Could not extract text from file"
- Check file isn't corrupted
- Try saving as .txt instead of .docx
- Ensure file contains text (not just images)

### "Invalid file type"
- Only .docx and .txt are supported
- Check file extension is lowercase
- Don't rename .doc to .docx (must be actual DOCX format)

### "No file selected"
- Click "Choose File" before clicking "Upload"
- Check browser allows file uploads
- Try different browser if issue persists

### Analysis Not Appearing in Trade Plan
- Verify upload success (check confirmation message)
- Reload trade plan generation page
- Check browser console for errors

## Example Workflow

**Daily Trading Routine:**

1. **Morning (9:00 AM)**
   - Review global markets, news, economic calendar
   - Write analysis document with your market view
   - Upload to system

2. **Market Open (9:15 AM)**
   - Generate AI trade plan (now includes your analysis)
   - Review suggested trades
   - Enable auto-trading

3. **During Day**
   - Monitor active trades
   - AI uses your analysis for all decisions

4. **End of Day (3:30 PM)**
   - Review performance
   - Note what worked/didn't work
   - Update analysis for tomorrow

## Privacy & Storage

- **Files stored locally** in `uploads/` folder
- **Format:** `{clientcode}_{timestamp}_{filename}`
- **Persistence:** Analysis remains active until you delete or replace it
- **Security:** Only you can see your analysis (tied to your client code)

## Advanced Usage

### Conditional Strategies
```
IF NIFTY > 25,900 THEN:
  - Trade 26,000 CE aggressively
  - Target 20% gains
  
IF NIFTY < 25,700 THEN:
  - Switch to PE trades
  - 25,700 PE, 25,600 PE
```

### Time-Based Instructions
```
09:30 - 11:00: Momentum trades (CE on strength)
11:00 - 14:00: Wait for setup (avoid FOMO)
14:00 - 15:30: Mean reversion (fade extremes)
```

### Pattern Recognition
```
PATTERNS TO WATCH:
- Double bottom at 25,650 = bullish reversal
- Break above 25,900 with volume = breakout trade
- Failed rally at 25,950 = fade the move
```

---

**Ready to Start?**

1. Visit: http://localhost:5000/view/user_analysis
2. Upload your analysis document
3. Generate AI trade plan
4. Watch AI combine your insights with market data!

---

**Questions or Issues?**
Check logs in `tradebot.log` for detailed upload/processing information.
