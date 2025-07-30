from sqlalchemy import create_engine, Column, Integer, String, Float, DateTime, Text, Boolean
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
from datetime import datetime
import os

# Create database engine
DATABASE_URL = "sqlite:///./market_scanner.db"
engine = create_engine(DATABASE_URL, connect_args={"check_same_thread": False})

# Create session factory
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

# Create base class for models
Base = declarative_base()

class ScanResult(Base):
    __tablename__ = "scan_results"
    
    id = Column(Integer, primary_key=True, index=True)
    symbol = Column(String, index=True)
    company_name = Column(String)
    exchange = Column(String)
    country = Column(String, index=True)  # US or AU
    scan_type = Column(String)  # ttm_squeeze or volume_spike
    scan_date = Column(DateTime, default=datetime.utcnow)
    
    # Stock metrics
    price = Column(Float)
    change = Column(Float)
    change_percent = Column(Float)
    volume = Column(Integer)
    market_cap = Column(Integer)
    pe_ratio = Column(Float)
    
    # TTM Squeeze specific fields
    squeeze_days = Column(Integer, nullable=True)
    bollinger_upper = Column(Float, nullable=True)
    bollinger_lower = Column(Float, nullable=True)
    bollinger_middle = Column(Float, nullable=True)
    keltner_upper = Column(Float, nullable=True)
    keltner_lower = Column(Float, nullable=True)
    keltner_middle = Column(Float, nullable=True)
    momentum = Column(Float, nullable=True)
    squeeze_intensity = Column(String, nullable=True)
    
    # Volume Spike specific fields
    spike_days = Column(Integer, nullable=True)
    volume_ratio = Column(Float, nullable=True)
    avg_volume_30d = Column(Integer, nullable=True)
    consecutive_days = Column(Integer, nullable=True)
    spike_intensity = Column(String, nullable=True)

class HistoricalData(Base):
    __tablename__ = "historical_data"
    
    id = Column(Integer, primary_key=True, index=True)
    symbol = Column(String, index=True)
    date = Column(DateTime, index=True)
    open = Column(Float)
    high = Column(Float)
    low = Column(Float)
    close = Column(Float)
    volume = Column(Integer)
    country = Column(String, index=True)

class ScanSession(Base):
    __tablename__ = "scan_sessions"
    
    id = Column(Integer, primary_key=True, index=True)
    country = Column(String, index=True)
    scan_type = Column(String)  # scheduled or manual
    start_time = Column(DateTime, default=datetime.utcnow)
    end_time = Column(DateTime, nullable=True)
    status = Column(String)  # running, completed, failed
    results_count = Column(Integer, default=0)
    error_message = Column(Text, nullable=True)

# Create tables
def create_tables():
    Base.metadata.create_all(bind=engine)

# Database dependency
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close() 