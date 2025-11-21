from pydantic import BaseModel


class StudyGuideRequest(BaseModel):
    summary_path: str
    output_directory: str = "data/output/study_guides"


class StudyGuideResponse(BaseModel):
    message: str = "study guide schema defect"
    study_guide_path: str