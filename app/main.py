from fastapi import FastAPI
from app.api.routes import  big_workflow
from scripts.logging_config import setup_logging

setup_logging()

app = FastAPI(
    title="Video and Audio Processing API",
    version="1.0.0",
    description="API for video processing, transcription, summarization, study guides, podcasts, and concept maps"
)

app.include_router(big_workflow.router, prefix="/api/v1/workflow", tags=["Workflow"])
