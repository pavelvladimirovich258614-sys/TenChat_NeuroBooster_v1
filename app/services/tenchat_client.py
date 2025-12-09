"""
TenChat API Client (Reverse-Engineered)
"""
import httpx
import json
from typing import Dict, List, Optional, Any
from loguru import logger

try:
    from httpx_socks import AsyncProxyTransport
    SOCKS_AVAILABLE = True
except ImportError:
    SOCKS_AVAILABLE = False
    logger.warning("httpx-socks not installed, SOCKS5 proxies will not work")


class TenChatClient:
    """HTTP/2 client for TenChat API"""

    def __init__(
        self,
        cookies: Dict[str, str],
        proxy: Dict[str, Any],
        user_agent: str,
        base_url: str = "https://tenchat.ru"
    ):
        """
        Initialize TenChat client

        Args:
            cookies: Dictionary with cookies
            proxy: Dictionary with proxy configuration (from ProxyHandler.get_httpx_proxy_config)
            user_agent: User-Agent string
            base_url: TenChat base URL
        """
        self.base_url = base_url
        self.cookies = cookies
        self.user_agent = user_agent

        # Create httpx client with HTTP/2 support
        # Handle different proxy types
        proxy_type = proxy.get("type", "http")

        if proxy_type == "socks5":
            if not SOCKS_AVAILABLE:
                raise RuntimeError(
                    "SOCKS5 proxy requested but httpx-socks is not installed. "
                    "Install it with: pip install httpx-socks"
                )

            # Create SOCKS5 transport
            transport = AsyncProxyTransport.from_url(
                f"socks5://{proxy['username']}:{proxy['password']}@{proxy['host']}:{proxy['port']}"
            )

            self.client = httpx.AsyncClient(
                transport=transport,
                timeout=30.0,
                follow_redirects=True,
                verify=True
            )
        else:
            # HTTP proxy (standard httpx)
            self.client = httpx.AsyncClient(
                http2=True,
                proxies=proxy.get("url"),
                timeout=30.0,
                follow_redirects=True,
                verify=True
            )

    def _get_headers(self, extra_headers: Optional[Dict[str, str]] = None) -> Dict[str, str]:
        """
        Get default headers for requests

        Args:
            extra_headers: Additional headers to include

        Returns:
            Dictionary with headers
        """
        headers = {
            "User-Agent": self.user_agent,
            "Accept": "application/json, text/plain, */*",
            "Accept-Language": "ru-RU,ru;q=0.9,en-US;q=0.8,en;q=0.7",
            "Accept-Encoding": "gzip, deflate, br",
            "Connection": "keep-alive",
            "Sec-Fetch-Dest": "empty",
            "Sec-Fetch-Mode": "cors",
            "Sec-Fetch-Site": "same-origin",
            "Referer": f"{self.base_url}/",
            "Origin": self.base_url,
        }

        # Add CSRF token if available
        if "csrftoken" in self.cookies:
            headers["X-CSRFToken"] = self.cookies["csrftoken"]
        if "X-Xsrf-Token" in self.cookies:
            headers["X-XSRF-TOKEN"] = self.cookies["X-Xsrf-Token"]

        # Merge extra headers
        if extra_headers:
            headers.update(extra_headers)

        return headers

    async def check_auth(self) -> bool:
        """
        Check if authentication is valid

        Returns:
            True if authenticated, False otherwise
        """
        try:
            # Try to get user profile or feed
            response = await self.client.get(
                f"{self.base_url}/api/v1/profile/me",
                headers=self._get_headers(),
                cookies=self.cookies
            )

            if response.status_code == 200:
                logger.info("Authentication check: SUCCESS")
                return True
            elif response.status_code == 401:
                logger.warning("Authentication check: UNAUTHORIZED")
                return False
            else:
                logger.warning(f"Authentication check: Unexpected status {response.status_code}")
                return False

        except Exception as e:
            logger.error(f"Authentication check failed: {e}")
            return False

    async def get_feed(
        self,
        feed_type: str = "all",
        limit: int = 20,
        offset: int = 0
    ) -> Optional[List[Dict[str, Any]]]:
        """
        Get posts from feed

        Args:
            feed_type: Feed type (all, business, it, marketing)
            limit: Number of posts to fetch
            offset: Offset for pagination

        Returns:
            List of posts or None if error
        """
        try:
            params = {
                "type": feed_type,
                "limit": limit,
                "offset": offset
            }

            response = await self.client.get(
                f"{self.base_url}/api/v1/feed",
                headers=self._get_headers(),
                cookies=self.cookies,
                params=params
            )

            if response.status_code == 200:
                data = response.json()
                posts = data.get("posts", []) if isinstance(data, dict) else data
                logger.info(f"Fetched {len(posts)} posts from feed")
                return posts
            elif response.status_code == 401:
                logger.error("Get feed: UNAUTHORIZED - cookies expired")
                return None
            else:
                logger.error(f"Get feed failed: {response.status_code}")
                return None

        except Exception as e:
            logger.error(f"Get feed exception: {e}")
            return None

    async def like_post(self, post_id: str) -> bool:
        """
        Like a post

        Args:
            post_id: Post ID to like

        Returns:
            True if successful, False otherwise
        """
        try:
            response = await self.client.post(
                f"{self.base_url}/api/v1/posts/{post_id}/like",
                headers=self._get_headers({"Content-Type": "application/json"}),
                cookies=self.cookies,
                json={}
            )

            if response.status_code in [200, 201]:
                logger.info(f"Liked post {post_id}")
                return True
            elif response.status_code == 401:
                logger.error(f"Like post {post_id}: UNAUTHORIZED")
                return False
            elif response.status_code == 403:
                logger.error(f"Like post {post_id}: FORBIDDEN (captcha or banned)")
                return False
            else:
                logger.error(f"Like post {post_id} failed: {response.status_code}")
                return False

        except Exception as e:
            logger.error(f"Like post {post_id} exception: {e}")
            return False

    async def follow_user(self, user_id: str) -> bool:
        """
        Follow a user

        Args:
            user_id: User ID to follow

        Returns:
            True if successful, False otherwise
        """
        try:
            response = await self.client.post(
                f"{self.base_url}/api/v1/users/{user_id}/follow",
                headers=self._get_headers({"Content-Type": "application/json"}),
                cookies=self.cookies,
                json={}
            )

            if response.status_code in [200, 201]:
                logger.info(f"Followed user {user_id}")
                return True
            elif response.status_code == 401:
                logger.error(f"Follow user {user_id}: UNAUTHORIZED")
                return False
            elif response.status_code == 403:
                logger.error(f"Follow user {user_id}: FORBIDDEN")
                return False
            else:
                logger.error(f"Follow user {user_id} failed: {response.status_code}")
                return False

        except Exception as e:
            logger.error(f"Follow user {user_id} exception: {e}")
            return False

    async def post_article(
        self,
        title: str,
        text: str,
        hashtags: Optional[List[str]] = None,
        image_path: Optional[str] = None
    ) -> Optional[str]:
        """
        Publish an article

        Args:
            title: Article title
            text: Article text
            hashtags: List of hashtags
            image_path: Path to image file (optional)

        Returns:
            Post ID if successful, None otherwise
        """
        try:
            # Prepare article data
            article_data = {
                "title": title,
                "text": text,
                "tags": hashtags or []
            }

            # If image provided, upload it first
            if image_path:
                image_url = await self._upload_image(image_path)
                if image_url:
                    article_data["image"] = image_url

            response = await self.client.post(
                f"{self.base_url}/api/v1/articles",
                headers=self._get_headers({"Content-Type": "application/json"}),
                cookies=self.cookies,
                json=article_data
            )

            if response.status_code in [200, 201]:
                data = response.json()
                post_id = data.get("id") or data.get("post_id")
                logger.info(f"Published article: {post_id}")
                return post_id
            elif response.status_code == 401:
                logger.error("Post article: UNAUTHORIZED")
                return None
            elif response.status_code == 403:
                logger.error("Post article: FORBIDDEN")
                return None
            else:
                logger.error(f"Post article failed: {response.status_code}")
                return None

        except Exception as e:
            logger.error(f"Post article exception: {e}")
            return None

    async def _upload_image(self, image_path: str) -> Optional[str]:
        """
        Upload image to TenChat

        Args:
            image_path: Path to image file

        Returns:
            Image URL if successful, None otherwise
        """
        try:
            with open(image_path, "rb") as f:
                files = {"file": f}
                response = await self.client.post(
                    f"{self.base_url}/api/v1/upload/image",
                    headers=self._get_headers(),
                    cookies=self.cookies,
                    files=files
                )

            if response.status_code in [200, 201]:
                data = response.json()
                image_url = data.get("url")
                logger.info(f"Uploaded image: {image_url}")
                return image_url
            else:
                logger.error(f"Upload image failed: {response.status_code}")
                return None

        except Exception as e:
            logger.error(f"Upload image exception: {e}")
            return None

    async def close(self):
        """Close HTTP client"""
        await self.client.aclose()
