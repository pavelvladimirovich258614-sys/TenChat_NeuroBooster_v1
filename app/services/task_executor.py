"""
Task Executor with human emulation and safety limits
"""
import asyncio
import random
from datetime import datetime, timedelta
from typing import Dict, Optional, List
from loguru import logger
from sqlalchemy import select, and_, func
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.database import Account, Action, Task, DailyStats
from app.services.tenchat_client import TenChatClient
from app.services.ai_generator import AIGenerator
from app.utils.cookies_parser import CookiesParser
from app.utils.proxy_handler import ProxyHandler
from config.settings import settings


class TaskExecutor:
    """Execute tasks with safety limits and human emulation"""

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

    async def execute_task(self, task: Task) -> bool:
        """
        Execute a task

        Args:
            task: Task to execute

        Returns:
            True if successful, False otherwise
        """
        logger.info(f"Executing task {task.id}: {task.task_type}")

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

        except Exception as e:
            logger.error(f"Task {task.id} failed: {e}")
            task.status = "failed"
            task.error_message = str(e)
            await self.db.commit()
            return False

    async def _execute_warmup(self, account: Account, task: Task) -> bool:
        """
        Execute warmup task (liking feed)

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
                account.status = "cookies_expired"
                await self.db.commit()
                raise ValueError("Authentication failed - cookies expired")

            # Get feed
            posts = await client.get_feed(feed_type=feed_type, limit=num_likes * 2)
            if not posts:
                raise ValueError("Failed to fetch feed")

            # Like posts with delays
            liked_count = 0
            for i, post in enumerate(posts[:num_likes]):
                post_id = post.get("id") or post.get("post_id")
                if not post_id:
                    continue

                # Like post
                success = await client.like_post(str(post_id))

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

                    # Update task progress
                    task.progress = int((i + 1) / num_likes * 100)
                    await self.db.commit()

                    # Human-like delay
                    if i < num_likes - 1:  # No delay after last like
                        delay = random.randint(
                            settings.MIN_ACTION_DELAY,
                            settings.MAX_ACTION_DELAY
                        )
                        logger.info(f"[{account.name}] Liked post {post_id}. Pausing {delay} seconds...")
                        await asyncio.sleep(delay)

            task.result = f"Liked {liked_count}/{num_likes} posts"
            logger.info(f"Warmup completed: {liked_count}/{num_likes} likes")

            return liked_count > 0

        finally:
            await client.close()

    async def _execute_ai_post(self, account: Account, task: Task) -> bool:
        """
        Execute AI post task

        Args:
            account: Account to use
            task: Task with parameters

        Returns:
            True if successful
        """
        params = task.parameters or {}
        topic = params.get("topic", "")
        style = params.get("style", "professional")

        if not topic:
            raise ValueError("Topic is required for AI post task")

        logger.info(f"AI post task: {topic}")

        # Check daily limits
        if not await self._check_daily_limit(account.id, "post", 1):
            raise ValueError("Daily post limit exceeded")

        # Generate article
        task.progress = 20
        await self.db.commit()

        article = await self.ai_generator.generate_article(topic, style)
        if not article:
            raise ValueError("Failed to generate article")

        logger.info(f"Generated article: {article['title']}")

        # Create TenChat client
        client = await self._create_client(account)

        try:
            # Check auth
            if not await client.check_auth():
                account.status = "cookies_expired"
                await self.db.commit()
                raise ValueError("Authentication failed - cookies expired")

            task.progress = 50
            await self.db.commit()

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
            task.result = f"Posted article: {post_id}"
            await self.db.commit()

            logger.info(f"AI post completed: {post_id}")
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
