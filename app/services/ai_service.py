import logging
import json
import os
from openai import OpenAI

# Initialize OpenAI client
openai_client = None
try:
    api_key = os.getenv("OPENAI_API_KEY")
    if api_key:
        openai_client = OpenAI(api_key=api_key)
    else:
        logging.warning("OPENAI_API_KEY not found in environment variables")
except Exception as e:
    logging.error(f"Failed to initialize OpenAI client: {e}")

def parse_trade_plan_with_ai(plan_text, clientcode):
    """Use OpenAI to parse trade plan text into structured JSON"""
    if not openai_client:
        logging.error("OpenAI client not initialized")
        return None
        
    try:
        logging.info(f"Parsing trade plan for {clientcode} using AI")
        
        parsing_prompt = f"""Parse this trading plan into structured JSON format. Extract ALL trade setups mentioned.

TRADE PLAN:
{plan_text}

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

        response = openai_client.chat.completions.create(
            model="gpt-4o",
            messages=[
                {"role": "system", "content": "You are a JSON parser. Return ONLY valid JSON, no markdown formatting."},
                {"role": "user", "content": parsing_prompt}
            ],
            temperature=0,
            max_tokens=2000
        )
        
        content = response.choices[0].message.content
        if not content:
            raise ValueError("OpenAI returned empty content")
        
        parsed_json = content.strip()
        
        # Remove markdown code blocks if present
        if parsed_json.startswith("```"):
            parsed_json = parsed_json.split("```")[1]
            if parsed_json.startswith("json"):
                parsed_json = parsed_json[4:]
        
        parsed_data = json.loads(parsed_json)
        logging.info(f"Successfully parsed {len(parsed_data.get('trades', []))} trades")
        
        return parsed_data
        
    except Exception as e:
        logging.error(f"Error parsing trade plan with AI: {e}", exc_info=True)
        return None

def ai_analyze_market_shift(nifty_price, indicators, premarket_data=None):
    """Use AI to analyze if market conditions have shifted significantly"""
    if not openai_client:
        return None
        
    try:
        premarket = premarket_data or {}
        
        # Build AI prompt for market shift analysis
        prompt = f"""Analyze current NIFTY market conditions and determine if there's a significant shift in direction.

[UP] CURRENT NIFTY: {nifty_price:.2f}
[CHART] RSI (14): {indicators.get('rsi', 'N/A')}
[DOWN] MACD: {indicators.get('macd', 'N/A')}
🌎 Global Markets: {premarket.get('sgx_nifty', 'N/A')}

Based on these indicators, has the market shifted direction significantly?

Respond in JSON format:
{{
  "shift_detected": true/false,
  "new_direction": "bullish" / "bearish" / "neutral",
  "confidence": 0-100,
  "reason": "Brief explanation",
  "recommendation": "hold" / "tighten_sl" / "trail_sl" / "exit_early"
}}"""

        response = openai_client.chat.completions.create(
            model="gpt-4o",
            messages=[
                {"role": "system", "content": "You are a professional market analyst. Respond only with valid JSON."},
                {"role": "user", "content": prompt}
            ],
            temperature=0.3,
            max_tokens=500
        )
        
        content = response.choices[0].message.content
        if not content:
            return None
        
        analysis_text = content.strip()
        
        # Extract JSON from response
        if '```json' in analysis_text:
            analysis_text = analysis_text.split('```json')[1].split('```')[0].strip()
        elif '```' in analysis_text:
            analysis_text = analysis_text.split('```')[1].split('```')[0].strip()
        
        analysis = json.loads(analysis_text)
        
        logging.info(f"[AI] Market Analysis: {analysis.get('new_direction')} ({analysis.get('confidence')}% confidence)")
        
        return analysis
        
    except Exception as e:
        logging.error(f"Error in AI market analysis: {e}")
        return None

def ai_adjust_trade_params(trade_data, market_analysis):
    """Use AI to determine new stop loss and target levels based on market shift"""
    if not openai_client:
        return None
        
    try:
        recommendation = market_analysis.get('recommendation')
        new_direction = market_analysis.get('new_direction')
        
        current_sl = trade_data.get('stop_loss')
        current_target_1 = trade_data.get('target_1')
        current_target_2 = trade_data.get('target_2')
        entry_price = trade_data.get('entry_price')
        current_price = trade_data.get('current_price', entry_price)
        
        # Build AI prompt for parameter adjustment
        prompt = f"""Given market has shifted to {new_direction}, adjust stop loss and targets for this trade.

[CAPITAL] Entry Price: Rs.{entry_price}
[UP] Current Price: Rs.{current_price}
[SL] Current Stop Loss: Rs.{current_sl}
[TARGET] Current Target 1: Rs.{current_target_1}
[TARGET] Current Target 2: Rs.{current_target_2}

[TRADE] Market Direction: {new_direction}
[TIP] Recommendation: {recommendation}

Provide new stop loss and target levels. Respond in JSON:
{{
  "new_stop_loss": <price>,
  "new_target_1": <price>,
  "new_target_2": <price>,
  "modification_reason": "Brief explanation"
}}

Rules:
- If tighten_sl: Move SL closer to current price to protect profits
- If trail_sl: Trail SL below current price
- If exit_early: Lower targets to book profits quickly
- Stop loss should NEVER be worse than original"""

        response = openai_client.chat.completions.create(
            model="gpt-4o",
            messages=[
                {"role": "system", "content": "You are a professional risk manager. Respond only with valid JSON."},
                {"role": "user", "content": prompt}
            ],
            temperature=0.3,
            max_tokens=300
        )
        
        content = response.choices[0].message.content
        if not content:
            return None
        
        adjustment_text = content.strip()
        
        # Extract JSON
        if '```json' in adjustment_text:
            adjustment_text = adjustment_text.split('```json')[1].split('```')[0].strip()
        elif '```' in adjustment_text:
            adjustment_text = adjustment_text.split('```')[1].split('```')[0].strip()
        
        adjustments = json.loads(adjustment_text)
        
        logging.info(f"[CONFIG] AI Trade Adjustment: New SL Rs.{adjustments.get('new_stop_loss')}")
        
        return adjustments
        
    except Exception as e:
        logging.error(f"Error in AI trade adjustment: {e}")
        return None
