from typing import AsyncGenerator
from app.infrastructure.db_sql_server.sql_server_client_async import SQLServerClientAsync
from app.core.setup_config import settings

async def get_db() -> AsyncGenerator[SQLServerClientAsync, None]:
    """
    Dependency que entrega una instancia conectada de SQLServerClientAsync.
    Maneja la apertura y cierre de la conexión automáticamente.
    """
    # Usamos el método de tu clase settings para obtener el Connection String
    dsn = settings.get_database_sql_server_url()
    
    # Instanciamos el cliente
    client = SQLServerClientAsync(dsn=dsn)
    
    # Usamos el context manager asíncrono (__aenter__ / __aexit__) 
    # que ya definiste en tu archivo estandarizado para conectar y desconectar.
    async with client as db:
        yield db