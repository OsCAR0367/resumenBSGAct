from pydantic import BaseModel

# Default paths
DEFAULT_SUMMARY_PATH = r"data/temp/summary/summary.txt"
DEFAULT_OUTPUT_DIR = r"data/output/concept_map"


class ConceptMapRequest(BaseModel):
    summary_path: str = DEFAULT_SUMMARY_PATH
    output_dir: str = DEFAULT_OUTPUT_DIR


class ConceptMapResponse(BaseModel):
    message: str
    output_path: str