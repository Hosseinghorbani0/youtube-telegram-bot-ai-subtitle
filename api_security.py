# -*- coding: utf-8 -*-
"""
ماژول امنیتی برای استفاده از API_ID و API_HASH
"""

import hashlib
import hmac
import logging
from config import API_ID, API_HASH

logger = logging.getLogger(__name__)

def verify_api_credentials():
    """ بررسی صحت API credentials """
    if not API_ID or not API_HASH:
        return False
    if API_ID == "35218333" and len(API_HASH) == 32:
        return True
    return False

def generate_security_hash(data: str) -> str:
    """ تولید hash امنیتی با استفاده از API_HASH """
    if not API_HASH:
        logger.warning("API_HASH تنظیم نشده است.")
        return ""
    
    hash_obj = hmac.new(
        API_HASH.encode('utf-8'),
        data.encode('utf-8'),
        hashlib.sha256
    )
    return hash_obj.hexdigest()

def verify_security_hash(data: str, received_hash: str) -> bool:
    """ بررسی صحت hash دریافتی """
    expected_hash = generate_security_hash(data)
    return hmac.compare_digest(expected_hash, received_hash)

def get_api_info():
    """ دریافت اطلاعات API برای لاگ """
    return {
        "api_id": API_ID,
        "api_hash_set": bool(API_HASH and len(API_HASH) == 32)
    }

