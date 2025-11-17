"""
Script to remove all emojis from markdown documentation files
"""
import re
import os

# Comprehensive emoji replacement mapping
EMOJI_REPLACEMENTS = {
    # Status indicators
    '✅': '[DONE]',
    '❌': '[X]',
    '⚠️': '[WARNING]',
    '✓': '[OK]',
    
    # Trading symbols  
    '🔄': '[IN-PROGRESS]',
    '📈': '[UP]',
    '📉': '[DOWN]',
    '🛑': '[STOP]',
    '🎯': '[TARGET]',
    '📊': '[STATS]',
    '🚀': '[DEPLOY]',
    '⏰': '[TIME]',
    '🚨': '[ALERT]',
    '💡': '[TIP]',
    '📝': '[NOTE]',
    '🔧': '[CONFIG]',
    '🐛': '[DEBUG]',
    '📞': '[CONTACT]',
    '🎓': '[LEARN]',
    '🔐': '[SECURITY]',
    '🏆': '[SUCCESS]',
    '📋': '[CHECKLIST]',
    '🔌': '[API]',
    '⏳': '[PLACEHOLDER]',
    '🧪': '[TEST]',
    
    # Performance indicators
    '🔥': '[HOT]',
    '💪': '[STRONG]',
    '💰': '[MONEY]',
    
    # Direction/Status
    '➡️': '[NEUTRAL]',
    '❓': '[UNKNOWN]',
    '🟢': '[BULLISH]',
    '🔴': '[BEARISH]',
    '⚪': '[NEUTRAL]',
    
    # Additional
    '📰': '[NEWS]',
    '⚡': '[FAST]',
}

def remove_emojis_from_file(filepath):
    """Remove emojis from a single file"""
    try:
        with open(filepath, 'r', encoding='utf-8') as f:
            content = f.read()
        
        original_content = content
        replacements_made = 0
        
        # Replace each emoji
        for emoji, replacement in EMOJI_REPLACEMENTS.items():
            if emoji in content:
                count = content.count(emoji)
                content = content.replace(emoji, replacement)
                replacements_made += count
                print(f"  Replaced {count}x '{emoji}' with '{replacement}'")
        
        # Only write if changes were made
        if content != original_content:
            with open(filepath, 'w', encoding='utf-8') as f:
                f.write(content)
            print(f"[OK] Updated {filepath}: {replacements_made} replacements\n")
            return replacements_made
        else:
            print(f"  No emojis found in {filepath}\n")
            return 0
            
    except Exception as e:
        print(f"[ERROR] Error processing {filepath}: {e}\n")
        return 0

def main():
    """Process all markdown files in the current directory"""
    total_replacements = 0
    files_processed = 0
    
    print("=" * 60)
    print("EMOJI REMOVAL SCRIPT - MARKDOWN FILES")
    print("=" * 60)
    print()
    
    # Process all .md files
    for filename in os.listdir('.'):
        if filename.endswith('.md'):
            print(f"Processing: {filename}")
            replacements = remove_emojis_from_file(filename)
            total_replacements += replacements
            files_processed += 1
    
    print("=" * 60)
    print(f"SUMMARY: {total_replacements} emojis replaced in {files_processed} files")
    print("=" * 60)

if __name__ == '__main__':
    main()
