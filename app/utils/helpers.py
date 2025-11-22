import logging
import sys
import pytz
from datetime import datetime

# IST Timezone for Indian market
IST = pytz.timezone('Asia/Kolkata')

def get_ist_now():
    """Get current datetime in IST timezone"""
    return datetime.now(IST)

def setup_logging():
    # Logging setup - Configure console handler with UTF-8 encoding
    console_handler = logging.StreamHandler()
    console_handler.setLevel(logging.INFO)
    console_handler.setFormatter(logging.Formatter('%(asctime)s - %(levelname)s - %(message)s'))
    
    # Force UTF-8 encoding for Windows console
    if sys.platform == 'win32':
        console_handler.stream = open(sys.stdout.fileno(), mode='w', encoding='utf-8', buffering=1)

    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(levelname)s - %(message)s',
        handlers=[
            logging.FileHandler('tradebot.log', encoding='utf-8'),
            console_handler
        ]
    )

    # Silence verbose APScheduler logs (only show warnings and errors)
    logging.getLogger('apscheduler.scheduler').setLevel(logging.WARNING)
    logging.getLogger('apscheduler.executors.default').setLevel(logging.WARNING)
