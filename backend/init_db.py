#!/usr/bin/env python
"""Initialize database tables"""
import sys
sys.path.insert(0, '.')

from app.config import settings
from app.models import Base
from sqlalchemy import create_engine

# Create engine
engine = create_engine(str(settings.DATABASE_URL))

# Create all tables
Base.metadata.create_all(bind=engine)
print("✅ Database tables created successfully!")
