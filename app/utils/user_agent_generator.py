"""
User-Agent generator for account fingerprinting
"""
import random
from typing import List


class UserAgentGenerator:
    """Generate realistic desktop User-Agent strings"""

    # Chrome versions (recent)
    CHROME_VERSIONS = [
        "120.0.0.0", "121.0.0.0", "122.0.0.0", "123.0.0.0"
    ]

    # Safari versions
    SAFARI_VERSIONS = [
        "17.2", "17.3", "17.4"
    ]

    # Operating systems
    WINDOWS_OS = [
        "Windows NT 10.0; Win64; x64",
        "Windows NT 11.0; Win64; x64"
    ]

    MAC_OS = [
        "Macintosh; Intel Mac OS X 10_15_7",
        "Macintosh; Intel Mac OS X 11_7_0",
        "Macintosh; Intel Mac OS X 12_6_0"
    ]

    LINUX_OS = [
        "X11; Linux x86_64",
        "X11; Ubuntu; Linux x86_64"
    ]

    @staticmethod
    def generate_chrome_windows() -> str:
        """Generate Chrome on Windows User-Agent"""
        os_string = random.choice(UserAgentGenerator.WINDOWS_OS)
        chrome_version = random.choice(UserAgentGenerator.CHROME_VERSIONS)

        return (
            f"Mozilla/5.0 ({os_string}) "
            f"AppleWebKit/537.36 (KHTML, like Gecko) "
            f"Chrome/{chrome_version} Safari/537.36"
        )

    @staticmethod
    def generate_chrome_mac() -> str:
        """Generate Chrome on macOS User-Agent"""
        os_string = random.choice(UserAgentGenerator.MAC_OS)
        chrome_version = random.choice(UserAgentGenerator.CHROME_VERSIONS)

        return (
            f"Mozilla/5.0 ({os_string}) "
            f"AppleWebKit/537.36 (KHTML, like Gecko) "
            f"Chrome/{chrome_version} Safari/537.36"
        )

    @staticmethod
    def generate_safari_mac() -> str:
        """Generate Safari on macOS User-Agent"""
        os_string = random.choice(UserAgentGenerator.MAC_OS)
        safari_version = random.choice(UserAgentGenerator.SAFARI_VERSIONS)

        return (
            f"Mozilla/5.0 ({os_string}) "
            f"AppleWebKit/605.1.15 (KHTML, like Gecko) "
            f"Version/{safari_version} Safari/605.1.15"
        )

    @staticmethod
    def generate_chrome_linux() -> str:
        """Generate Chrome on Linux User-Agent"""
        os_string = random.choice(UserAgentGenerator.LINUX_OS)
        chrome_version = random.choice(UserAgentGenerator.CHROME_VERSIONS)

        return (
            f"Mozilla/5.0 ({os_string}) "
            f"AppleWebKit/537.36 (KHTML, like Gecko) "
            f"Chrome/{chrome_version} Safari/537.36"
        )

    @staticmethod
    def generate_random() -> str:
        """Generate random desktop User-Agent"""
        generators = [
            UserAgentGenerator.generate_chrome_windows,
            UserAgentGenerator.generate_chrome_mac,
            UserAgentGenerator.generate_safari_mac,
            UserAgentGenerator.generate_chrome_linux
        ]

        generator = random.choice(generators)
        return generator()
