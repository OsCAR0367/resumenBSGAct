import os
from pathlib import Path
from dotenv import load_dotenv

BASE_DIR = Path(__file__).resolve().parent.parent 
ENV_FILE = BASE_DIR / '.env'

if ENV_FILE.exists():
    load_dotenv(ENV_FILE)

class Config:
    """
    Clase centralizada para configuración de APIs.
    """
    
    AZURE_SPEECH_KEY = os.getenv("AZURE_SPEECH_KEY", "")
    AZURE_SPEECH_REGION = os.getenv("AZURE_SPEECH_REGION", "eastus")

    _gcp_cred_path = os.getenv("GOOGLE_APPLICATION_CREDENTIALS", "")
    
    if _gcp_cred_path:
        GOOGLE_APPLICATION_CREDENTIALS = str(BASE_DIR / _gcp_cred_path)
        
        os.environ["GOOGLE_APPLICATION_CREDENTIALS"] = GOOGLE_APPLICATION_CREDENTIALS
    else:
        GOOGLE_APPLICATION_CREDENTIALS = None

    VIMEO_ACCESS_TOKEN = os.getenv("VIMEO_ACCESS_TOKEN", "")
    
    OPENAI_API_KEY = os.getenv("OPENAI_API_KEY", "")