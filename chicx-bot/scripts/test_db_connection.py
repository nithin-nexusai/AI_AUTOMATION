#!/usr/bin/env python3
"""Test database connection for debugging CI/CD issues."""

import asyncio
import sys
import os
from sqlalchemy.ext.asyncio import create_async_engine
from sqlalchemy import text


async def test_connection():
    """Test database connection with detailed error reporting."""
    database_url = os.getenv(
        "DATABASE_URL",
        "postgresql+asyncpg://test:test@127.0.0.1:5432/chicx_test"
    )
    
    print(f"Testing connection to: {database_url.replace('test:test', 'test:***')}")
    
    try:
        # Create engine
        engine = create_async_engine(
            database_url,
            echo=True,
            pool_pre_ping=True,
            connect_args={
                "timeout": 10,
                "command_timeout": 10,
            }
        )
        
        print("\n✓ Engine created successfully")
        
        # Test connection
        async with engine.connect() as conn:
            result = await conn.execute(text("SELECT version();"))
            version = result.scalar()
            print(f"\n✓ Connected to PostgreSQL!")
            print(f"  Version: {version}")
            
            # Test pgvector extension
            result = await conn.execute(
                text("SELECT * FROM pg_extension WHERE extname = 'vector';")
            )
            extension = result.fetchone()
            if extension:
                print(f"\n✓ pgvector extension is installed")
            else:
                print(f"\n✗ pgvector extension is NOT installed")
                print("  Run: CREATE EXTENSION IF NOT EXISTS vector;")
        
        await engine.dispose()
        print("\n✓ All tests passed!")
        return 0
        
    except Exception as e:
        print(f"\n✗ Connection failed: {e}")
        print(f"\nError type: {type(e).__name__}")
        import traceback
        traceback.print_exc()
        return 1


if __name__ == "__main__":
    exit_code = asyncio.run(test_connection())
    sys.exit(exit_code)

# Made with Bob
