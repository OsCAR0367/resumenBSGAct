from pydantic import BaseModel


class TranscriptionRequest(BaseModel):
    audio_path: str
    output_directory: str = "data/output/transcriptions"


class TranscriptionResponse(BaseModel):
    message: str = "transcription schema defect"
    transcription_path: str