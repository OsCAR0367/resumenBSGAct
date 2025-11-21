from pydantic import BaseModel


class SummaryRequest(BaseModel):
    transcription_path: str
    output_directory: str = "data/temp/summary"


class SummaryResponse(BaseModel):
    message: str = "summary schema defect"
    summary_path: str