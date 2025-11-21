from pydantic import BaseModel

# Default directories
DEFAULT_SUMMARY_PATH = r"data/temp/summary/transcription_summary.txt"
DEFAULT_AUDIO_OUTPUT_PATH = r"data/output/podcast/podcast_summary.wav"
DEFAULT_SCRIPT_OUTPUT_PATH = r"data/temp/podcast/podcast_script.txt"


class PodcastRequest(BaseModel):
    summary_file: str = DEFAULT_SUMMARY_PATH
    audio_output: str = DEFAULT_AUDIO_OUTPUT_PATH
    script_output: str = DEFAULT_SCRIPT_OUTPUT_PATH


class PodcastResponse(BaseModel):
    message: str = "podcast schema defect"
    script_output: str
    audio_output: str