import os
from dotenv import load_dotenv
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker


load_dotenv()

# 1. Construir la URL de Conexión para AIOODBC
# Formato: mssql+aioodbc://<user>:<password>@<host>/<dbname>?driver=<driver>
# Es CRÍTICO especificar el driver ODBC correcto instalado en tu sistema (ej: ODBC Driver 17 for SQL Server)

server = os.getenv("DB_SERVER")
user = os.getenv("DB_USER")
password = os.getenv("DB_PASSWORD")
database = os.getenv("DB_NAME")
driver = os.getenv("DB_DRIVER")

DATABASE_URL = os.getenv(
    "DATABASE_URL", 
    f"mssql+aioodbc://{user}:{password}@{server}/{database}?driver={driver}"
)

# 2. Crear el Async Engine
engine = create_async_engine(
    DATABASE_URL,
    echo=False,
    pool_pre_ping=True,
    pool_size=10,
    max_overflow=20
)

# 3. Crear la Fábrica de Sesiones Asíncronas
AsyncSessionLocal = sessionmaker(
    bind=engine,
    class_=AsyncSession,
    expire_on_commit=False,
    autocommit=False,
    autoflush=False
)