import logging
from sqlalchemy import create_engine
from sqlalchemy.orm import declarative_base, sessionmaker
from backend.config import settings

logger = logging.getLogger("property-scout-db")

# Base class for SQLAlchemy Models
Base = declarative_base()

# Configure SQLAlchemy connection engine
# pool_pre_ping=True helps reconnect if DB drops
engine = create_engine(
    settings.DATABASE_URL,
    pool_pre_ping=True
)

# Thread-local session factory
SessionLocal = sessionmaker(
    autocommit=False,
    autoflush=False,
    bind=engine
)

def get_db():
    """
    FastAPI dependency yielding a database session
    """
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

def init_db():
    """
    Initializes database tables defined in models.py
    """
    try:
        logger.info("Initializing relational database tables...")
        # Import models here to ensure they register on Base
        import backend.db.models # noqa
        Base.metadata.create_all(bind=engine)
        logger.info("Relational database tables initialized successfully.")
    except Exception as e:
        logger.error(f"Error initializing relational database tables: {e}")
        raise e
