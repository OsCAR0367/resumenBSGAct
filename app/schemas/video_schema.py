from pydantic import BaseModel

class VideoDownloadRequest(BaseModel):
    vimeo_url: str
    download_directory: str = "data/input/videos"

class VideoResponse(BaseModel):
    message: str = "El video schema defect"
    file_path: str
