"""
Database connection manager
"""
import os
from pathlib import Path
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker
from sqlalchemy.pool import StaticPool
from app.models.database import Base


class DatabaseManager:
    """Async database manager"""

    def __init__(self, database_url: str):
        """Initialize database manager"""
        self.database_url = database_url

        # Create async engine with connection pooling
        self.engine = create_async_engine(
            database_url,
            connect_args={"check_same_thread": False} if "sqlite" in database_url else {},
            poolclass=StaticPool if "sqlite" in database_url else None,
            echo=False
        )

        # Create session factory
        self.async_session_maker = async_sessionmaker(
            self.engine,
            class_=AsyncSession,
            expire_on_commit=False
        )

    async def init_db(self):
        """Initialize database (create tables)"""
        # Ensure data directory exists
        if "sqlite" in self.database_url:
            db_path = self.database_url.replace("sqlite+aiosqlite:///", "")
            db_dir = Path(db_path).parent
            db_dir.mkdir(parents=True, exist_ok=True)

        async with self.engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)

    async def get_session(self) -> AsyncSession:
        """Get database session"""
        async with self.async_session_maker() as session:
            yield session

    async def close(self):
        """Close database connection"""
        await self.engine.dispose()


# Global database manager instance
db_manager: DatabaseManager = None


def get_db_manager() -> DatabaseManager:
    """Get global database manager instance"""
    global db_manager
    if db_manager is None:
        from config.settings import settings
        db_manager = DatabaseManager(settings.DATABASE_URL)
    return db_manager


async def get_db():
    """Dependency for FastAPI to get database session"""
    db = get_db_manager()
    async for session in db.get_session():
        yield session
