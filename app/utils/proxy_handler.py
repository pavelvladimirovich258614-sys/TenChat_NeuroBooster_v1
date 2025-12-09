"""
Proxy handler for TenChat requests
"""
import re
from typing import Optional, Dict
from urllib.parse import quote


class ProxyHandler:
    """Handle proxy configuration and validation"""

    @staticmethod
    def parse_proxy(proxy_string: str) -> Dict[str, str]:
        """
        Parse proxy string to dictionary

        Args:
            proxy_string: Proxy in format "ip:port:login:pass"

        Returns:
            Dictionary with proxy configuration

        Raises:
            ValueError: If proxy format is invalid
        """
        parts = proxy_string.split(":")

        if len(parts) != 4:
            raise ValueError(
                "Invalid proxy format. Expected: ip:port:login:pass"
            )

        ip, port, login, password = parts

        # Validate IP
        if not ProxyHandler._is_valid_ip(ip):
            raise ValueError(f"Invalid IP address: {ip}")

        # Validate port
        try:
            port_int = int(port)
            if not (1 <= port_int <= 65535):
                raise ValueError(f"Port must be between 1 and 65535: {port}")
        except ValueError:
            raise ValueError(f"Invalid port number: {port}")

        return {
            "ip": ip,
            "port": port,
            "login": login,
            "password": password
        }

    @staticmethod
    def _is_valid_ip(ip: str) -> bool:
        """
        Validate IP address format

        Args:
            ip: IP address string

        Returns:
            True if valid IPv4 address
        """
        pattern = re.compile(
            r'^'
            r'(?:(?:25[0-5]|2[0-4][0-9]|[01]?[0-9][0-9]?)\.){3}'
            r'(?:25[0-5]|2[0-4][0-9]|[01]?[0-9][0-9]?)'
            r'$'
        )
        return bool(pattern.match(ip))

    @staticmethod
    def get_httpx_proxy_config(proxy_string: str) -> Dict[str, str]:
        """
        Get proxy configuration for httpx client

        Args:
            proxy_string: Proxy in format "ip:port:login:pass"

        Returns:
            Dictionary with httpx proxy configuration
        """
        proxy_data = ProxyHandler.parse_proxy(proxy_string)

        # URL-encode credentials
        login = quote(proxy_data["login"])
        password = quote(proxy_data["password"])

        proxy_url = (
            f"http://{login}:{password}@"
            f"{proxy_data['ip']}:{proxy_data['port']}"
        )

        return {
            "http://": proxy_url,
            "https://": proxy_url
        }

    @staticmethod
    def format_proxy_display(proxy_string: str) -> str:
        """
        Format proxy for display (hide password)

        Args:
            proxy_string: Proxy in format "ip:port:login:pass"

        Returns:
            Formatted string with hidden password
        """
        try:
            proxy_data = ProxyHandler.parse_proxy(proxy_string)
            return (
                f"{proxy_data['ip']}:{proxy_data['port']} "
                f"({proxy_data['login']}:****)"
            )
        except ValueError:
            return "Invalid proxy"
