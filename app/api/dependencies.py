from typing import AsyncGenerator
from sqlalchemy.ext.asyncio import AsyncSession
from app.infrastructure.database.connection_sqlserver import AsyncSessionLocal

async def get_db() -> AsyncGenerator[AsyncSession, None]:
    """
    Dependency que entrega una sesión asíncrona de base de datos.
    """
    async with AsyncSessionLocal() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise
        # El context manager 'async with' cierra la sesión automáticamente