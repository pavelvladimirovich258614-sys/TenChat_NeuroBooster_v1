"""
Cookies parser for TenChat authentication
"""
import json
from typing import Dict, List, Any


class CookiesParser:
    """Parse cookies from JSON format (EditThisCookie/J2TEAM)"""

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

        # Common authentication cookie names
        important_cookies = [
            "sessionid",
            "csrftoken",
            "X-Xsrf-Token",
            "auth_token",
            "access_token",
            "refresh_token",
            "_session",
            "sid"
        ]

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
        Validate if cookies contain minimum required data

        Args:
            cookies_dict: Dictionary with cookies

        Returns:
            True if cookies are valid
        """
        # Check if at least one session-related cookie exists
        session_cookies = ["sessionid", "auth_token", "access_token", "_session", "sid"]
        return any(cookie in cookies_dict for cookie in session_cookies)
