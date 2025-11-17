"""Test AI trade plan generation and parsing"""
import os
import json
from openai import OpenAI
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Initialize OpenAI client
openai_client = OpenAI(api_key=os.environ.get('OPENAI_API_KEY'))

# Sample parameters
capital = 20000
current_price = 25847.3
current_rsi = 50.00
current_macd = 0.00
max_per_trade = capital * 0.5
max_premium_per_lot = max_per_trade / 15

# Generation prompt
gen_prompt = f"""Generate intraday NIFTY options trade plan based on HISTORICAL data.

CAPITAL: Rs.{capital:,}
MAX PER TRADE: Rs.{max_per_trade:,.0f} (50% of capital)
CURRENT NIFTY: {current_price:.2f}
RSI: {current_rsi:.2f}
MACD: {current_macd:.2f}

Generate 1-2 NIFTY option trade setups with complete details:

For each trade, specify:
1. Strike price (ATM, slightly OTM based on NIFTY level)
2. Option type (CE for bullish, PE for bearish)
3. Entry price: Option premium price (realistic based on NIFTY level)
4. Entry conditions: NIFTY spot price level that triggers entry
5. Stop loss: Option premium level (not NIFTY index)
6. Target 1 & Target 2: Option premium levels
7. Quantity: 15 or 25 (based on lot size)
8. Entry time window: e.g., 09:30 to 11:00

Guidelines:
- Option premiums: Rs.50-200 range for ATM options
- Stop loss: 20-30% below entry price
- Target 1: 15-20% above entry price
- Target 2: 30-40% above entry price
- Entry condition: "When NIFTY crosses above 25850" (for CE) or "When NIFTY crosses below 25800" (for PE)

Format example:
Trade 1: NIFTY 26000 CE
Entry Premium: Rs.120
Entry Condition: When NIFTY crosses above 25900
Stop Loss: Rs.85 (premium)
Target 1: Rs.140 (premium)
Target 2: Rs.165 (premium)
Quantity: 25
Entry Time: 09:30 to 11:30

Trade 2: NIFTY 25700 PE
Entry Premium: Rs.100
Entry Condition: When NIFTY crosses below 25750
Stop Loss: Rs.70 (premium)
Target 1: Rs.120 (premium)
Target 2: Rs.145 (premium)
Quantity: 25
Entry Time: 09:30 to 12:00"""

print("=" * 80)
print("GENERATING TRADE PLAN...")
print("=" * 80)

response = openai_client.chat.completions.create(
    model="gpt-4o",
    messages=[
        {"role": "system", "content": "You are a professional intraday trader."},
        {"role": "user", "content": gen_prompt}
    ],
    temperature=0.7,
    max_tokens=2000
)

trade_plan_text = response.choices[0].message.content
print("\nGENERATED TRADE PLAN:")
print(trade_plan_text)

# Now parse it
parsing_prompt = f"""Parse this trading plan into structured JSON format. Extract ALL trade setups mentioned.

TRADE PLAN:
{trade_plan_text}

Return ONLY valid JSON (no markdown, no explanation) in this exact format:
{{
  "trades": [
    {{
      "trade_number": 1,
      "instrument": "NIFTY 26000 CE",
      "tradingsymbol": "NIFTY26000CE",
      "strike": 26000,
      "option_type": "CE",
      "entry_price": 120.00,
      "entry_conditions": [
        {{"type": "price", "indicator": "NIFTY", "operator": ">", "value": 25900}}
      ],
      "quantity": 25,
      "stop_loss": 85.00,
      "target_1": 140.00,
      "target_2": 165.00,
      "entry_time_start": "09:30",
      "entry_time_end": "11:30"
    }}
  ]
}}

PARSING RULES:
1. instrument: Extract strike and option type (e.g., "NIFTY 26000 CE")
2. tradingsymbol: Combine without spaces (e.g., "NIFTY26000CE")
3. strike: Extract numeric strike price (e.g., 26000)
4. option_type: Extract "CE" or "PE"
5. entry_price: Extract option premium for entry (e.g., Rs.120 → 120.00)
6. entry_conditions: Convert "When NIFTY crosses above 25900" to:
   {{"type": "price", "indicator": "NIFTY", "operator": ">", "value": 25900}}
   Convert "When NIFTY crosses below 25750" to:
   {{"type": "price", "indicator": "NIFTY", "operator": "<", "value": 25750}}
7. stop_loss: Extract premium level (e.g., Rs.85 → 85.00)
8. target_1: Extract first target premium (e.g., Rs.140 → 140.00)
9. target_2: Extract second target premium (e.g., Rs.165 → 165.00)
10. quantity: Extract quantity (default to 25 if not specified)
11. entry_time_start/end: Extract time window (e.g., "09:30 to 11:30" → "09:30", "11:30")

IMPORTANT: All prices (entry_price, stop_loss, targets) should be OPTION PREMIUM levels, NOT NIFTY index levels.
Return valid JSON only."""

print("\n" + "=" * 80)
print("PARSING TRADE PLAN...")
print("=" * 80)

response2 = openai_client.chat.completions.create(
    model="gpt-4o",
    messages=[
        {"role": "system", "content": "You are a JSON parser. Return ONLY valid JSON, no markdown formatting."},
        {"role": "user", "content": parsing_prompt}
    ],
    temperature=0,
    max_tokens=2000
)

content = response2.choices[0].message.content
if not content:
    raise ValueError("OpenAI returned empty content")

parsed_json = content.strip()

# Remove markdown code blocks if present
if parsed_json.startswith("```"):
    parsed_json = parsed_json.split("```")[1]
    if parsed_json.startswith("json"):
        parsed_json = parsed_json[4:]

print("\nPARSED JSON:")
print(parsed_json)

# Validate
try:
    parsed_data = json.loads(parsed_json)
    print("\n" + "=" * 80)
    print("VALIDATION: SUCCESS")
    print("=" * 80)
    print(json.dumps(parsed_data, indent=2))
    
    # Check key fields
    for i, trade in enumerate(parsed_data.get('trades', []), 1):
        print(f"\nTrade {i} Validation:")
        print(f"  [OK] tradingsymbol: {trade.get('tradingsymbol', 'MISSING')}")
        print(f"  [OK] entry_price: {trade.get('entry_price', 'MISSING')}")
        print(f"  [OK] entry_conditions: {trade.get('entry_conditions', 'MISSING')}")
        print(f"  [OK] stop_loss: {trade.get('stop_loss', 'MISSING')}")
        print(f"  [OK] target_1: {trade.get('target_1', 'MISSING')}")
        
except json.JSONDecodeError as e:
    print(f"\nVALIDATION FAILED: {e}")
