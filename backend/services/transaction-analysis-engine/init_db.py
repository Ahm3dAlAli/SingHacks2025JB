"""
Database initialization script for Transaction Analysis Engine.
This script creates all necessary tables and loads initial data.
"""
import asyncio
import os
import sys
from pathlib import Path

# Add the project root to the Python path
sys.path.append(str(Path(__file__).parent))

from sqlalchemy import text
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker

from app.database.connection import SQLALCHEMY_DATABASE_URL
from app.database.models import Base

async def init_models():
    """Create all database tables and load initial data."""
    # Create async engine
    engine = create_async_engine(SQLALCHEMY_DATABASE_URL)
    
    # Create all tables
    print("Creating database tables...")
    async with engine.begin() as conn:
        # Enable uuid-ossp extension if not already enabled
        await conn.execute(text('CREATE EXTENSION IF NOT EXISTS "uuid-ossp"'))
        # Create all tables
        await conn.run_sync(Base.metadata.create_all)
    
    # Load initial data
    print("Loading initial data...")
    async with AsyncSession(engine) as session:
        # Check if rules already exist
        result = await session.execute(text("SELECT COUNT(*) FROM regulatory_rules"))
        count = result.scalar()
        
        if count == 0:
            # Load seed data
            seed_file = Path(__file__).parent / "database" / "seed_rules.sql"
            if seed_file.exists():
                print(f"Loading data from {seed_file}...")
                with open(seed_file, 'r') as f:
                    sql = f.read()
                
                # Split SQL into individual statements and execute them
                for statement in sql.split(';'):
                    statement = statement.strip()
                    if statement:
                        try:
                            await session.execute(text(statement))
                            await session.commit()
                        except Exception as e:
                            print(f"Error executing statement: {e}")
                            await session.rollback()
                            raise
    
    print("Database initialization complete!")
    await engine.dispose()

if __name__ == "__main__":
    print("Starting database initialization...")
    asyncio.run(init_models())
