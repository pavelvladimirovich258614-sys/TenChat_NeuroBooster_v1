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

    async def comment_on_post(
        self,
        post_id: str,
        comment_text: str
    ) -> bool:
        """
        Comment on a post

        Args:
            post_id: Post ID to comment on
            comment_text: Comment text

        Returns:
            True if successful, False otherwise
        """
        try:
            response = await self.client.post(
                f"{self.base_url}/api/v1/posts/{post_id}/comments",
                headers=self._get_headers({"Content-Type": "application/json"}),
                cookies=self.cookies,
                json={"text": comment_text}
            )

            if response.status_code in [200, 201]:
                logger.info(f"Commented on post {post_id}")
                return True
            elif response.status_code == 401:
                logger.error(f"Comment on post {post_id}: UNAUTHORIZED")
                return False
            elif response.status_code == 403:
                logger.error(f"Comment on post {post_id}: FORBIDDEN")
                return False
            else:
                logger.error(f"Comment on post {post_id} failed: {response.status_code}")
                return False

        except Exception as e:
            logger.error(f"Comment on post {post_id} exception: {e}")
            return False

    async def search_users(
        self,
        query: str,
        limit: int = 20
    ) -> Optional[List[Dict[str, Any]]]:
        """
        Search for users

        Args:
            query: Search query (name, position, company)
            limit: Number of results

        Returns:
            List of users or None if error
        """
        try:
            params = {
                "q": query,
                "limit": limit
            }

            response = await self.client.get(
                f"{self.base_url}/api/v1/users/search",
                headers=self._get_headers(),
                cookies=self.cookies,
                params=params
            )

            if response.status_code == 200:
                data = response.json()
                users = data.get("users", []) if isinstance(data, dict) else data
                logger.info(f"Found {len(users)} users for query '{query}'")
                return users
            elif response.status_code == 401:
                logger.error("Search users: UNAUTHORIZED")
                return None
            else:
                logger.error(f"Search users failed: {response.status_code}")
                return None

        except Exception as e:
            logger.error(f"Search users exception: {e}")
            return None

    async def send_message(
        self,
        user_id: str,
        message_text: str
    ) -> bool:
        """
        Send direct message to user

        Args:
            user_id: User ID to send message to
            message_text: Message text

        Returns:
            True if successful, False otherwise
        """
        try:
            response = await self.client.post(
                f"{self.base_url}/api/v1/messages",
                headers=self._get_headers({"Content-Type": "application/json"}),
                cookies=self.cookies,
                json={
                    "recipient_id": user_id,
                    "text": message_text
                }
            )

            if response.status_code in [200, 201]:
                logger.info(f"Sent message to user {user_id}")
                return True
            elif response.status_code == 401:
                logger.error(f"Send message to {user_id}: UNAUTHORIZED")
                return False
            elif response.status_code == 403:
                logger.error(f"Send message to {user_id}: FORBIDDEN")
                return False
            else:
                logger.error(f"Send message to {user_id} failed: {response.status_code}")
                return False

        except Exception as e:
            logger.error(f"Send message to {user_id} exception: {e}")
            return False

    async def get_inbox(
        self,
        limit: int = 20,
        unread_only: bool = False
    ) -> Optional[List[Dict[str, Any]]]:
        """
        Get inbox messages

        Args:
            limit: Number of messages to fetch
            unread_only: Fetch only unread messages

        Returns:
            List of messages or None if error
        """
        try:
            params = {
                "limit": limit,
                "unread": unread_only
            }

            response = await self.client.get(
                f"{self.base_url}/api/v1/messages/inbox",
                headers=self._get_headers(),
                cookies=self.cookies,
                params=params
            )

            if response.status_code == 200:
                data = response.json()
                messages = data.get("messages", []) if isinstance(data, dict) else data
                logger.info(f"Fetched {len(messages)} inbox messages")
                return messages
            elif response.status_code == 401:
                logger.error("Get inbox: UNAUTHORIZED")
                return None
            else:
                logger.error(f"Get inbox failed: {response.status_code}")
                return None

        except Exception as e:
            logger.error(f"Get inbox exception: {e}")
            return None

    async def invite_to_alliance(
        self,
        alliance_id: str,
        user_id: str
    ) -> bool:
        """
        Invite user to alliance

        Args:
            alliance_id: Alliance ID
            user_id: User ID to invite

        Returns:
            True if successful, False otherwise
        """
        try:
            response = await self.client.post(
                f"{self.base_url}/api/v1/alliances/{alliance_id}/invite",
                headers=self._get_headers({"Content-Type": "application/json"}),
                cookies=self.cookies,
                json={"user_id": user_id}
            )

            if response.status_code in [200, 201]:
                logger.info(f"Invited user {user_id} to alliance {alliance_id}")
                return True
            elif response.status_code == 401:
                logger.error(f"Invite to alliance: UNAUTHORIZED")
                return False
            elif response.status_code == 403:
                logger.error(f"Invite to alliance: FORBIDDEN")
                return False
            else:
                logger.error(f"Invite to alliance failed: {response.status_code}")
                return False

        except Exception as e:
            logger.error(f"Invite to alliance exception: {e}")
            return False

    async def get_user_profile(
        self,
        user_id: str
    ) -> Optional[Dict[str, Any]]:
        """
        Get user profile

        Args:
            user_id: User ID

        Returns:
            User profile data or None if error
        """
        try:
            response = await self.client.get(
                f"{self.base_url}/api/v1/users/{user_id}",
                headers=self._get_headers(),
                cookies=self.cookies
            )

            if response.status_code == 200:
                profile = response.json()
                logger.info(f"Fetched profile for user {user_id}")
                return profile
            elif response.status_code == 401:
                logger.error("Get user profile: UNAUTHORIZED")
                return None
            else:
                logger.error(f"Get user profile failed: {response.status_code}")
                return None

        except Exception as e:
            logger.error(f"Get user profile exception: {e}")
            return None

    async def get_my_followers(
        self,
        limit: int = 50
    ) -> Optional[List[Dict[str, Any]]]:
        """
        Get my followers

        Args:
            limit: Number of followers to fetch

        Returns:
            List of followers or None if error
        """
        try:
            params = {"limit": limit}

            response = await self.client.get(
                f"{self.base_url}/api/v1/profile/me/followers",
                headers=self._get_headers(),
                cookies=self.cookies,
                params=params
            )

            if response.status_code == 200:
                data = response.json()
                followers = data.get("followers", []) if isinstance(data, dict) else data
                logger.info(f"Fetched {len(followers)} followers")
                return followers
            elif response.status_code == 401:
                logger.error("Get followers: UNAUTHORIZED")
                return None
            else:
                logger.error(f"Get followers failed: {response.status_code}")
                return None

        except Exception as e:
            logger.error(f"Get followers exception: {e}")
            return None

    async def unfollow_user(
        self,
        user_id: str
    ) -> bool:
        """
        Unfollow a user

        Args:
            user_id: User ID to unfollow

        Returns:
            True if successful, False otherwise
        """
        try:
            response = await self.client.delete(
                f"{self.base_url}/api/v1/users/{user_id}/follow",
                headers=self._get_headers(),
                cookies=self.cookies
            )

            if response.status_code in [200, 204]:
                logger.info(f"Unfollowed user {user_id}")
                return True
            elif response.status_code == 401:
                logger.error(f"Unfollow user {user_id}: UNAUTHORIZED")
                return False
            else:
                logger.error(f"Unfollow user {user_id} failed: {response.status_code}")
                return False

        except Exception as e:
            logger.error(f"Unfollow user {user_id} exception: {e}")
            return False

    async def get_post_by_id(
        self,
        post_id: str
    ) -> Optional[Dict[str, Any]]:
        """
        Get post by ID

        Args:
            post_id: Post ID

        Returns:
            Post data or None if error
        """
        try:
            response = await self.client.get(
                f"{self.base_url}/api/v1/posts/{post_id}",
                headers=self._get_headers(),
                cookies=self.cookies
            )

            if response.status_code == 200:
                post = response.json()
                logger.info(f"Fetched post {post_id}")
                return post
            elif response.status_code == 401:
                logger.error("Get post: UNAUTHORIZED")
                return None
            else:
                logger.error(f"Get post failed: {response.status_code}")
                return None

        except Exception as e:
            logger.error(f"Get post exception: {e}")
            return None

    async def get_trending_posts(
        self,
        limit: int = 20
    ) -> Optional[List[Dict[str, Any]]]:
        """
        Get trending posts

        Args:
            limit: Number of posts to fetch

        Returns:
            List of trending posts or None if error
        """
        try:
            params = {"limit": limit}

            response = await self.client.get(
                f"{self.base_url}/api/v1/posts/trending",
                headers=self._get_headers(),
                cookies=self.cookies,
                params=params
            )

            if response.status_code == 200:
                data = response.json()
                posts = data.get("posts", []) if isinstance(data, dict) else data
                logger.info(f"Fetched {len(posts)} trending posts")
                return posts
            elif response.status_code == 401:
                logger.error("Get trending posts: UNAUTHORIZED")
                return None
            else:
                logger.error(f"Get trending posts failed: {response.status_code}")
                return None

        except Exception as e:
            logger.error(f"Get trending posts exception: {e}")
            return None

    async def send_connection_request(
        self,
        user_id: str,
        message: Optional[str] = None
    ) -> bool:
        """
        Send connection request to user

        Args:
            user_id: User ID to connect with
            message: Optional message to include

        Returns:
            True if successful, False otherwise
        """
        try:
            payload = {"user_id": user_id}
            if message:
                payload["message"] = message

            response = await self.client.post(
                f"{self.base_url}/api/v1/connections/request",
                headers=self._get_headers({"Content-Type": "application/json"}),
                cookies=self.cookies,
                json=payload
            )

            if response.status_code in [200, 201]:
                logger.info(f"Sent connection request to user {user_id}")
                return True
            elif response.status_code == 401:
                logger.error(f"Connection request: UNAUTHORIZED")
                return False
            elif response.status_code == 403:
                logger.error(f"Connection request: FORBIDDEN")
                return False
            else:
                logger.error(f"Connection request failed: {response.status_code}")
                return False

        except Exception as e:
            logger.error(f"Connection request exception: {e}")
            return False

    async def close(self):
        """Close HTTP client"""
        await self.client.aclose()
