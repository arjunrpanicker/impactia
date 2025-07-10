from pydantic import BaseModel
from typing import List, Optional
from fastapi import UploadFile, Form

class ChangedMethod(BaseModel):
    file_path: str
    method: str
    summary: str

class ImpactedMethod(BaseModel):
    file_path: str
    method: str
    impact_reason: str
    impact_description: str

class ImpactAnalysisResponse(BaseModel):
    changed_methods: List[ChangedMethod]
    impacted_methods: List[ImpactedMethod]
    dependency_chain: List[str]

class ImpactAnalysisRequestForm:
    def __init__(
        self,
        base_files: List[UploadFile],
        updated_files: List[UploadFile],
        file_paths: List[str] = Form(default=[])
    ):
        self.base_files = base_files
        self.updated_files = updated_files
        self.file_paths = file_paths