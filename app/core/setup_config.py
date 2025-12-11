import os
from enum import Enum
from pathlib import Path
from typing import Any, Dict, List, Optional

from dotenv import load_dotenv

# Definir tipos de entorno
class Environment(str, Enum):
    DEVELOPMENT = "development"
    PRODUCTION = "production"
    TEST = "test"

# Definir niveles de log
class LogLevel(str, Enum):
    DEBUG = "DEBUG"
    INFO = "INFO"
    WARNING = "WARNING"
    ERROR = "ERROR"
    CRITICAL = "CRITICAL"

def load_env_file() -> Optional[str]:
    base_dir = Path(__file__).resolve().parent.parent.parent
    env_files = [
        base_dir / f".env.production",
        base_dir / f".env.test",
        base_dir / f".env.development",
        base_dir / ".env",
    ]
    for env_file in env_files:
        if env_file.is_file():
            load_dotenv(dotenv_path=str(env_file), override=True)
            print(f"Loaded environment from {env_file}")
            return str(env_file)
    print("No .env file found, using system environment variables")
    return None

ENV_FILE = load_env_file()

# Funciones auxiliares
def parse_bool(value: Optional[str], default: bool = False) -> bool:
    if value is None: return default
    return value.lower() in ("true", "1", "t", "yes", "on")

def parse_int(value: Optional[str], default: int) -> int:
    if value is None: return default
    try: return int(value)
    except ValueError: return default

def parse_float(value: Optional[str], default: float) -> float:
    if value is None: return default
    try: return float(value)
    except ValueError: return default

def parse_list_from_env(env_key: str, default: Optional[List[str]] = None) -> List[str]:
    value = os.getenv(env_key)
    if not value: return default or []
    value = value.strip("\"'")
    if not value: return default or []
    if "," not in value: return [value.strip()]
    return [item.strip() for item in value.split(",") if item.strip()]

def parse_dict_of_lists_from_env(prefix: str, default_dict: Optional[Dict[str, List[str]]] = None) -> Dict[str, List[str]]:
    result = default_dict.copy() if default_dict else {}
    for key, value in os.environ.items():
        if key.startswith(prefix):
            endpoint = key[len(prefix):].lower()
            if value:
                result[endpoint] = parse_list_from_env(key)
    return result

class Settings:
    """Configuración de ajustes de la aplicación."""

    def __init__(self):
        """Inicializar ajustes de la aplicación desde variables de entorno."""
        
        # ### CORRECCIÓN 1: Definir BASE_DIR al inicio ###
        self.BASE_DIR = Path(__file__).resolve().parent.parent.parent

        # Establecer el entorno
        self.ENVIRONMENT = os.getenv("APP_ENV", "development")

        # Directorios
        self.DATA_DIR = self.BASE_DIR / 'data'
        self.INPUT_VIDEO_DIR = self.DATA_DIR / 'input' / 'videos'

        self.FFMPEG_BINARY_PATH = r"C:\ffmpeg\ffmpeg\bin\ffmpeg.EXE"
        # Outputs
        self.OUTPUT_DIR = self.DATA_DIR / 'output'
        self.CONCEPT_MAP_OUTPUT_DIR = self.OUTPUT_DIR / 'concept_map'
        self.PODCAST_OUTPUT_DIR = self.OUTPUT_DIR / 'podcast'
        self.STUDY_GUIDE_OUTPUT_DIR = self.OUTPUT_DIR / 'study_guides'
        self.TRANSCRIPTIONS_OUTPUT_DIR = self.OUTPUT_DIR / 'transcriptions'
        self.VIDEOS_OUTPUT_DIR = self.OUTPUT_DIR / 'videos'

        # Temps
        self.TEMP_DIR = self.DATA_DIR / 'temp'
        self.TEMP_SUMMARY_DIR = self.TEMP_DIR / 'summary'
        self.TEMP_PODCAST_DIR = self.TEMP_DIR / 'podcast'
        self.TEMP_AUDIOS_DIR = self.TEMP_DIR / 'audios'
        self.TEMP_CHUNKS_DIR = self.TEMP_DIR / 'chunks'

        # Llamada al método para crear directorios
        self._create_dirs()
        
        # Configuración de la aplicación
        self.PROJECT_NAME = os.getenv("PROJECT_NAME", "Proceso Resumen BSG")
        self.VERSION = os.getenv("VERSION", "1.0.0")
        self.DESCRIPTION = os.getenv("DESCRIPTION", "FastAPI, listo para producción.")
        self.DEBUG = parse_bool(os.getenv("DEBUG"), default=False)
        self.HOST = os.getenv("HOST", "127.0.0.1")
        self.PORT = parse_int(os.getenv("PORT", "5050"), default=5050)

        # Configuración CORS
        self.ALLOWED_ORIGINS = parse_list_from_env("ALLOWED_ORIGINS", ["*"])

        # VIMEO
        self.VIMEO_ACCESS_TOKEN = os.getenv("VIMEO_ACCESS_TOKEN", None)

        # Azure Speech / Blob
        self.AZURE_SPEECH_KEY = os.getenv("AZURE_SPEECH_KEY", None)
        self.AZURE_SPEECH_REGION = os.getenv("AZURE_SPEECH_REGION", None)
        self.AZURE_BLOB_CONNECTION_STRING = os.getenv("AZURE_BLOB_CONNECTION_STRING", None)
        self.AZURE_BLOB_CONTAINER = os.getenv("AZURE_BLOB_CONTAINER", "procesoresumenia")
        
        # Carpetas Virtuales Blob
        self.AZURE_BLOB_SUBFOLDER_PDFS = os.getenv("AZURE_BLOB_SUBFOLDER_PDFS", "PDFs")
        self.AZURE_BLOB_SUBFOLDER_AUDIO = os.getenv("AZURE_BLOB_SUBFOLDER_AUDIO", "ResumenAudio")
        self.AZURE_BLOB_SUBFOLDER_AUDIOSESION = os.getenv("AZURE_BLOB_SUBFOLDER_AUDIOSESION", "AudioSesion")
        
        # LLMs
        self.LLM_PROVIDER = os.getenv("LLM_PROVIDER", None)
        self.OPENAI_API_KEY = os.getenv("OPENAI_API_KEY", None)
        self.GOOGLE_APPLICATION_CREDENTIALS = os.getenv("GOOGLE_APPLICATION_CREDENTIALS", None)
        self.GEMINI_API_KEY = os.getenv("GEMINI_API_KEY", None)
        self.OPENAI_MODEL = os.getenv("OPENAI_MODEL", "gpt-4o")
        self.VERTEXAI_MODEL = os.getenv("VERTEXAI_MODEL", "gemini-2.5-flash")
        self.GEMINI_MODEL = os.getenv("GEMINI_MODEL", "gemini-2.5-flash")

        self.DEFAULT_LLM_TEMPERATURE = parse_float(os.getenv("DEFAULT_LLM_TEMPERATURE"), default=0.2)
        self.MAX_LLM_CALL_RETRIES = parse_int(os.getenv("MAX_LLM_CALL_RETRIES"), default=3)

        # Logging y DB
        self.LOG_DIR = Path(os.getenv("LOG_DIR", "logs"))
        self.SQLITE_PATH = os.getenv("SQLITE_PATH", None)

        self.SQLSERVER_HOST = os.getenv("SQLSERVER_HOST", "localhost")
        self.SQLSERVER_DB = os.getenv("SQLSERVER_DB", "db_sqlserver")
        self.SQLSERVER_USER = os.getenv("SQLSERVER_USER", "user_sqlserver")
        self.SQLSERVER_PASSWORD = os.getenv("SQLSERVER_PASSWORD", "pass_sqlserver")
        self.SQLSERVER_DRIVER = os.getenv("SQLSERVER_DRIVER", "ODBC Driver 18 for SQL Server")
        self.SQLSERVER_PORT = os.getenv("SQLSERVER_PORT", "1433")

        self.MERMAID_CLI_PATH = os.getenv("MERMAID_CLI_PATH", "mmdc")
        self.TUTOR_VIRTUAL_API = os.getenv("TUTOR_VIRTUAL_API", "")

    # ### CORRECCIÓN 2: Agregar el método que faltaba ###
    def _create_dirs(self):
        """Crea los directorios necesarios si no existen."""
        dirs_to_create = [
            self.DATA_DIR,
            self.INPUT_VIDEO_DIR,
            self.OUTPUT_DIR,
            self.CONCEPT_MAP_OUTPUT_DIR,
            self.PODCAST_OUTPUT_DIR,
            self.STUDY_GUIDE_OUTPUT_DIR,
            self.TRANSCRIPTIONS_OUTPUT_DIR,
            self.VIDEOS_OUTPUT_DIR,
            self.TEMP_DIR,
            self.TEMP_SUMMARY_DIR,
            self.TEMP_PODCAST_DIR,
            self.TEMP_AUDIOS_DIR,
            self.TEMP_CHUNKS_DIR
        ]
        for d in dirs_to_create:
            d.mkdir(parents=True, exist_ok=True)

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
        safe_dict = {}
        for key, value in self.__dict__.items():
            if "PASSWORD" in key or "KEY" in key or "SECRET" in key:
                safe_dict[key] = "***HIDDEN***"
            else:
                safe_dict[key] = value
        return f"Settings({safe_dict})"

# Crear instancia de configuración
settings = Settings()