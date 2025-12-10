"""
Cookies parser for TenChat authentication
"""
# STARTUP VERIFICATION
print("[STARTUP] cookies_parser.py LOADED - VERSION 2025-12-10-v4 (FULL DEBUG)")

import json
import traceback
from typing import Dict, List, Any
from loguru import logger


class CookiesParser:
    """Parse cookies from JSON format (EditThisCookie/J2TEAM/Cookie-Editor)"""

    @staticmethod
    def parse_json(cookies_json: str) -> Dict[str, str]:
        """
        Parse cookies from JSON string to dictionary format
        """
        try:
            return CookiesParser._parse_json_internal(cookies_json)
        except Exception as e:
            logger.error(f"[COOKIES_PARSER] EXCEPTION: {type(e).__name__}: {e}")
            logger.error(f"[COOKIES_PARSER] TRACEBACK:\n{traceback.format_exc()}")
            raise

    @staticmethod
    def _parse_json_internal(cookies_json: str) -> Dict[str, str]:
        """Internal parsing with full error handling"""
        
        # Validate input
        if cookies_json is None:
            raise ValueError("Cookies JSON is None")
        
        logger.error(f"[COOKIES_PARSER] START - input type: {type(cookies_json).__name__}")
        
        # Ensure we have a string
        if isinstance(cookies_json, bytes):
            cookies_json = cookies_json.lstrip(b'\xef\xbb\xbf')
            cookies_json = cookies_json.decode('utf-8')
        
        # Strip BOM and whitespace
        cookies_json = cookies_json.lstrip('\ufeff').strip()
        
        if not cookies_json:
            raise ValueError("Cookies JSON is empty")
        
        logger.error(f"[COOKIES_PARSER] Input length: {len(cookies_json)}")
        logger.error(f"[COOKIES_PARSER] First 300 chars: {repr(cookies_json[:300])}")
        
        # Parse JSON
        try:
            cookies_data = json.loads(cookies_json)
            logger.error(f"[COOKIES_PARSER] json.loads OK - type: {type(cookies_data).__name__}")
        except json.JSONDecodeError as e:
            logger.error(f"[COOKIES_PARSER] json.loads FAILED: {e}")
            raise ValueError(f"Invalid JSON format: {e}")
        
        # Handle multiple encodings
        parse_attempts = 0
        while isinstance(cookies_data, str) and parse_attempts < 3:
            parse_attempts += 1
            logger.error(f"[COOKIES_PARSER] Decoding attempt {parse_attempts} (got string)")
            try:
                cookies_data = json.loads(cookies_data)
            except json.JSONDecodeError as e:
                raise ValueError(f"Multi-encoded JSON parse failed at attempt {parse_attempts}: {e}")
        
        logger.error(f"[COOKIES_PARSER] After decode loops - type: {type(cookies_data).__name__}")
        
        # Handle dict wrapper
        if isinstance(cookies_data, dict):
            logger.error(f"[COOKIES_PARSER] Got dict with keys: {list(cookies_data.keys())[:10]}")
            for key in ["cookies", "data", "items", "result"]:
                if key in cookies_data:
                    cookies_data = cookies_data[key]
                    logger.error(f"[COOKIES_PARSER] Extracted from '{key}' wrapper")
                    break
            else:
                if cookies_data and all(str(k).isdigit() for k in cookies_data.keys()):
                    cookies_data = list(cookies_data.values())
                    logger.error(f"[COOKIES_PARSER] Converted numeric-key dict to list")
                else:
                    # Maybe it's a single cookie dict?
                    if "name" in cookies_data and "value" in cookies_data:
                        cookies_data = [cookies_data]
                        logger.error(f"[COOKIES_PARSER] Wrapped single cookie in list")
                    else:
                        raise ValueError(f"Cookies must be array, got dict with keys: {list(cookies_data.keys())[:5]}")
        
        if not isinstance(cookies_data, list):
            raise ValueError(f"Cookies must be array, got {type(cookies_data).__name__}")
        
        logger.error(f"[COOKIES_PARSER] Processing {len(cookies_data)} entries")
        
        # Log first few elements for debugging
        for idx, elem in enumerate(cookies_data[:3]):
            logger.error(f"[COOKIES_PARSER] Element[{idx}] type={type(elem).__name__}, value={repr(str(elem)[:100])}")
        
        cookies_dict = {}
        skipped = 0
        
        for i, cookie in enumerate(cookies_data):
            try:
                # If string, try to parse as JSON
                if isinstance(cookie, str):
                    cookie = cookie.strip()
                    if cookie.startswith('{'):
                        try:
                            cookie = json.loads(cookie)
                            logger.error(f"[COOKIES_PARSER] Parsed string entry {i} as JSON object")
                        except json.JSONDecodeError as e:
                            logger.error(f"[COOKIES_PARSER] Entry {i} string parse failed: {e}")
                            skipped += 1
                            continue
                    else:
                        logger.error(f"[COOKIES_PARSER] Entry {i} is non-JSON string: {repr(cookie[:50])}")
                        skipped += 1
                        continue
                
                if not isinstance(cookie, dict):
                    logger.error(f"[COOKIES_PARSER] Entry {i} not dict: {type(cookie).__name__}")
                    skipped += 1
                    continue
                
                # Safely get name and value
                name = cookie.get("name") if hasattr(cookie, 'get') else None
                value = cookie.get("value") if hasattr(cookie, 'get') else None
                
                if name and value:
                    cookies_dict[str(name)] = str(value)
                else:
                    logger.error(f"[COOKIES_PARSER] Entry {i} missing name/value: keys={list(cookie.keys()) if hasattr(cookie, 'keys') else 'N/A'}")
                    
            except Exception as e:
                logger.error(f"[COOKIES_PARSER] Entry {i} exception: {type(e).__name__}: {e}")
                skipped += 1
                continue
        
        logger.error(f"[COOKIES_PARSER] DONE: {len(cookies_dict)} cookies, {skipped} skipped")
        
        if not cookies_dict:
            raise ValueError(f"No valid cookies found. Total entries: {len(cookies_data)}, skipped: {skipped}")
        
        logger.error(f"[COOKIES_PARSER] Cookie names: {list(cookies_dict.keys())}")
        return cookies_dict

    @staticmethod
    def extract_auth_tokens(cookies_dict: Dict[str, str]) -> Dict[str, str]:
        """
        Extract authentication tokens from cookies

        Args:
            cookies_dict: Dictionary with cookies

        Returns:
            Dictionary with important auth tokens
        """
        auth_tokens = {}

        # TenChat-specific cookies
        tenchat_cookies = [
            "SESSION",
            "TCAF",
            "TCRF",
            "session",
            "tcaf",
            "tcrf"
        ]

        # Common authentication cookie names
        generic_cookies = [
            "sessionid",
            "csrftoken",
            "X-Xsrf-Token",
            "auth_token",
            "access_token",
            "refresh_token",
            "_session",
            "sid"
        ]

        important_cookies = tenchat_cookies + generic_cookies

        for key in important_cookies:
            if key in cookies_dict:
                auth_tokens[key] = cookies_dict[key]

        return auth_tokens

    @staticmethod
    def cookies_to_header_string(cookies_dict: Dict[str, str]) -> str:
        """
        Convert cookies dictionary to Cookie header string

        Args:
            cookies_dict: Dictionary with cookies

        Returns:
            Cookie header string (e.g., "name1=value1; name2=value2")
        """
        return "; ".join([f"{name}={value}" for name, value in cookies_dict.items()])

    @staticmethod
    def validate_cookies(cookies_dict: Dict[str, str]) -> bool:
        """
        Validate if cookies contain minimum required data for TenChat

        Args:
            cookies_dict: Dictionary with cookies

        Returns:
            True if cookies are valid
        """
        # Create case-insensitive lookup
        cookies_lower = {key.lower(): key for key in cookies_dict.keys()}

        # TenChat-specific cookies (case-insensitive)
        tenchat_cookies = ["session", "tcaf", "tcrf", "sessionid"]

        # Generic session cookies (case-insensitive)
        generic_cookies = ["auth_token", "access_token", "_session", "sid", "token"]

        # Check if at least one TenChat-specific cookie exists
        has_tenchat_cookie = any(cookie.lower() in cookies_lower for cookie in tenchat_cookies)

        # Or at least one generic session cookie
        has_generic_cookie = any(cookie.lower() in cookies_lower for cookie in generic_cookies)

        is_valid = has_tenchat_cookie or has_generic_cookie

        if is_valid:
            found_cookies = [cookies_lower[c.lower()] for c in (tenchat_cookies + generic_cookies) if c.lower() in cookies_lower]
            logger.info(f"Cookies validation: PASSED. Found important cookies: {found_cookies}")
        else:
            logger.warning(f"Cookies validation: FAILED. Available cookies: {list(cookies_dict.keys())}")
            logger.warning(f"Expected at least one of: {tenchat_cookies + generic_cookies}")

        return is_valid
