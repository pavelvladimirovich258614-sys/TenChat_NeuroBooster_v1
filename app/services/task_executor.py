"""
Task Executor with Enhanced Human Emulation and Safety Features
"""
import asyncio
import random
import json
from datetime import datetime, timedelta
from typing import Dict, Optional, List, Any, Tuple
from loguru import logger
from sqlalchemy import select, and_, func
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.database import Account, Action, Task, DailyStats
from app.services.tenchat_client import (
    TenChatClient, 
    AuthExpiredError, 
    CaptchaRequiredError, 
    RateLimitError,
    ProxyError,
    APIError
)
from app.services.ai_generator import AIGenerator
from app.utils.cookies_parser import CookiesParser
from app.utils.proxy_handler import ProxyHandler
from config.settings import settings


class TaskExecutor:
    """Execute tasks with advanced human emulation and safety features"""

    def __init__(
        self,
        db_session: AsyncSession,
        ai_generator: AIGenerator
    ):
        """
        Initialize task executor

        Args:
            db_session: Database session
            ai_generator: AI generator instance
        """
        self.db = db_session
        self.ai_generator = ai_generator
        self._session_action_count = 0  # Track actions in current session

    async def _check_activity_window(self) -> bool:
        """Check if current time is within allowed activity window"""
        current_hour = datetime.now().hour
        if not settings.is_within_activity_window(current_hour):
            logger.warning(f"Outside activity window ({settings.ACTIVITY_WINDOW_START}-{settings.ACTIVITY_WINDOW_END}h)")
            return False
        return True
    
    async def _human_delay(self, risky: bool = False, action_name: str = "action"):
        """
        Apply human-like delay with session breaks
        
        Args:
            risky: Whether this is a risky action (longer delay)
            action_name: Name of action for logging
        """
        # Check if we need a session break
        self._session_action_count += 1
        
        if settings.should_take_session_break(self._session_action_count):
            break_duration = settings.get_session_break_duration()
            logger.info(f"Taking session break ({break_duration}s) after {self._session_action_count} actions")
            await asyncio.sleep(break_duration)
            self._session_action_count = 0
        else:
            # Normal delay
            delay = settings.get_random_delay(risky=risky)
            logger.debug(f"[{action_name}] Waiting {delay:.1f}s...")
            await asyncio.sleep(delay)
    
    async def _simulate_reading(self, content_length: int = 100):
        """Simulate reading content before acting"""
        # Longer content = longer read time
        base_delay = settings.get_read_delay()
        length_factor = min(content_length / 500, 2.0)  # Cap at 2x
        delay = base_delay * (1 + length_factor * 0.5)
        await asyncio.sleep(delay)
    
    async def _maybe_noise_action(self, client: TenChatClient):
        """Maybe perform a noise action for human-like behavior"""
        if settings.ENABLE_NOISE_ACTIONS and random.random() < settings.NOISE_ACTION_PROBABILITY:
            noise_actions = [
                lambda: client.scroll_feed(),
                lambda: client.get_trending_posts(limit=3),
            ]
            action = random.choice(noise_actions)
            try:
                await action()
                logger.debug("Performed noise action")
                await asyncio.sleep(random.uniform(2, 5))
            except:
                pass  # Noise actions failures are ok
    
    async def execute_task(self, task: Task) -> bool:
        """
        Execute a task with enhanced error handling

        Args:
            task: Task to execute

        Returns:
            True if successful, False otherwise
        """
        logger.info(f"Executing task {task.id}: {task.task_type}")
        
        # Reset session counter for new task
        self._session_action_count = 0

        # Check activity window
        if not await self._check_activity_window():
            task.status = "pending"
            task.error_message = "Outside activity window, will retry later"
            await self.db.commit()
            return False

        # Update task status
        task.status = "running"
        task.started_at = datetime.utcnow()
        await self.db.commit()

        try:
            # Get account
            result = await self.db.execute(
                select(Account).where(Account.id == task.account_id)
            )
            account = result.scalar_one_or_none()

            if not account:
                raise ValueError(f"Account {task.account_id} not found")

            # Check account status
            if account.status != "active":
                raise ValueError(f"Account {account.name} is not active: {account.status}")

            # Execute task based on type
            if task.task_type == "warmup":
                success = await self._execute_warmup(account, task)
            elif task.task_type == "ai_post":
                success = await self._execute_ai_post(account, task)
            elif task.task_type == "mass_follow":
                success = await self._execute_mass_follow(account, task)
            elif task.task_type == "ai_comments":
                success = await self._execute_ai_comments(account, task)
            elif task.task_type == "connections":
                success = await self._execute_connections(account, task)
            elif task.task_type == "dm_followers":
                success = await self._execute_dm_followers(account, task)
            elif task.task_type == "dm_cold":
                success = await self._execute_dm_cold(account, task)
            elif task.task_type == "alliance_invites":
                success = await self._execute_alliance_invites(account, task)
            elif task.task_type == "parse_users":
                success = await self._execute_parse_users(account, task)
            elif task.task_type == "auto_reply":
                success = await self._execute_auto_reply(account, task)
            else:
                raise ValueError(f"Unknown task type: {task.task_type}")

            # Update task
            if success:
                task.status = "completed"
                task.progress = 100
                task.completed_at = datetime.utcnow()
            else:
                task.status = "failed"
                task.error_message = "Task execution failed"

            await self.db.commit()
            return success

        except AuthExpiredError as e:
            logger.error(f"Task {task.id} failed: Authentication expired")
            task.status = "failed"
            task.error_message = "🔒 Cookies expired - требуется повторная авторизация"
            # Update account status
            account.status = "cookies_expired"
            await self.db.commit()
            return False
        
        except CaptchaRequiredError as e:
            logger.error(f"Task {task.id} failed: Captcha required")
            task.status = "failed"
            task.error_message = "⚠️ Требуется капча - аккаунт временно заблокирован"
            account.status = "captcha"
            await self.db.commit()
            return False
        
        except RateLimitError as e:
            logger.warning(f"Task {task.id}: Rate limited, will retry")
            task.status = "pending"
            task.error_message = f"Rate limit - повтор через {e.retry_after}s"
            await self.db.commit()
            return False
        
        except ProxyError as e:
            logger.error(f"Task {task.id} failed: Proxy error - {e}")
            task.status = "failed"
            task.error_message = f"🌐 Ошибка прокси: {str(e)[:100]}"
            account.status = "proxy_error"
            await self.db.commit()
            return False

        except Exception as e:
            logger.error(f"Task {task.id} failed: {e}")
            task.status = "failed"
            task.error_message = str(e)[:500]
            await self.db.commit()
            return False

    async def _execute_warmup(self, account: Account, task: Task) -> bool:
        """
        Execute warmup task (liking feed) with human-like behavior

        Args:
            account: Account to use
            task: Task with parameters

        Returns:
            True if successful
        """
        params = task.parameters or {}
        num_likes = params.get("num_likes", 10)
        feed_type = params.get("feed_type", "all")

        logger.info(f"Warmup task: {num_likes} likes from {feed_type} feed")

        # Check daily limits
        if not await self._check_daily_limit(account.id, "like", num_likes):
            raise ValueError("Daily like limit exceeded")

        # Create TenChat client
        client = await self._create_client(account)

        try:
            # Check auth
            if not await client.check_auth():
                raise AuthExpiredError()

            # Get feed
            posts = await client.get_feed(feed_type=feed_type, limit=num_likes * 2)
            if not posts:
                raise ValueError("Failed to fetch feed")

            # Randomize order if enabled
            if settings.RANDOMIZE_ACTION_ORDER:
                random.shuffle(posts)

            # Like posts with human-like delays
            liked_count = 0
            posts_to_process = posts[:num_likes]
            
            for i, post in enumerate(posts_to_process):
                post_id = post.get("id") or post.get("post_id")
                post_content = post.get("text") or post.get("content", "")
                
                if not post_id:
                    continue

                # Simulate reading the post
                await self._simulate_reading(len(post_content))
                
                # Maybe do a noise action
                await self._maybe_noise_action(client)

                # Like post
                try:
                    success = await client.like_post(str(post_id))
                except (AuthExpiredError, CaptchaRequiredError):
                    raise
                except Exception as e:
                    logger.warning(f"Failed to like post {post_id}: {e}")
                    success = False

                # Log action
                action = Action(
                    account_id=account.id,
                    action_type="like",
                    target_id=str(post_id),
                    success=success
                )
                self.db.add(action)

                if success:
                    liked_count += 1
                    await self._increment_daily_stats(account.id, "like")
                    logger.info(f"[{account.name}] ✓ Liked post {post_id}")

                # Update task progress
                task.progress = int((i + 1) / len(posts_to_process) * 100)
                await self.db.commit()

                # Human-like delay (no delay after last action)
                if i < len(posts_to_process) - 1:
                    await self._human_delay(risky=False, action_name=f"like_{i+1}")

            task.result = f"Liked {liked_count}/{num_likes} posts"
            logger.info(f"Warmup completed: {liked_count}/{num_likes} likes")

            return liked_count > 0

        finally:
            await client.close()

    async def _execute_ai_post(self, account: Account, task: Task) -> bool:
        """
        Execute AI post task with human-like timing

        Args:
            account: Account to use
            task: Task with parameters

        Returns:
            True if successful
        """
        params = task.parameters or {}

        # Support both old format (single topic) and new format (topics array)
        topics = params.get("topics", [])
        if not topics:
            # Fallback to old format
            single_topic = params.get("topic", "")
            if single_topic:
                topics = [single_topic]

        style = params.get("style", "professional")
        mood = params.get("mood", "expert")

        if not topics:
            raise ValueError("Topic is required for AI post task")

        # Use first topic (UI creates separate tasks for each topic)
        topic = topics[0] if isinstance(topics, list) else topics

        logger.info(f"AI post task: {topic} (style: {style}, mood: {mood})")

        # Check daily limits
        if not await self._check_daily_limit(account.id, "post", 1):
            raise ValueError("Daily post limit exceeded")

        # Generate article with mood
        task.progress = 10
        await self.db.commit()
        
        logger.info("Generating article with AI...")
        article = await self.ai_generator.generate_article(
            topic=topic,
            style=style,
            mood=mood
        )
        if not article:
            raise ValueError("Failed to generate article")

        logger.info(f"Generated article ({mood} mood): {article['title'][:50]}...")
        task.progress = 40
        await self.db.commit()

        # Create TenChat client
        client = await self._create_client(account)

        try:
            # Check auth
            if not await client.check_auth():
                raise AuthExpiredError()

            task.progress = 50
            await self.db.commit()
            
            # Simulate "writing" time - humans don't post instantly
            writing_delay = random.uniform(10, 30)
            logger.debug(f"Simulating writing time ({writing_delay:.0f}s)...")
            await asyncio.sleep(writing_delay)

            # Post article
            post_id = await client.post_article(
                title=article["title"],
                text=article["text"],
                hashtags=article["hashtags"]
            )

            if not post_id:
                raise ValueError("Failed to post article")

            # Log action
            action = Action(
                account_id=account.id,
                action_type="post",
                target_id=str(post_id),
                success=True
            )
            self.db.add(action)
            await self._increment_daily_stats(account.id, "post")

            task.progress = 100
            task.result = f"✅ Опубликовано ({mood}): {article['title'][:50]}..."
            await self.db.commit()

            logger.info(f"AI post completed ({mood} mood): {post_id}")
            return True

        finally:
            await client.close()

    async def _create_client(self, account: Account) -> TenChatClient:
        """
        Create TenChat client for account

        Args:
            account: Account

        Returns:
            TenChat client instance
        """
        # Parse cookies
        cookies = CookiesParser.parse_json(account.cookies_json)

        # Parse proxy
        proxy = ProxyHandler.get_httpx_proxy_config(account.proxy)

        # Create client
        client = TenChatClient(
            cookies=cookies,
            proxy=proxy,
            user_agent=account.user_agent,
            base_url=settings.TENCHAT_BASE_URL
        )

        return client

    async def _check_daily_limit(
        self,
        account_id: int,
        action_type: str,
        count: int = 1
    ) -> bool:
        """
        Check if action is within daily limits

        Args:
            account_id: Account ID
            action_type: Action type (like, follow, post)
            count: Number of actions to perform

        Returns:
            True if within limits
        """
        today = datetime.utcnow().date()

        # Get today's stats
        result = await self.db.execute(
            select(DailyStats).where(
                and_(
                    DailyStats.account_id == account_id,
                    func.date(DailyStats.date) == today
                )
            )
        )
        stats = result.scalar_one_or_none()

        if not stats:
            return True  # No stats yet, within limits

        # Check limits
        if action_type == "like":
            current = stats.likes_count
            limit = settings.DAILY_LIMIT_LIKES
        elif action_type == "follow":
            current = stats.follows_count
            limit = settings.DAILY_LIMIT_FOLLOWS
        elif action_type == "post":
            current = stats.posts_count
            limit = settings.DAILY_LIMIT_POSTS
        else:
            return True

        return (current + count) <= limit

    async def _increment_daily_stats(
        self,
        account_id: int,
        action_type: str
    ):
        """
        Increment daily statistics

        Args:
            account_id: Account ID
            action_type: Action type
        """
        today = datetime.utcnow().replace(hour=0, minute=0, second=0, microsecond=0)

        # Get or create today's stats
        result = await self.db.execute(
            select(DailyStats).where(
                and_(
                    DailyStats.account_id == account_id,
                    DailyStats.date == today
                )
            )
        )
        stats = result.scalar_one_or_none()

        if not stats:
            stats = DailyStats(
                account_id=account_id,
                date=today
            )
            self.db.add(stats)

        # Increment counter
        if action_type == "like":
            stats.likes_count += 1
        elif action_type == "follow":
            stats.follows_count += 1
        elif action_type == "post":
            stats.posts_count += 1
        elif action_type == "comment":
            stats.comments_count += 1

        await self.db.commit()

    async def _execute_mass_follow(self, account: Account, task: Task) -> bool:
        """
        Execute mass follow task

        Args:
            account: Account to use
            task: Task with parameters

        Returns:
            True if successful
        """
        params = task.parameters or {}
        search_query = params.get("search_query", "")
        num_follows = params.get("num_follows", 10)

        logger.info(f"Mass follow task: {num_follows} follows for query '{search_query}'")

        # Check daily limits
        if not await self._check_daily_limit(account.id, "follow", num_follows):
            raise ValueError("Daily follow limit exceeded")

        # Create TenChat client
        client = await self._create_client(account)

        try:
            # Check auth
            if not await client.check_auth():
                account.status = "cookies_expired"
                await self.db.commit()
                raise ValueError("Authentication failed - cookies expired")

            # Search users
            users = await client.search_users(search_query, limit=num_follows * 2)
            if not users:
                raise ValueError("Failed to find users")

            # Follow users with delays
            followed_count = 0
            for i, user in enumerate(users[:num_follows]):
                user_id = user.get("id") or user.get("user_id")
                if not user_id:
                    continue

                # Follow user
                success = await client.follow_user(str(user_id))

                # Log action
                action = Action(
                    account_id=account.id,
                    action_type="follow",
                    target_id=str(user_id),
                    success=success
                )
                self.db.add(action)

                if success:
                    followed_count += 1
                    await self._increment_daily_stats(account.id, "follow")

                    # Update task progress
                    task.progress = int((i + 1) / num_follows * 100)
                    await self.db.commit()

                    # Human-like delay
                    if i < num_follows - 1:
                        delay = random.randint(
                            settings.MIN_ACTION_DELAY,
                            settings.MAX_ACTION_DELAY
                        )
                        logger.info(f"[{account.name}] Followed user {user_id}. Pausing {delay} seconds...")
                        await asyncio.sleep(delay)

            task.result = f"Followed {followed_count}/{num_follows} users"
            logger.info(f"Mass follow completed: {followed_count}/{num_follows} follows")

            return followed_count > 0

        finally:
            await client.close()

    async def _execute_ai_comments(self, account: Account, task: Task) -> bool:
        """
        Execute AI comments task

        Args:
            account: Account to use
            task: Task with parameters

        Returns:
            True if successful
        """
        params = task.parameters or {}
        num_comments = params.get("num_comments", 5)
        feed_type = params.get("feed_type", "all")

        logger.info(f"AI comments task: {num_comments} comments on {feed_type} feed")

        # Check daily limits
        if not await self._check_daily_limit(account.id, "comment", num_comments):
            raise ValueError("Daily comment limit exceeded")

        # Create TenChat client
        client = await self._create_client(account)

        try:
            # Check auth
            if not await client.check_auth():
                account.status = "cookies_expired"
                await self.db.commit()
                raise ValueError("Authentication failed - cookies expired")

            # Get feed
            posts = await client.get_feed(feed_type=feed_type, limit=num_comments * 2)
            if not posts:
                raise ValueError("Failed to fetch feed")

            # Comment on posts with AI
            commented_count = 0
            for i, post in enumerate(posts[:num_comments]):
                post_id = post.get("id") or post.get("post_id")
                post_content = post.get("text") or post.get("content", "")

                if not post_id or not post_content:
                    continue

                # Generate AI comment
                comment_text = await self.ai_generator.generate_comment(post_content)
                if not comment_text:
                    logger.warning(f"Failed to generate comment for post {post_id}")
                    continue

                # Post comment
                success = await client.comment_on_post(str(post_id), comment_text)

                # Log action
                action = Action(
                    account_id=account.id,
                    action_type="comment",
                    target_id=str(post_id),
                    success=success
                )
                self.db.add(action)

                if success:
                    commented_count += 1
                    await self._increment_daily_stats(account.id, "comment")

                    # Update task progress
                    task.progress = int((i + 1) / num_comments * 100)
                    await self.db.commit()

                    # Human-like delay
                    if i < num_comments - 1:
                        delay = random.randint(
                            settings.MIN_ACTION_DELAY,
                            settings.MAX_ACTION_DELAY
                        )
                        logger.info(f"[{account.name}] Commented on post {post_id}. Pausing {delay} seconds...")
                        await asyncio.sleep(delay)

            task.result = f"Commented on {commented_count}/{num_comments} posts"
            logger.info(f"AI comments completed: {commented_count}/{num_comments} comments")

            return commented_count > 0

        finally:
            await client.close()

    async def _execute_connections(self, account: Account, task: Task) -> bool:
        """
        Execute connection requests task

        Args:
            account: Account to use
            task: Task with parameters

        Returns:
            True if successful
        """
        params = task.parameters or {}
        search_query = params.get("search_query", "")
        num_requests = params.get("num_requests", 10)

        logger.info(f"Connections task: {num_requests} connection requests")

        # Create TenChat client
        client = await self._create_client(account)

        try:
            # Check auth
            if not await client.check_auth():
                account.status = "cookies_expired"
                await self.db.commit()
                raise ValueError("Authentication failed - cookies expired")

            # Search users
            users = await client.search_users(search_query, limit=num_requests * 2)
            if not users:
                raise ValueError("Failed to find users")

            # Send connection requests
            sent_count = 0
            for i, user in enumerate(users[:num_requests]):
                user_id = user.get("id") or user.get("user_id")
                if not user_id:
                    continue

                # Send connection request
                success = await client.send_connection_request(str(user_id))

                # Log action
                action = Action(
                    account_id=account.id,
                    action_type="connection",
                    target_id=str(user_id),
                    success=success
                )
                self.db.add(action)

                if success:
                    sent_count += 1

                    # Update task progress
                    task.progress = int((i + 1) / num_requests * 100)
                    await self.db.commit()

                    # Human-like delay
                    if i < num_requests - 1:
                        delay = random.randint(
                            settings.MIN_ACTION_DELAY,
                            settings.MAX_ACTION_DELAY
                        )
                        logger.info(f"[{account.name}] Sent connection request to {user_id}. Pausing {delay} seconds...")
                        await asyncio.sleep(delay)

            task.result = f"Sent {sent_count}/{num_requests} connection requests"
            logger.info(f"Connections completed: {sent_count}/{num_requests} requests")

            return sent_count > 0

        finally:
            await client.close()

    async def _execute_dm_followers(self, account: Account, task: Task) -> bool:
        """
        Execute DM to followers task

        Args:
            account: Account to use
            task: Task with parameters

        Returns:
            True if successful
        """
        params = task.parameters or {}
        message_purpose = params.get("message_purpose", "networking")
        num_messages = params.get("num_messages", 10)

        logger.info(f"DM followers task: {num_messages} messages")

        # Create TenChat client
        client = await self._create_client(account)

        try:
            # Check auth
            if not await client.check_auth():
                account.status = "cookies_expired"
                await self.db.commit()
                raise ValueError("Authentication failed - cookies expired")

            # Get followers
            followers = await client.get_my_followers(limit=num_messages * 2)
            if not followers:
                raise ValueError("Failed to fetch followers")

            # Send messages
            sent_count = 0
            for i, follower in enumerate(followers[:num_messages]):
                user_id = follower.get("id") or follower.get("user_id")
                user_name = follower.get("name", "")
                user_position = follower.get("position", "")

                if not user_id:
                    continue

                # Generate AI message
                message_text = await self.ai_generator.generate_welcome_message(
                    recipient_name=user_name,
                    recipient_position=user_position
                )
                if not message_text:
                    logger.warning(f"Failed to generate message for user {user_id}")
                    continue

                # Send message
                success = await client.send_message(str(user_id), message_text)

                # Log action
                action = Action(
                    account_id=account.id,
                    action_type="message",
                    target_id=str(user_id),
                    success=success
                )
                self.db.add(action)

                if success:
                    sent_count += 1

                    # Update task progress
                    task.progress = int((i + 1) / num_messages * 100)
                    await self.db.commit()

                    # Human-like delay
                    if i < num_messages - 1:
                        delay = random.randint(
                            settings.MIN_ACTION_DELAY * 2,
                            settings.MAX_ACTION_DELAY * 2
                        )
                        logger.info(f"[{account.name}] Sent message to {user_id}. Pausing {delay} seconds...")
                        await asyncio.sleep(delay)

            task.result = f"Sent {sent_count}/{num_messages} messages"
            logger.info(f"DM followers completed: {sent_count}/{num_messages} messages")

            return sent_count > 0

        finally:
            await client.close()

    async def _execute_dm_cold(self, account: Account, task: Task) -> bool:
        """
        Execute cold DM task

        Args:
            account: Account to use
            task: Task with parameters

        Returns:
            True if successful
        """
        params = task.parameters or {}
        search_query = params.get("search_query", "")
        message_purpose = params.get("message_purpose", "networking")
        num_messages = params.get("num_messages", 5)

        logger.info(f"Cold DM task: {num_messages} messages for query '{search_query}'")

        # Create TenChat client
        client = await self._create_client(account)

        try:
            # Check auth
            if not await client.check_auth():
                account.status = "cookies_expired"
                await self.db.commit()
                raise ValueError("Authentication failed - cookies expired")

            # Search users
            users = await client.search_users(search_query, limit=num_messages * 2)
            if not users:
                raise ValueError("Failed to find users")

            # Send messages
            sent_count = 0
            for i, user in enumerate(users[:num_messages]):
                user_id = user.get("id") or user.get("user_id")
                user_name = user.get("name", "")
                user_position = user.get("position", "")

                if not user_id:
                    continue

                # Generate AI message
                message_text = await self.ai_generator.generate_dm_message(
                    purpose=message_purpose,
                    recipient_name=user_name,
                    recipient_position=user_position
                )
                if not message_text:
                    logger.warning(f"Failed to generate message for user {user_id}")
                    continue

                # Send message
                success = await client.send_message(str(user_id), message_text)

                # Log action
                action = Action(
                    account_id=account.id,
                    action_type="message",
                    target_id=str(user_id),
                    success=success
                )
                self.db.add(action)

                if success:
                    sent_count += 1

                    # Update task progress
                    task.progress = int((i + 1) / num_messages * 100)
                    await self.db.commit()

                    # Human-like delay (longer for cold outreach)
                    if i < num_messages - 1:
                        delay = random.randint(
                            settings.MIN_ACTION_DELAY * 3,
                            settings.MAX_ACTION_DELAY * 3
                        )
                        logger.info(f"[{account.name}] Sent cold message to {user_id}. Pausing {delay} seconds...")
                        await asyncio.sleep(delay)

            task.result = f"Sent {sent_count}/{num_messages} cold messages"
            logger.info(f"Cold DM completed: {sent_count}/{num_messages} messages")

            return sent_count > 0

        finally:
            await client.close()

    async def _execute_alliance_invites(self, account: Account, task: Task) -> bool:
        """
        Execute alliance invites task

        Args:
            account: Account to use
            task: Task with parameters

        Returns:
            True if successful
        """
        params = task.parameters or {}
        alliance_id = params.get("alliance_id", "")
        search_query = params.get("search_query", "")
        num_invites = params.get("num_invites", 10)

        if not alliance_id:
            raise ValueError("Alliance ID is required")

        logger.info(f"Alliance invites task: {num_invites} invites to alliance {alliance_id}")

        # Create TenChat client
        client = await self._create_client(account)

        try:
            # Check auth
            if not await client.check_auth():
                account.status = "cookies_expired"
                await self.db.commit()
                raise ValueError("Authentication failed - cookies expired")

            # Search users
            users = await client.search_users(search_query, limit=num_invites * 2)
            if not users:
                raise ValueError("Failed to find users")

            # Send invites
            invited_count = 0
            for i, user in enumerate(users[:num_invites]):
                user_id = user.get("id") or user.get("user_id")
                if not user_id:
                    continue

                # Invite to alliance
                success = await client.invite_to_alliance(alliance_id, str(user_id))

                # Log action
                action = Action(
                    account_id=account.id,
                    action_type="alliance_invite",
                    target_id=str(user_id),
                    success=success
                )
                self.db.add(action)

                if success:
                    invited_count += 1

                    # Update task progress
                    task.progress = int((i + 1) / num_invites * 100)
                    await self.db.commit()

                    # Human-like delay
                    if i < num_invites - 1:
                        delay = random.randint(
                            settings.MIN_ACTION_DELAY,
                            settings.MAX_ACTION_DELAY
                        )
                        logger.info(f"[{account.name}] Invited user {user_id} to alliance. Pausing {delay} seconds...")
                        await asyncio.sleep(delay)

            task.result = f"Invited {invited_count}/{num_invites} users to alliance"
            logger.info(f"Alliance invites completed: {invited_count}/{num_invites} invites")

            return invited_count > 0

        finally:
            await client.close()

    async def _execute_parse_users(self, account: Account, task: Task) -> bool:
        """
        Execute parse users task

        Args:
            account: Account to use
            task: Task with parameters

        Returns:
            True if successful
        """
        params = task.parameters or {}
        search_query = params.get("search_query", "")
        num_users = params.get("num_users", 50)

        logger.info(f"Parse users task: {num_users} users for query '{search_query}'")

        # Create TenChat client
        client = await self._create_client(account)

        try:
            # Check auth
            if not await client.check_auth():
                account.status = "cookies_expired"
                await self.db.commit()
                raise ValueError("Authentication failed - cookies expired")

            # Search users
            users = await client.search_users(search_query, limit=num_users)
            if not users:
                raise ValueError("Failed to find users")

            # Collect user data
            user_data = []
            for i, user in enumerate(users):
                user_id = user.get("id") or user.get("user_id")
                if not user_id:
                    continue

                # Get full profile
                profile = await client.get_user_profile(str(user_id))
                if profile:
                    user_data.append({
                        "id": user_id,
                        "name": profile.get("name", ""),
                        "position": profile.get("position", ""),
                        "company": profile.get("company", ""),
                        "location": profile.get("location", "")
                    })

                # Update progress
                task.progress = int((i + 1) / num_users * 100)
                await self.db.commit()

                # Small delay to avoid rate limiting
                await asyncio.sleep(random.uniform(1, 3))

            # Save result (json already imported at top)
            task.result = f"Parsed {len(user_data)} users: {json.dumps(user_data, ensure_ascii=False)[:500]}"
            logger.info(f"Parse users completed: {len(user_data)} users parsed")

            return len(user_data) > 0

        finally:
            await client.close()

    async def _execute_auto_reply(self, account: Account, task: Task) -> bool:
        """
        Execute auto-reply task (monitors inbox and replies to new messages)

        Args:
            account: Account to use
            task: Task with parameters

        Returns:
            True if successful
        """
        params = task.parameters or {}
        check_interval = params.get("check_interval", 300)  # 5 minutes default

        logger.info(f"Auto-reply task: monitoring inbox every {check_interval} seconds")

        # Create TenChat client
        client = await self._create_client(account)

        try:
            # Check auth
            if not await client.check_auth():
                account.status = "cookies_expired"
                await self.db.commit()
                raise ValueError("Authentication failed - cookies expired")

            # Get unread messages
            messages = await client.get_inbox(limit=20, unread_only=True)
            if not messages:
                task.result = "No unread messages"
                return True

            # Reply to messages
            replied_count = 0
            for i, message in enumerate(messages):
                sender_id = message.get("sender_id") or message.get("from_user_id")
                message_text = message.get("text") or message.get("content", "")

                if not sender_id or not message_text:
                    continue

                # Generate AI reply
                reply_text = await self.ai_generator.generate_auto_reply(
                    incoming_message=message_text
                )
                if not reply_text:
                    logger.warning(f"Failed to generate reply for message from {sender_id}")
                    continue

                # Send reply
                success = await client.send_message(str(sender_id), reply_text)

                # Log action
                action = Action(
                    account_id=account.id,
                    action_type="auto_reply",
                    target_id=str(sender_id),
                    success=success
                )
                self.db.add(action)

                if success:
                    replied_count += 1

                    # Update task progress
                    task.progress = int((i + 1) / len(messages) * 100)
                    await self.db.commit()

                    # Small delay between replies
                    await asyncio.sleep(random.randint(5, 15))

            task.result = f"Replied to {replied_count}/{len(messages)} messages"
            logger.info(f"Auto-reply completed: {replied_count}/{len(messages)} replies sent")

            return replied_count > 0

        finally:
            await client.close()
