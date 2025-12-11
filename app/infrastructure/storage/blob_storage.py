import logging
import os
import aiofiles
from datetime import datetime, timedelta, timezone
from pathlib import Path

# Cliente Asíncrono de Azure Storage
from azure.storage.blob.aio import BlobServiceClient
from azure.storage.blob import generate_blob_sas, BlobSasPermissions, ContentSettings

# Importamos la instancia 'settings' (no la clase) para acceder a las variables cargadas
from app.core.setup_config import settings

logger = logging.getLogger(__name__)

class BlobStorageError(Exception):
    """Excepción para errores en la capa de almacenamiento."""
    pass

async def upload_file_to_blob_async(
    local_path: str, 
    blob_subfolder: str, 
    content_type: str = 'application/octet-stream'
) -> str:
    """
    Sube un archivo genérico a Azure Blob Storage de forma asíncrona.

    Args:
        local_path (str): Ruta absoluta del archivo local.
        blob_subfolder (str): Carpeta virtual dentro del contenedor (ej: 'AudioSesion', 'PDFs').
        content_type (str): Tipo MIME del archivo (ej: 'audio/mpeg', 'application/pdf').
                            Por defecto es 'application/octet-stream'.

    Returns:
        str: La URL pública del blob con un token SAS adjunto para acceso temporal.
    """
    local_file = Path(local_path)
    if not local_file.exists():
        raise FileNotFoundError(f"Archivo no encontrado para subir: {local_path}")

    # Obtener configuración desde settings
    conn_str = settings.AZURE_BLOB_CONNECTION_STRING
    container_name = settings.AZURE_BLOB_CONTAINER
    
    if not conn_str or not container_name:
        raise ValueError("Configuración de Azure Blob incompleta (CONNECTION_STRING o CONTAINER).")

    # Construir nombre del blob: carpeta/nombre_archivo
    blob_name = f"{blob_subfolder}/{local_file.name}".lstrip("/")
    
    logger.info(f"Iniciando subida asíncrona: {local_file.name} -> {container_name}/{blob_name} (Tipo: {content_type})")

    try:
        # 1. Crear cliente de servicio asíncrono
        blob_service_client = BlobServiceClient.from_connection_string(conn_str)

        # Usamos 'async with' para gestionar la sesión HTTP
        async with blob_service_client:
            # Obtener cliente del blob específico
            blob_client = blob_service_client.get_blob_client(container=container_name, blob=blob_name)
            
            # 2. Leer archivo y subir (Streaming)
            async with aiofiles.open(local_file, "rb") as f:
                data = await f.read()
                
                # Subir los datos configurando el Content-Type correcto
                await blob_client.upload_blob(
                    data, 
                    overwrite=True, 
                    content_settings=ContentSettings(content_type=content_type)
                )
        
        logger.info("Subida completada exitosamente.")

        # 3. Generar SAS Token (Síncrono, operación de CPU)
        # Requerimos el nombre de la cuenta y la clave para firmar
        account_name = blob_service_client.account_name
        account_key = blob_service_client.credential.account_key

        sas_token = generate_blob_sas(
            account_name=account_name,
            container_name=container_name,
            blob_name=blob_name,
            account_key=account_key,
            permission=BlobSasPermissions(read=True),
            expiry=datetime.now(timezone.utc) + timedelta(minutes=120) # Expira en 2 horas
        )
        
        # Construir la URL completa
        # blob_client.url contiene la ruta base (https://cuenta.blob.core.../contenedor/archivo)
        sas_url = f"{blob_client.url}?{sas_token}"
        
        return sas_url

    except Exception as e:
        logger.error(f"Error en subida AIO a Azure: {str(e)}")
        raise BlobStorageError(f"Fallo al subir a Blob Storage: {e}")