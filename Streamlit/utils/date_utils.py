"""
Date parsing and formatting utilities
"""
import re
from datetime import datetime
import pandas as pd
import numpy as np
from dateutil import parser as dateparser
from config.settings import Config

# Arabic month translations
AR_MONTHS = {
    'يناير': 'January', 'فبراير': 'February', 'مارس': 'March',
    'أبريل': 'April', 'مايو': 'May', 'يونيو': 'June',
    'يونيه': 'June', 'يوليو': 'July', 'يوليوز': 'July',
    'أغسطس': 'August', 'اغسطس': 'August', 'سبتمبر': 'September',
    'أكتوبر': 'October', 'اكتوبر': 'October', 'نوفمبر': 'November',
    'ديسمبر': 'December'
}

# Arabic to English digit translation
AR_DIGITS = str.maketrans('٠١٢٣٤٥٦٧٨٩', '0123456789')


def arabic_to_english_datestr(s):
    """Convert Arabic date string to English format"""
    if not isinstance(s, str):
        return s
    
    # Clean and normalize
    t = s.strip().replace('،', ',').replace('|', ' ').replace('ـ', ' ')
    
    # Translate digits
    t = t.translate(AR_DIGITS)
    
    # Translate month names
    for ar, en in AR_MONTHS.items():
        t = re.sub(ar, en, t, flags=re.IGNORECASE)
    
    # Handle AM/PM indicators
    t = re.sub(r'(\d{1,2}[:\.]\d{1,2})\s*ص', r'\1 AM', t)
    t = re.sub(r'(\d{1,2}[:\.]\d{1,2})\s*م', r'\1 PM', t)
    
    return t


def try_parse_datestr(s):
    """
    Attempt to parse various date formats into datetime object
    Returns datetime with Cairo timezone
    """
    if s is None:
        return None
    
    # Handle datetime objects
    if isinstance(s, (pd.Timestamp, datetime)):
        dt = s.to_pydatetime() if isinstance(s, pd.Timestamp) else s
        if dt.tzinfo is None:
            try:
                return dt.replace(tzinfo=Config.CAIRO_TZ)
            except:
                return dt
        try:
            return dt.astimezone(Config.CAIRO_TZ)
        except:
            return dt
    
    # Handle numeric timestamps
    if isinstance(s, (int, float, np.integer, np.floating)):
        try:
            return datetime.fromtimestamp(float(s), tz=Config.CAIRO_TZ)
        except:
            return None
    
    # Handle string dates
    if isinstance(s, str):
        cleaned = arabic_to_english_datestr(s)
        
        # Try dateutil parser first
        try:
            dt = dateparser.parse(cleaned, fuzzy=True)
            if dt is None:
                return None
            if dt.tzinfo is None:
                try:
                    return dt.replace(tzinfo=Config.CAIRO_TZ)
                except:
                    return dt
            return dt.astimezone(Config.CAIRO_TZ)
        except:
            pass
        
        # Fallback: regex pattern matching
        m = re.search(r'(\d{1,2})[^\d](\d{1,2})[^\d](\d{4}).*?(\d{1,2}):(\d{2})', cleaned)
        if m:
            day, month, year, hh, mm = m.groups()
            try:
                return datetime(
                    int(year), int(month), int(day), 
                    int(hh), int(mm), 
                    tzinfo=Config.CAIRO_TZ
                )
            except:
                return None
    
    return None


def unified_date_display(dt_text, fallback=None):
    """
    Format date for display
    Args:
        dt_text: Date string or object to parse
        fallback: Fallback datetime if parsing fails
    Returns:
        Formatted date string
    """
    dt = try_parse_datestr(dt_text) if dt_text else None
    if dt is None and fallback is not None:
        dt = fallback
    if dt is None:
        return "Unknown"
    
    try:
        return dt.strftime("%a, %d %b %Y %H:%M")
    except:
        return str(dt)