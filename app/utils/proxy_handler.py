"""
Proxy handler for TenChat requests
"""
import re
from typing import Optional, Dict, Tuple
from urllib.parse import quote


class ProxyHandler:
    """Handle proxy configuration and validation"""

    @staticmethod
    def parse_proxy(proxy_string: str) -> Dict[str, str]:
        """
        Parse proxy string to dictionary

        Args:
            proxy_string: Proxy in format "ip:port:login:pass" or "socks5://ip:port:login:pass" or "type:ip:port:login:pass"

        Returns:
            Dictionary with proxy configuration including 'type' key

        Raises:
            ValueError: If proxy format is invalid
        """
        proxy_type = "http"  # default

        # Check for URL-style prefix (socks5:// or http://)
        if "://" in proxy_string:
            if proxy_string.startswith("socks5://"):
                proxy_type = "socks5"
                proxy_string = proxy_string.replace("socks5://", "")
            elif proxy_string.startswith("http://"):
                proxy_type = "http"
                proxy_string = proxy_string.replace("http://", "")
            else:
                raise ValueError("Unsupported proxy protocol. Use 'http://' or 'socks5://'")

        parts = proxy_string.split(":")

        # Check for type:ip:port:login:pass format
        if len(parts) == 5:
            proxy_type_part = parts[0].lower()
            if proxy_type_part in ["http", "socks5"]:
                proxy_type = proxy_type_part
                parts = parts[1:]  # Remove type from parts
            else:
                raise ValueError(f"Invalid proxy type: {proxy_type_part}. Use 'http' or 'socks5'")

        if len(parts) != 4:
            raise ValueError(
                "Invalid proxy format. Expected: ip:port:login:pass or socks5://ip:port:login:pass or type:ip:port:login:pass"
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
            "type": proxy_type,
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
    def get_httpx_proxy_config(proxy_string: str) -> Dict[str, any]:
        """
        Get proxy configuration for httpx client

        Args:
            proxy_string: Proxy in format "ip:port:login:pass" or with type prefix

        Returns:
            Dictionary with httpx proxy configuration and type info
        """
        proxy_data = ProxyHandler.parse_proxy(proxy_string)

        # URL-encode credentials
        login = quote(proxy_data["login"])
        password = quote(proxy_data["password"])

        proxy_type = proxy_data["type"]

        # For HTTP proxy, use standard httpx format
        if proxy_type == "http":
            proxy_url = (
                f"http://{login}:{password}@"
                f"{proxy_data['ip']}:{proxy_data['port']}"
            )
            return {
                "type": "http",
                "url": {
                    "http://": proxy_url,
                    "https://": proxy_url
                }
            }
        # For SOCKS5, return config for httpx-socks
        elif proxy_type == "socks5":
            return {
                "type": "socks5",
                "host": proxy_data["ip"],
                "port": int(proxy_data["port"]),
                "username": proxy_data["login"],
                "password": proxy_data["password"]
            }
        else:
            raise ValueError(f"Unsupported proxy type: {proxy_type}")

    @staticmethod
    def format_proxy_display(proxy_string: str) -> str:
        """
        Format proxy for display (hide password)

        Args:
            proxy_string: Proxy in format "ip:port:login:pass" or with type prefix

        Returns:
            Formatted string with hidden password and proxy type
        """
        try:
            proxy_data = ProxyHandler.parse_proxy(proxy_string)
            proxy_type = proxy_data.get('type', 'http').upper()
            return (
                f"[{proxy_type}] {proxy_data['ip']}:{proxy_data['port']} "
                f"({proxy_data['login']}:****)"
            )
        except ValueError:
            return "Invalid proxy"
