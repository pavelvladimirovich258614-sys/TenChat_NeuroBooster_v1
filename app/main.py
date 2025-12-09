"""
FastAPI Backend for TenChat NeuroBooster with Enhanced Reliability
"""
import asyncio
import signal
import sys
from contextlib import asynccontextmanager
from fastapi import FastAPI, Depends, HTTPException, UploadFile, File, Form
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy import select, desc
from sqlalchemy.ext.asyncio import AsyncSession
from typing import List, Optional
from datetime import datetime
from pydantic import BaseModel

from app.models.database import Account, Task, Action, DailyStats
from app.utils.db_manager import get_db_manager, get_db
from app.utils.cookies_parser import CookiesParser
from app.utils.proxy_handler import ProxyHandler
from app.utils.user_agent_generator import UserAgentGenerator
from app.services.tenchat_client import TenChatClient, AuthExpiredError, CaptchaRequiredError, ProxyError
from app.services.ai_generator import AIGenerator
from app.services.task_executor import TaskExecutor
from config.settings import settings
from loguru import logger

# Configure loguru for better output
logger.remove()
logger.add(
    sys.stderr,
    format="<green>{time:YYYY-MM-DD HH:mm:ss}</green> | <level>{level: <8}</level> | <cyan>{name}</cyan>:<cyan>{function}</cyan>:<cyan>{line}</cyan> - <level>{message}</level>",
    level="INFO"
)
logger.add(
    "logs/tenchat_booster.log",
    rotation="10 MB",
    retention="7 days",
    compression="zip",
    level="DEBUG"
)


# Pydantic models
class AccountCreate(BaseModel):
    name: str
    cookies_json: str
    proxy: str


class AccountResponse(BaseModel):
    id: int
    name: str
    proxy_display: str
    status: str
    last_check: datetime
    created_at: datetime

    class Config:
        from_attributes = True


class TaskCreate(BaseModel):
    account_ids: List[int]
    task_type: str  # warmup, ai_post
    parameters: dict


class TaskResponse(BaseModel):
    id: int
    account_id: int
    task_type: str
    status: str
    progress: int
    result: Optional[str]
    error_message: Optional[str]
    created_at: datetime

    class Config:
        from_attributes = True


class ActionResponse(BaseModel):
    id: int
    account_id: int
    action_type: str
    target_id: Optional[str]
    success: bool
    error_message: Optional[str]
    created_at: datetime

    class Config:
        from_attributes = True


# Global task queue and workers
task_queue: asyncio.Queue = None
task_workers_running = False
task_worker_tasks: List[asyncio.Task] = []


async def task_worker(worker_id: int):
    """Background worker to process tasks"""
    global task_workers_running

    logger.info(f"Task worker #{worker_id} started")

    # Create AI generator for this worker
    ai_generator = AIGenerator(
        base_url=settings.AI_BASE_URL,
        api_key=settings.AI_API_KEY,
        model_comments=settings.AI_MODEL_COMMENTS,
        model_articles=settings.AI_MODEL_ARTICLES,
        model_analytics=settings.AI_MODEL_ANALYTICS
    )

    db_manager = get_db_manager()

    while task_workers_running:
        try:
            # Get task from queue with timeout
            task_id = await asyncio.wait_for(task_queue.get(), timeout=2.0)
            
            logger.info(f"Worker #{worker_id} processing task {task_id}")

            # Process task - get single session
            db = None
            try:
                async for session in db_manager.get_session():
                    db = session
                    break
                
                if db:
                    # Get task
                    result = await db.execute(
                        select(Task).where(Task.id == task_id)
                    )
                    task = result.scalar_one_or_none()

                    if task:
                        executor = TaskExecutor(db, ai_generator)
                        success = await executor.execute_task(task)
                        logger.info(f"Worker #{worker_id} finished task {task_id}: {'SUCCESS' if success else 'FAILED'}")
                    else:
                        logger.warning(f"Task {task_id} not found in database")
            
            except Exception as e:
                logger.error(f"Worker #{worker_id} error processing task {task_id}: {e}")
            finally:
                task_queue.task_done()

        except asyncio.TimeoutError:
            continue
        except asyncio.CancelledError:
            logger.info(f"Task worker #{worker_id} cancelled")
            break
        except Exception as e:
            logger.error(f"Task worker #{worker_id} error: {e}")
            await asyncio.sleep(1)

    logger.info(f"Task worker #{worker_id} stopped")


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan events with graceful shutdown"""
    global task_queue, task_workers_running, task_worker_tasks

    # Startup
    logger.info("=" * 50)
    logger.info("Starting TenChat NeuroBooster API v1.2.1")
    logger.info("=" * 50)

    # Initialize database
    db_manager = get_db_manager()
    await db_manager.init_db()
    logger.info("✓ Database initialized")

    # Create task queue with max size
    task_queue = asyncio.Queue(maxsize=settings.TASK_QUEUE_MAX_SIZE)
    logger.info(f"✓ Task queue created (max size: {settings.TASK_QUEUE_MAX_SIZE})")

    # Start multiple task workers
    task_workers_running = True
    num_workers = settings.NUM_TASK_WORKERS
    
    for i in range(num_workers):
        worker_task = asyncio.create_task(task_worker(i + 1))
        task_worker_tasks.append(worker_task)
    
    logger.info(f"✓ Started {num_workers} task workers")
    logger.info("=" * 50)
    logger.info("API ready to accept requests")
    logger.info("=" * 50)

    yield

    # Shutdown
    logger.info("=" * 50)
    logger.info("Shutting down TenChat NeuroBooster API...")

    # Signal workers to stop
    task_workers_running = False
    
    # Wait for workers to finish current tasks (with timeout)
    logger.info("Waiting for task workers to finish...")
    try:
        # Cancel all workers
        for worker_task in task_worker_tasks:
            worker_task.cancel()
        
        # Wait for all to complete with timeout
        await asyncio.wait_for(
            asyncio.gather(*task_worker_tasks, return_exceptions=True),
            timeout=30.0
        )
        logger.info("✓ All task workers stopped")
    except asyncio.TimeoutError:
        logger.warning("⚠ Some workers did not stop in time")

    # Close database
    await db_manager.close()
    logger.info("✓ Database connection closed")
    logger.info("=" * 50)
    logger.info("Shutdown complete")
    logger.info("=" * 50)


# Create FastAPI app
app = FastAPI(
    title="TenChat NeuroBooster API",
    description="Self-hosted automation service for TenChat",
    version="1.0.0",
    lifespan=lifespan
)

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# Routes

@app.get("/")
async def root():
    """Health check"""
    return {"status": "ok", "service": "TenChat NeuroBooster"}


@app.post("/accounts", response_model=AccountResponse)
async def create_account(
    account: AccountCreate,
    db: AsyncSession = Depends(get_db)
):
    """Create new account"""
    try:
        # Validate cookies
        cookies = CookiesParser.parse_json(account.cookies_json)
        if not CookiesParser.validate_cookies(cookies):
            raise HTTPException(400, "Invalid cookies")

        # Validate proxy
        proxy_config = ProxyHandler.get_httpx_proxy_config(account.proxy)

        # Generate User-Agent
        user_agent = UserAgentGenerator.generate_random()

        # Create account
        new_account = Account(
            name=account.name,
            cookies_json=account.cookies_json,
            proxy=account.proxy,
            user_agent=user_agent,
            status="active"
        )

        db.add(new_account)
        await db.commit()
        await db.refresh(new_account)

        # Check authentication
        client = TenChatClient(cookies, proxy_config, user_agent)
        try:
            auth_ok = await client.check_auth()
            if not auth_ok:
                new_account.status = "cookies_expired"
                await db.commit()
        finally:
            await client.close()

        return AccountResponse(
            id=new_account.id,
            name=new_account.name,
            proxy_display=ProxyHandler.format_proxy_display(account.proxy),
            status=new_account.status,
            last_check=new_account.last_check,
            created_at=new_account.created_at
        )

    except ValueError as e:
        logger.warning(f"Validation error: {e}")
        raise HTTPException(400, f"Validation error: {str(e)}")
    except RuntimeError as e:
        logger.error(f"Runtime error: {e}")
        raise HTTPException(500, f"Configuration error: {str(e)}")
    except ConnectionError as e:
        logger.error(f"Connection error: {e}")
        raise HTTPException(500, f"Proxy connection failed: {str(e)}")
    except TimeoutError as e:
        logger.error(f"Timeout error: {e}")
        raise HTTPException(500, f"Proxy connection timeout: {str(e)}")
    except Exception as e:
        logger.error(f"Create account error: {type(e).__name__}: {e}", exc_info=True)
        # Return more specific error message
        error_msg = str(e)
        if "proxy" in error_msg.lower() or "socks" in error_msg.lower():
            raise HTTPException(500, f"Proxy error: {error_msg}")
        elif "connection" in error_msg.lower():
            raise HTTPException(500, f"Connection error: {error_msg}")
        else:
            raise HTTPException(500, f"Internal server error: {error_msg}")


@app.get("/accounts", response_model=List[AccountResponse])
async def list_accounts(db: AsyncSession = Depends(get_db)):
    """List all accounts"""
    result = await db.execute(select(Account).order_by(desc(Account.created_at)))
    accounts = result.scalars().all()

    return [
        AccountResponse(
            id=acc.id,
            name=acc.name,
            proxy_display=ProxyHandler.format_proxy_display(acc.proxy),
            status=acc.status,
            last_check=acc.last_check,
            created_at=acc.created_at
        )
        for acc in accounts
    ]


@app.delete("/accounts/{account_id}")
async def delete_account(account_id: int, db: AsyncSession = Depends(get_db)):
    """Delete account"""
    result = await db.execute(select(Account).where(Account.id == account_id))
    account = result.scalar_one_or_none()

    if not account:
        raise HTTPException(404, "Account not found")

    await db.delete(account)
    await db.commit()

    return {"status": "deleted"}


@app.post("/tasks", response_model=List[TaskResponse])
async def create_tasks(
    task_data: TaskCreate,
    db: AsyncSession = Depends(get_db)
):
    """Create tasks for accounts"""
    tasks = []

    for account_id in task_data.account_ids:
        # Verify account exists
        result = await db.execute(select(Account).where(Account.id == account_id))
        account = result.scalar_one_or_none()

        if not account:
            continue

        # Create task
        task = Task(
            account_id=account_id,
            task_type=task_data.task_type,
            parameters=task_data.parameters,
            status="pending"
        )

        db.add(task)
        await db.commit()
        await db.refresh(task)

        tasks.append(task)

        # Add to queue
        await task_queue.put(task.id)

    return [
        TaskResponse(
            id=t.id,
            account_id=t.account_id,
            task_type=t.task_type,
            status=t.status,
            progress=t.progress,
            result=t.result,
            error_message=t.error_message,
            created_at=t.created_at
        )
        for t in tasks
    ]


@app.get("/tasks", response_model=List[TaskResponse])
async def list_tasks(
    limit: int = 50,
    db: AsyncSession = Depends(get_db)
):
    """List recent tasks"""
    result = await db.execute(
        select(Task).order_by(desc(Task.created_at)).limit(limit)
    )
    tasks = result.scalars().all()

    return [
        TaskResponse(
            id=t.id,
            account_id=t.account_id,
            task_type=t.task_type,
            status=t.status,
            progress=t.progress,
            result=t.result,
            error_message=t.error_message,
            created_at=t.created_at
        )
        for t in tasks
    ]


@app.get("/actions", response_model=List[ActionResponse])
async def list_actions(
    limit: int = 100,
    db: AsyncSession = Depends(get_db)
):
    """List recent actions"""
    result = await db.execute(
        select(Action).order_by(desc(Action.created_at)).limit(limit)
    )
    actions = result.scalars().all()

    return [
        ActionResponse(
            id=a.id,
            account_id=a.account_id,
            action_type=a.action_type,
            target_id=a.target_id,
            success=a.success,
            error_message=a.error_message,
            created_at=a.created_at
        )
        for a in actions
    ]


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        app,
        host=settings.FASTAPI_HOST,
        port=settings.FASTAPI_PORT,
        log_level="info"
    )
