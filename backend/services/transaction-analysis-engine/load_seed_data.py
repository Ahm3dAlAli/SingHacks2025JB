"""
Script to load seed data into the regulatory_rules table.
"""
import asyncio
import os
from pathlib import Path
from sqlalchemy import text
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker

# Get database URL from environment or use default
DATABASE_URL = os.getenv(
    "DATABASE_URL",
    "postgresql+asyncpg://postgres:postgres@localhost:5432/aml_monitoring"
)

async def load_seed_data():
    """Load seed data from SQL file into the database."""
    # Create async engine
    engine = create_async_engine(DATABASE_URL)
    
    # Get the directory of the current script
    script_dir = Path(__file__).parent
    seed_file = script_dir / "database" / "seed_rules.sql"
    
    if not seed_file.exists():
        print(f"Error: Seed file not found at {seed_file}")
        return False
    
    print(f"Loading seed data from {seed_file}...")
    
    try:
        # Read the SQL file
        with open(seed_file, 'r') as f:
            sql = f.read()
        
        # Split into individual statements and execute them
        async with engine.begin() as conn:
            for statement in sql.split(';'):
                statement = statement.strip()
                if statement:
                    try:
                        await conn.execute(text(statement))
                        await conn.commit()
                    except Exception as e:
                        print(f"Error executing statement: {e}")
                        await conn.rollback()
                        raise
        
        print("Seed data loaded successfully!")
        return True
    except Exception as e:
        print(f"Error loading seed data: {e}")
        return False
    finally:
        await engine.dispose()

if __name__ == "__main__":
    asyncio.run(load_seed_data())
