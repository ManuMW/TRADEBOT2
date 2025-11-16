import re

with open('e:/TradeBot2/app.py', 'r', encoding='utf-8') as f:
    content = f.read()

# Fix 1: Replace all 'smartapi' key references with 'api'
print("Fixing 'smartapi' key references...")
content = re.sub(r"_SMARTAPI_SESSIONS\[session_id\]\['smartapi'\]", "_SMARTAPI_SESSIONS[session_id]['api']", content)

# Fix 2: Remove ALL Unicode symbols
print("Removing Unicode symbols...")
replacements = [
    ('₹', 'Rs.'),
    ('✓', '[OK]'),
    ('✗', '[X]'),
    ('✅', '[OK]'),
    ('❌', '[FAIL]'),
    ('⚠️', '[WARNING]'),
    ('⚠', '[WARNING]'),
    ('🔄', '[TRADE]'),
    ('💰', '[CAPITAL]'),
    ('💵', '[PRICE]'),
    ('🛑', '[SL]'),
    ('🎯', '[TARGET]'),
    ('📊', '[CHART]'),
    ('📈', '[UP]'),
    ('📉', '[DOWN]'),
    ('🚀', '[START]'),
    ('⏰', '[TIME]'),
    ('📅', '[DATE]'),
    ('🔍', '[SEARCH]'),
    ('💹', '[PROFIT]'),
    ('📋', '[LIST]'),
]

for old, new in replacements:
    count = content.count(old)
    if count > 0:
        print(f"  Replacing '{old}' with '{new}' ({count} times)")
        content = content.replace(old, new)

with open('e:/TradeBot2/app.py', 'w', encoding='utf-8') as f:
    f.write(content)

print("\nDone! Fixed all Unicode issues and smartapi key references.")
