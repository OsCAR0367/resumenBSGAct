import logging
import os
import aiofiles  # Para lectura de disco no bloqueante
from datetime import datetime, timedelta, timezone
from pathlib import Path

# Importamos el Cliente Asíncrono
from azure.storage.blob.aio import BlobServiceClient
from azure.storage.blob import generate_blob_sas, BlobSasPermissions, ContentSettings

from app.daemons.config import Config

logger = logging.getLogger(__name__)

class BlobStorageError(Exception):
    """Excepción para errores en la capa de almacenamiento."""
    pass

async def upload_audio_to_blob_async(local_path: str, blob_subfolder: str = "AudioSesion") -> str:
    """
    Sube un archivo de audio a Azure Blob Storage utilizando la implementación 
    nativa AIO (Asynchronous I/O).
    
    1. Lee el archivo del disco de forma asíncrona.
    2. Sube el stream a Azure sin bloquear el Event Loop.
    3. Genera y retorna la URL con firma SAS.
    """
    local_file = Path(local_path)
    if not local_file.exists():
        raise FileNotFoundError(f"Archivo no encontrado para subir: {local_path}")

    # Validar configuración
    conn_str = Config.AZURE_BLOB_CONNECTION_STRING
    container_name = Config.AZURE_BLOB_CONTAINER
    
    if not conn_str or not container_name:
        raise ValueError("Configuración de Azure Blob incompleta (CONNECTION_STRING o CONTAINER).")

    blob_name = f"{blob_subfolder}/{local_file.name}".lstrip("/")
    
    logger.info(f"Iniciando subida nativa AIO: {local_file.name} -> {container_name}/{blob_name}")

    try:
        # 1. Crear el cliente de servicio asíncrono
        blob_service_client = BlobServiceClient.from_connection_string(conn_str)

        # Usamos 'async with' para asegurar que la sesión HTTP se cierre correctamente
        async with blob_service_client:
            # Obtener cliente del blob específico
            blob_client = blob_service_client.get_blob_client(container=container_name, blob=blob_name)
            
            # 2. Leer archivo y subir (Streaming asíncrono)
            # Usamos aiofiles para no bloquear el disco mientras leemos
            async with aiofiles.open(local_file, "rb") as f:
                data = await f.read()
                
                # Subir los datos
                # content_settings ayuda a que el navegador/reproductor identifique el tipo
                await blob_client.upload_blob(
                    data, 
                    overwrite=True, 
                    content_settings=ContentSettings(content_type='audio/mpeg')
                )
        
        logger.info("Subida completada exitosamente.")

        # 3. Generar SAS Token (Operación puramente criptográfica/CPU, rápida)
        # Nota: generate_blob_sas es síncrona, pero al ser pura CPU y rápida, no afecta el rendimiento.
        # Necesitamos la key de la cuenta para firmar.
        
        # Extraemos la key del cliente (parseando la connection string internamente si es necesario)
        # Ojo: blob_service_client.credential puede ser un objeto o dict dependiendo de cómo se autenticó.
        # Si usas Connection String, 'credential' suele tener 'account_name' y 'account_key'.
        
        # Una forma más robusta si ya tienes la conn_string es recrear un objeto cliente ligero síncrono 
        # solo para extraer credenciales, O confiar en que Config tiene lo necesario.
        # Para simplificar y evitar doble dependencia, asumiremos que la connection string es válida.
        
        # Truco: Usamos las propiedades del cliente asíncrono que ya tenemos instanciado.
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
        
        # Construir la URL firmada
        # blob_client.url ya contiene la ruta base
        sas_url = f"{blob_client.url}?{sas_token}"
        
        return sas_url

    except Exception as e:
        logger.error(f"Error en subida AIO a Azure: {str(e)}")
        raise BlobStorageError(f"Fallo al subir a Blob Storage: {e}")