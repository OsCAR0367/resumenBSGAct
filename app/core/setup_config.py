import os
from enum import Enum
from pathlib import Path
from typing import Any, Dict, List, Optional

from dotenv import load_dotenv

# Definir tipos de entorno
class Environment(str, Enum):
    """Tipos de entorno de la aplicación.

    Define los posibles entornos en los que puede ejecutarse la aplicación:
    development, production y test.
    """

    DEVELOPMENT = "development"
    PRODUCTION = "production"
    TEST = "test"


# Definir niveles de log como enum para mayor seguridad de tipos
class LogLevel(str, Enum):
    """Tipos de nivel de log."""

    DEBUG = "DEBUG"
    INFO = "INFO"
    WARNING = "WARNING"
    ERROR = "ERROR"
    CRITICAL = "CRITICAL"

# Cargar archivo .env apropiado basado en el entorno
def load_env_file() -> Optional[str]:
    """Cargar archivo .env específico del entorno.

    Returns:
        Optional[str]: Ruta al archivo env cargado, o None si no se cargó ningún archivo
    """
    base_dir = Path(__file__).resolve().parent.parent.parent

    env_files = [
        base_dir / f".env.production",
        base_dir / f".env.test",
        base_dir / f".env.development",
        base_dir / ".env",
    ]

    # Cargar el primer archivo env que exista
    for env_file in env_files:
        if env_file.is_file():
            load_dotenv(dotenv_path=str(env_file), override=True)
            print(f"Loaded environment from {env_file}")
            return str(env_file)

    print("No .env file found, using system environment variables")
    return None


# Cargar archivo env
ENV_FILE = load_env_file()


# Funciones auxiliares para parsear variables de entorno
def parse_bool(value: Optional[str], default: bool = False) -> bool:
    """Parsear un valor booleano desde una cadena.

    Args:
        value: El valor de cadena a parsear
        default: El valor por defecto si el parseo falla

    Returns:
        bool: El valor booleano parseado
    """
    if value is None:
        return default
    return value.lower() in ("true", "1", "t", "yes", "on")


def parse_int(value: Optional[str], default: int) -> int:
    """Parsear un valor entero desde una cadena.

    Args:
        value: El valor de cadena a parsear
        default: El valor por defecto si el parseo falla

    Returns:
        int: El valor entero parseado
    """
    if value is None:
        return default
    try:
        return int(value)
    except ValueError:
        return default


def parse_float(value: Optional[str], default: float) -> float:
    """Parsear un valor flotante desde una cadena.

    Args:
        value: El valor de cadena a parsear
        default: El valor por defecto si el parseo falla

    Returns:
        float: El valor flotante parseado
    """
    if value is None:
        return default
    try:
        return float(value)
    except ValueError:
        return default


def parse_list_from_env(env_key: str, default: Optional[List[str]] = None) -> List[str]:
    """Parsear una lista separada por comas desde una variable de entorno.

    Args:
        env_key: La clave de la variable de entorno
        default: El valor por defecto si la variable no está establecida

    Returns:
        List[str]: La lista parseada
    """
    value = os.getenv(env_key)
    if not value:
        return default or []

    # Eliminar comillas si existen
    value = value.strip("\"'")

    # Manejar cadena vacía
    if not value:
        return default or []

    # Manejar caso de valor único
    if "," not in value:
        return [value.strip()]

    # Dividir valores separados por comas
    return [item.strip() for item in value.split(",") if item.strip()]


def parse_dict_of_lists_from_env(prefix: str, default_dict: Optional[Dict[str, List[str]]] = None) -> Dict[
    str, List[str]]:
    """Parsear diccionario de listas desde variables de entorno con un prefijo común.

    Args:
        prefix: El prefijo a buscar
        default_dict: El diccionario por defecto si no se encuentran variables

    Returns:
        Dict[str, List[str]]: El diccionario parseado
    """
    result = default_dict.copy() if default_dict else {}

    # Buscar todas las variables de entorno con el prefijo dado
    for key, value in os.environ.items():
        if key.startswith(prefix):
            endpoint = key[len(prefix):].lower()
            if value:
                result[endpoint] = parse_list_from_env(key)

    return result


class Settings:
    """Configuración de ajustes de la aplicación.

    Carga la configuración desde variables de entorno y proporciona
    valores predeterminados específicos del entorno.
    """

    def __init__(self):
        """Inicializar ajustes de la aplicación desde variables de entorno."""
        # Establecer el entorno
        self.ENVIRONMENT = os.getenv("APP_ENV", "development")

        # Configuración de la aplicación
        self.PROJECT_NAME = os.getenv("PROJECT_NAME", "Proceso Resumen BSG")
        self.VERSION = os.getenv("VERSION", "1.0.0")
        self.DESCRIPTION = os.getenv(
            "DESCRIPTION",
            "FastAPI, listo para producción."
        )
        self.DEBUG = parse_bool(os.getenv("DEBUG"), default=False)
        self.HOST = os.getenv("HOST", "127.0.0.1")
        self.PORT = parse_int(os.getenv("HOST", "5050"), default=5050)

        # Configuración CORS
        self.ALLOWED_ORIGINS = parse_list_from_env("ALLOWED_ORIGINS", ["*"])

        #Configurams VIMEO:
        self.VIMEO_ACCESS_TOKEN = os.getenv("VIMEO_ACCESS_TOKENVIMEO_ACCESS_TOKE", None)

        #Configuracion Azure Speech to text
        self.AZURE_SPEECH_KEY = os.getenv("AZURE_SPEECH_KEY", None)
        self.AZURE_SPEECH_REGION = os.getenv("AZURE_SPEECH_REGION", None)
        self.AZURE_BLOB_CONNECTION_STRING = os.getenv("AZURE_BLOB_CONNECTION_STRING", None)

        
        # Configuración de LLMs
        self.LLM_PROVIDER = os.getenv("LLM_PROVIDER", None)
        self.OPENAI_API_KEY = os.getenv("OPENAI_API_KEY", None)
        self.GOOGLE_APPLICATION_CREDENTIALS = os.getenv("GOOGLE_APPLICATION_CREDENTIALS", None)
        self.GEMINI_API_KEY = os.getenv("GEMINI_API_KEY", None)
        self.OPENAI_MODEL = os.getenv("OPENAI_MODEL", "gpt-5-mini")
        self.VERTEXAI_MODEL = os.getenv("VERTEXAI_MODEL", "gemini-2.5-flash")
        self.GEMINI_MODEL = os.getenv("GEMINI_MODEL", "gemini-2.5-flash")

        self.DEFAULT_LLM_TEMPERATURE = parse_float(
            os.getenv("DEFAULT_LLM_TEMPERATURE"),
            default=0.2
        )
        self.MAX_LLM_CALL_RETRIES = parse_int(
            os.getenv("MAX_LLM_CALL_RETRIES"),
            default=3
        )

        # Configuración de logging
        self.LOG_DIR = Path(os.getenv("LOG_DIR", "logs"))

        # Configuración de SQLite para Checkpoints
        self.SQLITE_PATH = os.getenv("SQLITE_PATH", None)

        # Configuración de SQL Server
        self.SQLSERVER_HOST = os.getenv("SQLSERVER_HOST", "localhost")
        self.SQLSERVER_DB = os.getenv("SQLSERVER_DB", "db_sqlserver")
        self.SQLSERVER_USER = os.getenv("SQLSERVER_USER", "user_sqlserver")
        self.SQLSERVER_PASSWORD = os.getenv("SQLSERVER_PASSWORD", "pass_sqlserver")
        self.SQLSERVER_DRIVER = os.getenv("SQLSERVER_DRIVER", "ODBC Driver 18 for SQL Server")
        self.SQLSERVER_PORT = os.getenv("SQLSERVER_PORT", "1433")



    def get_database_sql_server_url(self):
        return (
            f"Driver={self.SQLSERVER_DRIVER};"
            f"Server={self.SQLSERVER_HOST},{self.SQLSERVER_PORT};"
            f"Database={self.SQLSERVER_DB};"
            f"Uid={self.SQLSERVER_USER};"
            f"Pwd={self.SQLSERVER_PASSWORD};"
            "Encrypt=yes;"
            "TrustServerCertificate=yes;"
        )

    def __repr__(self) -> str:
        """Representación de cadena de configuración (ocultando datos sensibles)."""
        safe_dict = {}
        for key, value in self.__dict__.items():
            if "PASSWORD" in key or "KEY" in key or "SECRET" in key:
                safe_dict[key] = "***HIDDEN***"
            else:
                safe_dict[key] = value
        return f"Settings({safe_dict})"


# Crear instancia de configuración
settings = Settings()
