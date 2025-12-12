import os
import logging
from dotenv import load_dotenv

from app.infrastructure.video.vimeo_downloader import download_video_vimeo_async
from app.schemas.video_schema import VideoResponse
from app.infrastructure.client.vimeo_client import VimeoClient
from app.core.setup_config import settings

logger = logging.getLogger(__name__)
load_dotenv()

class VideoService:
    def __init__(self):
        self.vimeo = VimeoClient(access_token=settings.VIMEO_ACCESS_TOKEN)

    async def download_video(self, vimeo_url: str, download_directory: str, filename_prefix: str) -> str:
        file_path = await self.vimeo.process_video_url(
            vimeo_full_url=vimeo_url,
            output_dir=download_directory,
            file_prefix=filename_prefix
        )
        return file_path