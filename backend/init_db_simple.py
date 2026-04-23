#!/usr/bin/env python
"""Initialize database tables - Simple version"""
import sys
sys.path.insert(0, '.')

from app.config import settings
from sqlalchemy import create_engine

# Import Base and all models to register them
from app.models import Base, User

# Create engine
engine = create_engine(str(settings.DATABASE_URL))

# Create all tables
print("Creating database tables...")
Base.metadata.create_all(bind=engine)
print("✅ Database tables created successfully!")
