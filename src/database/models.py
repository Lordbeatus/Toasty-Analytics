"""
Database models for persistent storage
"""

import os
from datetime import datetime

from sqlalchemy import (
    JSON,
    Boolean,
    Column,
    DateTime,
    Float,
    ForeignKey,
    Integer,
    String,
    Text,
    create_engine,
)
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import relationship, sessionmaker

Base = declarative_base()


class User(Base):
    """User profile for personalized learning"""

    __tablename__ = "users"

    id = Column(String, primary_key=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Preferences
    preferences = Column(JSON, default={})  # User-specific preferences
    feedback_style = Column(
        String, default="standard"
    )  # minimal, standard, detailed, expert

    # Relationships
    grading_history = relationship(
        "GradingHistory", back_populates="user", cascade="all, delete-orphan"
    )
    learning_strategies = relationship(
        "LearningStrategy", back_populates="user", cascade="all, delete-orphan"
    )

    def __repr__(self):
        return f"<User(id='{self.id}')>"


class Agent(Base):
    """Agent profile for multi-agent systems"""

    __tablename__ = "agents"

    id = Column(String, primary_key=True)
    user_id = Column(String, ForeignKey("users.id"), nullable=True)
    agent_type = Column(String)  # 'coding', 'review', 'testing', etc.
    created_at = Column(DateTime, default=datetime.utcnow)

    # Agent configuration
    capabilities = Column(JSON, default=[])
    specializations = Column(JSON, default=[])
    performance_metrics = Column(JSON, default={})

    # Relationships
    grading_history = relationship(
        "GradingHistory", back_populates="agent", cascade="all, delete-orphan"
    )

    def __repr__(self):
        return f"<Agent(id='{self.id}', type='{self.agent_type}')>"


class GradingHistory(Base):
    """Historical grading records"""

    __tablename__ = "grading_history"

    id = Column(Integer, primary_key=True, autoincrement=True)
    user_id = Column(String, ForeignKey("users.id"), nullable=True)
    agent_id = Column(String, ForeignKey("agents.id"), nullable=True)
    session_id = Column(String, index=True)  # Groups multiple gradings in one session

    # Grading details
    dimension = Column(String)  # Which dimension was graded
    score = Column(Float)
    max_score = Column(Float)
    percentage = Column(Float)

    # Detailed data
    breakdown = Column(JSON)  # Full ScoreBreakdown
    feedback = Column(Text)
    suggestions = Column(JSON)  # List of ImprovementSuggestion
    grade_metadata = Column(JSON, default={})  # Code snippet, language, task_type, etc.

    # Timing
    timestamp = Column(DateTime, default=datetime.utcnow, index=True)
    generation_time = Column(Float)  # Time to generate code/response

    # Context
    task_type = Column(String)  # 'bug_fix', 'feature', 'refactor', etc.
    complexity = Column(String)  # 'simple', 'medium', 'complex'

    # Relationships
    user = relationship("User", back_populates="grading_history")
    agent = relationship("Agent", back_populates="grading_history")

    def __repr__(self):
        return f"<GradingHistory(id={self.id}, dimension='{self.dimension}', score={self.score})>"


class LearningStrategy(Base):
    """Learned strategies for improvement"""

    __tablename__ = "learning_strategies"

    id = Column(Integer, primary_key=True, autoincrement=True)
    user_id = Column(String, ForeignKey("users.id"))

    # Strategy details
    strategy_type = Column(
        String
    )  # 'parameter_adaptation', 'feedback_personalization', etc.
    dimension = Column(String)  # Which dimension this applies to

    # Learned parameters
    weights = Column(JSON, default={})
    thresholds = Column(JSON, default={})
    feedback_template = Column(Text, nullable=True)

    # Performance tracking
    effectiveness_score = Column(Float, default=0.0)  # How well this strategy works
    times_applied = Column(Integer, default=0)
    success_count = Column(Integer, default=0)

    # Metadata
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    active = Column(Boolean, default=True)

    # Relationships
    user = relationship("User", back_populates="learning_strategies")

    def __repr__(self):
        return f"<LearningStrategy(id={self.id}, type='{self.strategy_type}', effectiveness={self.effectiveness_score})>"


class CollectiveLearning(Base):
    """Global learning patterns from all users"""

    __tablename__ = "collective_learning"

    id = Column(Integer, primary_key=True, autoincrement=True)

    # Pattern details
    pattern_type = Column(
        String
    )  # 'common_mistake', 'best_practice', 'improvement_path'
    dimension = Column(String)

    # Pattern data
    pattern_data = Column(JSON)  # The actual pattern
    occurrence_count = Column(Integer, default=1)
    success_rate = Column(Float, default=0.0)

    # Context
    applicable_to = Column(JSON, default=[])  # Languages, task types, etc.

    # Metadata
    discovered_at = Column(DateTime, default=datetime.utcnow)
    last_seen = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    def __repr__(self):
        return f"<CollectiveLearning(id={self.id}, type='{self.pattern_type}', count={self.occurrence_count})>"


class DatabaseManager:
    """Manager for database connections and sessions"""

    def __init__(self, database_url: str = None):
        """
        Initialize database manager

        Args:
            database_url: SQLAlchemy database URL.
                         Defaults to SQLite in current directory.
        """
        if database_url is None:
            database_url = os.getenv(
                "TOASTYANALYTICS_DB_URL", "sqlite:///./toastyanalytics.db"
            )

        self.engine = create_engine(
            database_url, echo=os.getenv("DB_ECHO", "false").lower() == "true"
        )
        self.SessionLocal = sessionmaker(
            autocommit=False, autoflush=False, bind=self.engine
        )

        # Create tables
        Base.metadata.create_all(bind=self.engine)

    def get_session(self):
        """Get a new database session"""
        return self.SessionLocal()

    def close(self):
        """Close database connection"""
        self.engine.dispose()
