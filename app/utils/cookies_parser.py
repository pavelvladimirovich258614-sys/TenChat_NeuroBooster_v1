"""
Cookies parser for TenChat authentication
"""
import json
from typing import Dict, List, Any
from loguru import logger


class CookiesParser:
    """Parse cookies from JSON format (EditThisCookie/J2TEAM/Cookie-Editor)"""

    @staticmethod
    def parse_json(cookies_json: str) -> Dict[str, str]:
        """
        Parse cookies from JSON string to dictionary format

        Args:
            cookies_json: JSON string with cookies

        Returns:
            Dictionary with cookie name-value pairs

        Raises:
            ValueError: If JSON is invalid or format is incorrect
        """
        try:
            cookies_data = json.loads(cookies_json)
        except json.JSONDecodeError as e:
            raise ValueError(f"Invalid JSON format: {e}")

        if not isinstance(cookies_data, list):
            raise ValueError("Cookies JSON must be an array")

        cookies_dict = {}

        for cookie in cookies_data:
            if not isinstance(cookie, dict):
                continue

            name = cookie.get("name")
            value = cookie.get("value")

            if name and value:
                cookies_dict[name] = value

        if not cookies_dict:
            raise ValueError("No valid cookies found in JSON")

        logger.debug(f"Parsed {len(cookies_dict)} cookies: {list(cookies_dict.keys())}")
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
