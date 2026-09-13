from pydantic import BaseModel, Field


class AnalysisCreate(BaseModel):
    project_name: str = Field(min_length=1, max_length=255)
    file_name: str = Field(min_length=1, max_length=500)
    content: str = Field(min_length=1)


class AnalysisResponse(BaseModel):
    id: int
    project_name: str
    file_name: str
    analysis_type: str
    status: str
    result: str | None = None

    class Config:
        from_attributes = True
