from fastapi import APIRouter, HTTPException
from sqlalchemy.orm import Session
from fastapi import Depends

from app.api.dependencies import get_db
from app.services.video_service import VideoService
from app.schemas.video_schema import VideoDownloadRequest, VideoResponse
from app.core.logging_config import logger

router = APIRouter(tags=["Videos"])


@router.post("/download", summary="Download Vimeo Video", response_model=VideoResponse)

async def download_video_endpoint(
    request: VideoDownloadRequest,
    db: Session = Depends(get_db)
):
    """
    Descarga un video desde Vimeo
    """
    try:
        video_service = VideoService(db)
        result = await video_service.download_video(
            vimeo_url=request.vimeo_url,
            download_directory=request.download_directory
        )
        return result
    except Exception as e:
        logger.error(f"Error al descargar video: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))