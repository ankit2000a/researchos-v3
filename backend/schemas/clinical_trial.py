from pydantic import BaseModel, Field, field_validator
from typing import Optional, List, Any, Tuple
from datetime import datetime
from enum import Enum

class VerificationStatus(str, Enum):
    VERIFIED = "VERIFIED"
    GEOMETRIC_FAIL = "GEOMETRIC_FAIL"
    CRITICAL_CONFLICT = "CRITICAL_CONFLICT"
    MATH_ERROR = "MATH_ERROR"
    REVIEW_NEEDED = "REVIEW_NEEDED"
    UNVERIFIED = "UNVERIFIED"

class BoundingBox(BaseModel):
    x: float
    y: float
    w: float
    h: float
    page: int
    id: Optional[str] = None # traceable ID

class ClinicalDataField(BaseModel):
    value: Any
    extracted_value: Any
    source_text: Optional[str] = None
    coordinates: Optional[BoundingBox] = None
    confidence_score: float = 0.0
    verification_status: VerificationStatus = VerificationStatus.UNVERIFIED
    auditor_reasoning: Optional[str] = None
    thinking_log: Optional[str] = None # Chain of thought

class ClinicalTrialData(BaseModel):
    """
    Main Schema for Clinical Trial Data Extraction.
    """
    study_title: Optional[ClinicalDataField] = None
    p_value: Optional[ClinicalDataField] = None
    sample_size: Optional[ClinicalDataField] = None
    control_group_size: Optional[ClinicalDataField] = None
    treatment_group_size: Optional[ClinicalDataField] = None
    confidence_interval: Optional[ClinicalDataField] = None
    primary_endpoint_result: Optional[ClinicalDataField] = None
    
    # Validators can be added here for strict type checking if needed

class AuditLogEntry(BaseModel):
    """
    21 CFR Part 11 Compliant Log Entry.
    """
    timestamp: str = Field(default_factory=lambda: datetime.utcnow().isoformat())
    session_id: str
    data_field: str
    extracted_value: Any
    coordinates: Optional[List[float]] = None # [x, y, w, h]
    source_text_snippet: Optional[str] = None
    agent_reasoning: str
    thinking_log: Optional[str] = None
    bounding_box_id: Optional[str] = None
    confidence_score: float
    verification_status: str
    model_id: str
    previous_hash: Optional[str] = None # Hash Chain Link
    entry_hash: Optional[str] = None # Current Hash
