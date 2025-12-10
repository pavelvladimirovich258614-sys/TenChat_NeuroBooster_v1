"""
TenChat API Client (Reverse-Engineered) with Enhanced Safety Features
"""
import httpx
import asyncio
import random
import time
from typing import Dict, List, Optional, Any, Tuple
from datetime import datetime, timedelta
from enum import Enum
from dataclasses import dataclass, field
from loguru import logger

try:
    from httpx_socks import AsyncProxyTransport
    SOCKS_AVAILABLE = True
except ImportError:
    SOCKS_AVAILABLE = False
    logger.warning("httpx-socks not installed, SOCKS5 proxies will not work")


class APIError(Exception):
    """Custom API error with status code"""
    def __init__(self, message: str, status_code: int = 0, is_retryable: bool = True):
        super().__init__(message)
        self.status_code = status_code
        self.is_retryable = is_retryable


class AuthExpiredError(APIError):
    """Authentication/cookies expired"""
    def __init__(self, message: str = "Authentication expired"):
        super().__init__(message, status_code=401, is_retryable=False)


class RateLimitError(APIError):
    """Rate limit hit"""
    def __init__(self, message: str = "Rate limit exceeded", retry_after: int = 300):
        super().__init__(message, status_code=429, is_retryable=True)
        self.retry_after = retry_after


class CaptchaRequiredError(APIError):
    """Captcha required - account may be flagged"""
    def __init__(self, message: str = "Captcha required"):
        super().__init__(message, status_code=403, is_retryable=False)


class ProxyError(APIError):
    """Proxy connection error"""
    def __init__(self, message: str = "Proxy connection failed"):
        super().__init__(message, status_code=0, is_retryable=True)


@dataclass
class CircuitBreakerState:
    """Circuit breaker state tracking"""
    failures: int = 0
    last_failure_time: Optional[datetime] = None
    is_open: bool = False
    
    def record_failure(self, threshold: int, reset_time: int):
        """Record a failure and potentially open the circuit"""
        self.failures += 1
        self.last_failure_time = datetime.utcnow()
        if self.failures >= threshold:
            self.is_open = True
            logger.warning(f"Circuit breaker OPEN after {self.failures} failures")
    
    def record_success(self):
        """Record success and reset failure count"""
        self.failures = 0
        self.is_open = False
    
    def should_allow_request(self, reset_time: int) -> bool:
        """Check if request should be allowed"""
        if not self.is_open:
            return True
        
        # Check if enough time has passed to try again
        if self.last_failure_time:
            elapsed = (datetime.utcnow() - self.last_failure_time).total_seconds()
            if elapsed >= reset_time:
                logger.info("Circuit breaker attempting reset (half-open state)")
                return True
        
        return False


class TenChatClient:
    """HTTP/2 client for TenChat API with retry logic and circuit breaker"""

    # Browser-like headers rotation
    ACCEPT_LANGUAGES = [
        "ru-RU,ru;q=0.9,en-US;q=0.8,en;q=0.7",
        "ru,en;q=0.9,en-GB;q=0.8",
        "ru-RU,ru;q=0.9",
    ]
    
    SEC_CH_UA_OPTIONS = [
        '"Chromium";v="122", "Not(A:Brand";v="24", "Google Chrome";v="122"',
        '"Chromium";v="121", "Not A(Brand";v="99", "Google Chrome";v="121"',
        '"Google Chrome";v="123", "Not:A-Brand";v="8", "Chromium";v="123"',
    ]

    def __init__(
        self,
        cookies: Dict[str, str],
        proxy: Dict[str, Any],
        user_agent: str,
        base_url: str = "https://tenchat.ru",
        max_retries: int = 3,
        circuit_breaker_threshold: int = 5,
        circuit_breaker_reset_time: int = 1800
    ):
        """
        Initialize TenChat client with enhanced safety features
        """
        logger.error(f"[TenChatClient.__init__] START")
        logger.error(f"[TenChatClient.__init__] cookies type: {type(cookies)}")
        logger.error(f"[TenChatClient.__init__] cookies keys: {list(cookies.keys()) if hasattr(cookies, 'keys') else 'N/A'}")
        logger.error(f"[TenChatClient.__init__] proxy type: {type(proxy)}")
        logger.error(f"[TenChatClient.__init__] proxy: {proxy}")
        
        self.base_url = base_url
        self.cookies = cookies
        self.user_agent = user_agent
        self.max_retries = max_retries
        self.circuit_breaker_threshold = circuit_breaker_threshold
        self.circuit_breaker_reset_time = circuit_breaker_reset_time
        
        # Circuit breaker state
        self._circuit_breaker = CircuitBreakerState()
        
        # Request tracking for rate limiting awareness
        self._request_timestamps: List[datetime] = []
        self._last_request_time: Optional[datetime] = None
        
        # Randomize some headers for fingerprint variation
        self._accept_language = random.choice(self.ACCEPT_LANGUAGES)
        self._sec_ch_ua = random.choice(self.SEC_CH_UA_OPTIONS)
        
        # Store proxy config for reconnection
        self._proxy_config = proxy
        
        # Create client
        logger.error(f"[TenChatClient.__init__] Calling _create_client...")
        self.client = self._create_client(proxy)
        logger.error(f"[TenChatClient.__init__] DONE")

    def _create_client(self, proxy: Dict[str, Any]) -> httpx.AsyncClient:
        """Create httpx client with appropriate proxy configuration"""
        logger.error(f"[_create_client] START - proxy: {proxy}")
        
        proxy_type = proxy.get("type", "http")
        logger.error(f"[_create_client] proxy_type: {proxy_type}")
        
        timeout = httpx.Timeout(30.0, connect=10.0)

        if proxy_type == "socks5":
            if not SOCKS_AVAILABLE:
                raise RuntimeError(
                    "SOCKS5 proxy requested but httpx-socks is not installed. "
                    "Install it with: pip install httpx-socks"
                )

            # Build proxy URL safely
            proxy_host = proxy.get('host', '')
            proxy_port = proxy.get('port', '')
            proxy_user = proxy.get('username', '')
            proxy_pass = proxy.get('password', '')
            
            logger.error(f"[_create_client] SOCKS5 - host:{proxy_host}, port:{proxy_port}, user:{proxy_user[:3]}***")
            
            proxy_url = f"socks5://{proxy_user}:{proxy_pass}@{proxy_host}:{proxy_port}"
            logger.error(f"[_create_client] Creating AsyncProxyTransport...")
            
            transport = AsyncProxyTransport.from_url(proxy_url, http2=True)
            logger.error(f"[_create_client] Transport created, creating AsyncClient...")

            client = httpx.AsyncClient(
                transport=transport,
                timeout=timeout,
                follow_redirects=True,
                verify=True
            )
            logger.error(f"[_create_client] SOCKS5 client DONE")
            return client
        else:
            # HTTP proxy (standard httpx)
            logger.error(f"[_create_client] HTTP proxy - url: {proxy.get('url')}")
            client = httpx.AsyncClient(
                http2=True,
                proxies=proxy.get("url"),
                timeout=timeout,
                follow_redirects=True,
                verify=True
            )
            logger.error(f"[_create_client] HTTP client DONE")
            return client

    def _get_headers(self, extra_headers: Optional[Dict[str, str]] = None) -> Dict[str, str]:
        """
        Get default headers for requests with browser-like fingerprint
        """
        logger.error(f"[_get_headers] START")
        logger.error(f"[_get_headers] cookies type: {type(self.cookies)}")
        
        headers = {
            "User-Agent": self.user_agent,
            "Accept": "application/json, text/plain, */*",
            "Accept-Language": self._accept_language,
            "Accept-Encoding": "gzip, deflate, br",
            "Connection": "keep-alive",
            "Sec-Fetch-Dest": "empty",
            "Sec-Fetch-Mode": "cors",
            "Sec-Fetch-Site": "same-origin",
            "Sec-Ch-Ua": self._sec_ch_ua,
            "Sec-Ch-Ua-Mobile": "?0",
            "Sec-Ch-Ua-Platform": '"Windows"',
            "Referer": f"{self.base_url}/",
            "Origin": self.base_url,
            "DNT": "1",
            "Cache-Control": "no-cache",
            "Pragma": "no-cache",
        }

        # Add CSRF token if available (case-insensitive search)
        logger.error(f"[_get_headers] Iterating over cookies...")
        try:
            if hasattr(self.cookies, 'items'):
                for key, value in self.cookies.items():
                    key_lower = str(key).lower()
                    if key_lower == "csrftoken":
                        headers["X-CSRFToken"] = str(value)
                    elif key_lower == "x-xsrf-token":
                        headers["X-XSRF-TOKEN"] = str(value)
            else:
                logger.error(f"[_get_headers] WARNING: cookies has no items() method!")
        except Exception as e:
            logger.error(f"[_get_headers] Error iterating cookies: {type(e).__name__}: {e}")

        # Merge extra headers
        if extra_headers:
            headers.update(extra_headers)

        logger.error(f"[_get_headers] DONE - returning {len(headers)} headers")
        return headers

    async def _execute_with_retry(
        self,
        method: str,
        endpoint: str,
        **kwargs
    ) -> httpx.Response:
        """
        Execute HTTP request with retry logic and circuit breaker

        Args:
            method: HTTP method (GET, POST, DELETE, etc.)
            endpoint: API endpoint
            **kwargs: Additional arguments for httpx

        Returns:
            httpx.Response object

        Raises:
            APIError subclasses on failure
        """
        # Check circuit breaker
        if not self._circuit_breaker.should_allow_request(self.circuit_breaker_reset_time):
            raise APIError(
                "Circuit breaker is open - too many recent failures",
                is_retryable=False
            )

        url = f"{self.base_url}{endpoint}"
        last_exception = None
        
        for attempt in range(self.max_retries):
            try:
                # Add small random delay between retries (human-like)
                if attempt > 0:
                    delay = min(
                        5 * (2 ** attempt) + random.uniform(0, 2),
                        300  # Max 5 min
                    )
                    logger.info(f"Retry {attempt + 1}/{self.max_retries} after {delay:.1f}s")
                    await asyncio.sleep(delay)

                # Execute request
                self._last_request_time = datetime.utcnow()
                response = await self.client.request(
                    method,
                    url,
                    headers=self._get_headers(kwargs.pop("extra_headers", None)),
                    cookies=self.cookies,
                    **kwargs
                )

                # Check response status
                if response.status_code == 401:
                    self._circuit_breaker.record_failure(
                        self.circuit_breaker_threshold,
                        self.circuit_breaker_reset_time
                    )
                    raise AuthExpiredError()
                
                elif response.status_code == 403:
                    # Check if it's captcha or ban
                    try:
                        body = response.json()
                        if "captcha" in str(body).lower():
                            raise CaptchaRequiredError()
                    except:
                        pass
                    raise CaptchaRequiredError("Access forbidden - possible captcha or ban")
                
                elif response.status_code == 429:
                    retry_after = int(response.headers.get("Retry-After", 300))
                    raise RateLimitError(retry_after=retry_after)
                
                elif response.status_code >= 500:
                    # Server error - retryable
                    raise APIError(
                        f"Server error: {response.status_code}",
                        status_code=response.status_code,
                        is_retryable=True
                    )
                
                elif response.status_code >= 400:
                    # Client error - not retryable
                    raise APIError(
                        f"Client error: {response.status_code}",
                        status_code=response.status_code,
                        is_retryable=False
                    )

                # Success!
                self._circuit_breaker.record_success()
                return response

            except (httpx.ConnectError, httpx.ConnectTimeout, httpx.ProxyError) as e:
                last_exception = ProxyError(f"Connection failed: {e}")
                self._circuit_breaker.record_failure(
                    self.circuit_breaker_threshold,
                    self.circuit_breaker_reset_time
                )
                logger.warning(f"Proxy/connection error (attempt {attempt + 1}): {e}")
                
                # Try to recreate client on connection errors
                if attempt < self.max_retries - 1:
                    try:
                        await self.client.aclose()
                        self.client = self._create_client(self._proxy_config)
                        logger.info("Recreated HTTP client after connection error")
                    except Exception as recreate_error:
                        logger.error(f"Failed to recreate client: {recreate_error}")

            except httpx.TimeoutException as e:
                last_exception = APIError(f"Request timeout: {e}", is_retryable=True)
                logger.warning(f"Timeout (attempt {attempt + 1}): {e}")

            except (AuthExpiredError, CaptchaRequiredError) as e:
                # Non-retryable errors
                raise

            except RateLimitError as e:
                # Wait and retry for rate limits
                logger.warning(f"Rate limited, waiting {e.retry_after}s")
                await asyncio.sleep(e.retry_after)
                last_exception = e

            except APIError as e:
                if not e.is_retryable:
                    raise
                last_exception = e
                self._circuit_breaker.record_failure(
                    self.circuit_breaker_threshold,
                    self.circuit_breaker_reset_time
                )

            except Exception as e:
                last_exception = APIError(f"Unexpected error: {e}", is_retryable=True)
                logger.error(f"Unexpected error (attempt {attempt + 1}): {e}")
                self._circuit_breaker.record_failure(
                    self.circuit_breaker_threshold,
                    self.circuit_breaker_reset_time
                )

        # All retries exhausted
        if last_exception:
            raise last_exception
        raise APIError("All retries exhausted")

    async def check_auth(self) -> bool:
        """
        Check if authentication is valid
        """
        logger.error("[check_auth] START")
        logger.error(f"[check_auth] self.cookies type: {type(self.cookies)}")
        logger.error(f"[check_auth] self.cookies keys: {list(self.cookies.keys()) if hasattr(self.cookies, 'keys') else 'NOT A DICT!'}")
        
        try:
            logger.error("[check_auth] Calling _execute_with_retry...")
            response = await self._execute_with_retry("GET", "/api/v1/profile/me")
            logger.error(f"[check_auth] Response status: {response.status_code}")
            if response.status_code == 200:
                logger.info("Authentication check: SUCCESS")
                return True
            return False
        except AuthExpiredError:
            logger.warning("Authentication check: UNAUTHORIZED - cookies expired")
            return False
        except CaptchaRequiredError:
            logger.warning("Authentication check: CAPTCHA required")
            return False
        except Exception as e:
            logger.error(f"[check_auth] EXCEPTION: {type(e).__name__}: {e}")
            import traceback
            logger.error(f"[check_auth] Traceback:\n{traceback.format_exc()}")
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

            response = await self._execute_with_retry(
                "GET",
                "/api/v1/feed",
                params=params
            )

            if response.status_code == 200:
                data = response.json()
                posts = data.get("posts", []) if isinstance(data, dict) else data
                logger.info(f"Fetched {len(posts)} posts from feed")
                return posts
            return None

        except AuthExpiredError:
            logger.error("Get feed: UNAUTHORIZED - cookies expired")
            raise
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
            response = await self._execute_with_retry(
                "POST",
                f"/api/v1/posts/{post_id}/like",
                extra_headers={"Content-Type": "application/json"},
                json={}
            )

            if response.status_code in [200, 201]:
                logger.info(f"Liked post {post_id}")
                return True
            return False

        except AuthExpiredError:
            logger.error(f"Like post {post_id}: UNAUTHORIZED")
            raise
        except CaptchaRequiredError:
            logger.error(f"Like post {post_id}: CAPTCHA required")
            raise
        except RateLimitError:
            logger.error(f"Like post {post_id}: Rate limited")
            raise
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
            response = await self._execute_with_retry(
                "POST",
                f"/api/v1/users/{user_id}/follow",
                extra_headers={"Content-Type": "application/json"},
                json={}
            )

            if response.status_code in [200, 201]:
                logger.info(f"Followed user {user_id}")
                return True
            return False

        except AuthExpiredError:
            logger.error(f"Follow user {user_id}: UNAUTHORIZED")
            raise
        except CaptchaRequiredError:
            logger.error(f"Follow user {user_id}: FORBIDDEN - captcha required")
            raise
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

            response = await self._execute_with_retry(
                "POST",
                "/api/v1/articles",
                extra_headers={"Content-Type": "application/json"},
                json=article_data
            )

            if response.status_code in [200, 201]:
                data = response.json()
                post_id = data.get("id") or data.get("post_id")
                logger.info(f"Published article: {post_id}")
                return post_id
            return None

        except AuthExpiredError:
            logger.error("Post article: UNAUTHORIZED")
            raise
        except CaptchaRequiredError:
            logger.error("Post article: CAPTCHA required")
            raise
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
                response = await self._execute_with_retry(
                    "POST",
                    "/api/v1/upload/image",
                    files=files
                )

            if response.status_code in [200, 201]:
                data = response.json()
                image_url = data.get("url")
                logger.info(f"Uploaded image: {image_url}")
                return image_url
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
            response = await self._execute_with_retry(
                "POST",
                f"/api/v1/posts/{post_id}/comments",
                extra_headers={"Content-Type": "application/json"},
                json={"text": comment_text}
            )

            if response.status_code in [200, 201]:
                logger.info(f"Commented on post {post_id}")
                return True
            return False

        except AuthExpiredError:
            logger.error(f"Comment on post {post_id}: UNAUTHORIZED")
            raise
        except CaptchaRequiredError:
            logger.error(f"Comment on post {post_id}: CAPTCHA required")
            raise
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

            response = await self._execute_with_retry(
                "GET",
                "/api/v1/users/search",
                params=params
            )

            if response.status_code == 200:
                data = response.json()
                users = data.get("users", []) if isinstance(data, dict) else data
                logger.info(f"Found {len(users)} users for query '{query}'")
                return users
            return None

        except AuthExpiredError:
            logger.error("Search users: UNAUTHORIZED")
            raise
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
            response = await self._execute_with_retry(
                "POST",
                "/api/v1/messages",
                extra_headers={"Content-Type": "application/json"},
                json={
                    "recipient_id": user_id,
                    "text": message_text
                }
            )

            if response.status_code in [200, 201]:
                logger.info(f"Sent message to user {user_id}")
                return True
            return False

        except AuthExpiredError:
            logger.error(f"Send message to {user_id}: UNAUTHORIZED")
            raise
        except CaptchaRequiredError:
            logger.error(f"Send message to {user_id}: FORBIDDEN - captcha required")
            raise
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

            response = await self._execute_with_retry(
                "GET",
                "/api/v1/messages/inbox",
                params=params
            )

            if response.status_code == 200:
                data = response.json()
                messages = data.get("messages", []) if isinstance(data, dict) else data
                logger.info(f"Fetched {len(messages)} inbox messages")
                return messages
            return None

        except AuthExpiredError:
            logger.error("Get inbox: UNAUTHORIZED")
            raise
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
            response = await self._execute_with_retry(
                "POST",
                f"/api/v1/alliances/{alliance_id}/invite",
                extra_headers={"Content-Type": "application/json"},
                json={"user_id": user_id}
            )

            if response.status_code in [200, 201]:
                logger.info(f"Invited user {user_id} to alliance {alliance_id}")
                return True
            return False

        except AuthExpiredError:
            logger.error("Invite to alliance: UNAUTHORIZED")
            raise
        except CaptchaRequiredError:
            logger.error("Invite to alliance: FORBIDDEN - captcha required")
            raise
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
            response = await self._execute_with_retry(
                "GET",
                f"/api/v1/users/{user_id}"
            )

            if response.status_code == 200:
                profile = response.json()
                logger.debug(f"Fetched profile for user {user_id}")
                return profile
            return None

        except AuthExpiredError:
            logger.error("Get user profile: UNAUTHORIZED")
            raise
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

            response = await self._execute_with_retry(
                "GET",
                "/api/v1/profile/me/followers",
                params=params
            )

            if response.status_code == 200:
                data = response.json()
                followers = data.get("followers", []) if isinstance(data, dict) else data
                logger.info(f"Fetched {len(followers)} followers")
                return followers
            return None

        except AuthExpiredError:
            logger.error("Get followers: UNAUTHORIZED")
            raise
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
            response = await self._execute_with_retry(
                "DELETE",
                f"/api/v1/users/{user_id}/follow"
            )

            if response.status_code in [200, 204]:
                logger.info(f"Unfollowed user {user_id}")
                return True
            return False

        except AuthExpiredError:
            logger.error(f"Unfollow user {user_id}: UNAUTHORIZED")
            raise
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
            response = await self._execute_with_retry(
                "GET",
                f"/api/v1/posts/{post_id}"
            )

            if response.status_code == 200:
                post = response.json()
                logger.debug(f"Fetched post {post_id}")
                return post
            return None

        except AuthExpiredError:
            logger.error("Get post: UNAUTHORIZED")
            raise
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

            response = await self._execute_with_retry(
                "GET",
                "/api/v1/posts/trending",
                params=params
            )

            if response.status_code == 200:
                data = response.json()
                posts = data.get("posts", []) if isinstance(data, dict) else data
                logger.info(f"Fetched {len(posts)} trending posts")
                return posts
            return None

        except AuthExpiredError:
            logger.error("Get trending posts: UNAUTHORIZED")
            raise
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

            response = await self._execute_with_retry(
                "POST",
                "/api/v1/connections/request",
                extra_headers={"Content-Type": "application/json"},
                json=payload
            )

            if response.status_code in [200, 201]:
                logger.info(f"Sent connection request to user {user_id}")
                return True
            return False

        except AuthExpiredError:
            logger.error("Connection request: UNAUTHORIZED")
            raise
        except CaptchaRequiredError:
            logger.error("Connection request: FORBIDDEN - captcha required")
            raise
        except Exception as e:
            logger.error(f"Connection request exception: {e}")
            return False

    async def view_profile(self, user_id: str) -> bool:
        """
        Simulate viewing a user profile (noise action for human-like behavior)
        
        Args:
            user_id: User ID to view
            
        Returns:
            True if successful
        """
        try:
            await self.get_user_profile(user_id)
            return True
        except:
            return False

    async def scroll_feed(self, feed_type: str = "all") -> bool:
        """
        Simulate scrolling through feed (noise action for human-like behavior)
        
        Args:
            feed_type: Type of feed
            
        Returns:
            True if successful
        """
        try:
            # Get a few posts without doing anything
            await self.get_feed(feed_type=feed_type, limit=5)
            return True
        except:
            return False

    def get_circuit_breaker_status(self) -> Dict[str, Any]:
        """Get current circuit breaker status for monitoring"""
        return {
            "is_open": self._circuit_breaker.is_open,
            "failures": self._circuit_breaker.failures,
            "last_failure": self._circuit_breaker.last_failure_time.isoformat() if self._circuit_breaker.last_failure_time else None
        }

    async def close(self):
        """Close HTTP client gracefully"""
        try:
            await self.client.aclose()
            logger.debug("HTTP client closed")
        except Exception as e:
            logger.warning(f"Error closing HTTP client: {e}")
