from pydantic import BaseModel


class AudioExtractionRequest(BaseModel):
    video_path: str
    output_directory: str = "data/temp/audios"


class AudioResponse(BaseModel):
    message: str = "audio schema defect"
    audio_path: str