import asyncio
import logging
from pathlib import Path
import re
import os

# Logger específico para infraestructura
logger = logging.getLogger(__name__)

class AudioExtractionError(Exception):
    """Excepción personalizada para fallos en la extracción de audio."""
    pass

async def extract_audio_async(video_path: str, output_directory: str = None) -> str:
    """
    Extrae el audio de un video de forma asíncrona utilizando FFmpeg.
    No bloquea el Event Loop de Python.

    Args:
        video_path (str): Ruta absoluta del archivo de video.
        output_directory (str, optional): Carpeta donde guardar el audio. 
                                          Si es None, usa la misma del video.

    Returns:
        str: Ruta absoluta del archivo de audio generado (.mp3).
    """
    video_p = Path(video_path)

    if not video_p.exists():
        raise FileNotFoundError(f"Video no encontrado: {video_path}")

    # 1. Definir ruta de salida
    if output_directory:
        # Asegurar que el directorio existe (safe síncrono porque es rápido)
        os.makedirs(output_directory, exist_ok=True)
        # Limpiar nombre de archivo
        safe_stem = re.sub(r"[^\w.-]+", "_", video_p.stem)
        audio_p = Path(output_directory) / f"{safe_stem}.mp3"
    else:
        # Por defecto en la misma carpeta del video
        safe_stem = re.sub(r"[^\w.-]+", "_", video_p.stem)
        audio_p = video_p.parent / f"{safe_stem}.mp3"

    output_path_str = str(audio_p)
    
    logger.info(f"Iniciando extracción asíncrona: {video_p.name} -> {audio_p.name}")

    # 2. Construir comando FFmpeg
    # -y: Sobrescribir sin preguntar
    # -vn: No video
    # -ac 1: Mono
    # -ar 16000: 16kHz
    # -b:a 32k: Bitrate ligero
    cmd = [
        "ffmpeg",
        "-y",
        "-i", str(video_p),
        "-vn",
        "-ac", "1",
        "-ar", "16000",
        "-c:a", "libmp3lame",
        "-b:a", "32k",
        "-f", "mp3",
        output_path_str
    ]

    try:
        # 3. Ejecutar subproceso de forma NO BLOQUEANTE
        process = await asyncio.create_subprocess_exec(
            *cmd,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE
        )

        # Esperar a que termine sin detener el servidor
        stdout, stderr = await process.communicate()

        # 4. Verificar resultado
        if process.returncode != 0:
            error_msg = stderr.decode().strip()
            logger.error(f"FFmpeg falló con código {process.returncode}: {error_msg}")
            raise AudioExtractionError(f"Error en FFmpeg: {error_msg}")

        logger.info(f"Extracción completada exitosamente: {output_path_str}")
        return output_path_str

    except AudioExtractionError:
        raise
    except Exception as e:
        logger.error(f"Error inesperado en extracción asíncrona: {str(e)}")
        raise AudioExtractionError(f"Fallo sistémico al extraer audio: {str(e)}")