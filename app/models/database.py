"""
Database models for TenChat NeuroBooster
"""
from datetime import datetime
from typing import Optional
from sqlalchemy import Column, Integer, String, DateTime, Boolean, Text, ForeignKey, JSON
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import relationship

Base = declarative_base()


class Account(Base):
    """TenChat account model"""
    __tablename__ = "accounts"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(255), unique=True, nullable=False)
    cookies_json = Column(Text, nullable=False)  # JSON string
    proxy = Column(String(255), nullable=False)  # format: ip:port:login:pass
    user_agent = Column(String(512), nullable=False)
    status = Column(String(50), default="active")  # active, error, captcha, cookies_expired
    last_check = Column(DateTime, default=datetime.utcnow)
    created_at = Column(DateTime, default=datetime.utcnow)

    # Relationships
    actions = relationship("Action", back_populates="account", cascade="all, delete-orphan")
    tasks = relationship("Task", back_populates="account", cascade="all, delete-orphan")


class Action(Base):
    """Action log model (likes, follows, posts)"""
    __tablename__ = "actions"

    id = Column(Integer, primary_key=True, index=True)
    account_id = Column(Integer, ForeignKey("accounts.id"), nullable=False)
    action_type = Column(String(50), nullable=False)  # like, follow, post, comment
    target_id = Column(String(255))  # post_id, user_id, etc.
    success = Column(Boolean, default=True)
    error_message = Column(Text, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)

    # Relationships
    account = relationship("Account", back_populates="actions")


class Task(Base):
    """Task queue model"""
    __tablename__ = "tasks"

    id = Column(Integer, primary_key=True, index=True)
    account_id = Column(Integer, ForeignKey("accounts.id"), nullable=False)
    task_type = Column(String(50), nullable=False)  # warmup, ai_post
    parameters = Column(JSON)  # Task-specific parameters
    status = Column(String(50), default="pending")  # pending, running, completed, failed
    progress = Column(Integer, default=0)  # 0-100
    result = Column(Text, nullable=True)
    error_message = Column(Text, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    started_at = Column(DateTime, nullable=True)
    completed_at = Column(DateTime, nullable=True)

    # Relationships
    account = relationship("Account", back_populates="tasks")


class DailyStats(Base):
    """Daily statistics for safety limits"""
    __tablename__ = "daily_stats"

    id = Column(Integer, primary_key=True, index=True)
    account_id = Column(Integer, ForeignKey("accounts.id"), nullable=False)
    date = Column(DateTime, nullable=False)
    likes_count = Column(Integer, default=0)
    follows_count = Column(Integer, default=0)
    posts_count = Column(Integer, default=0)
    comments_count = Column(Integer, default=0)
