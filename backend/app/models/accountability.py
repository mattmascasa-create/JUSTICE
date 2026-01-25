"""
Officer Accountability Database Models
Tracks officer profiles, violations, and generates accountability scores
"""
from datetime import datetime, timezone
from typing import Optional, List, Dict
from pydantic import BaseModel, Field
from enum import Enum


class ViolationSeverity(str, Enum):
    MINOR = "minor"           # Warning-level (weight: 1)
    MODERATE = "moderate"     # Suspension-level (weight: 3)
    SERIOUS = "serious"       # Termination-level (weight: 5)
    CRITICAL = "critical"     # Criminal-level (weight: 10)


class ViolationType(str, Enum):
    # 4th Amendment
    UNLAWFUL_SEARCH = "unlawful_search"
    UNLAWFUL_SEIZURE = "unlawful_seizure"
    EXCESSIVE_FORCE = "excessive_force"
    FALSE_ARREST = "false_arrest"
    
    # 5th Amendment
    MIRANDA_VIOLATION = "miranda_violation"
    COERCED_CONFESSION = "coerced_confession"
    SELF_INCRIMINATION = "self_incrimination"
    
    # 1st Amendment
    RECORDING_INTERFERENCE = "recording_interference"
    SPEECH_SUPPRESSION = "speech_suppression"
    ASSEMBLY_INTERFERENCE = "assembly_interference"
    
    # 14th Amendment
    RACIAL_PROFILING = "racial_profiling"
    DISCRIMINATORY_ENFORCEMENT = "discriminatory_enforcement"
    DUE_PROCESS_VIOLATION = "due_process_violation"
    
    # Professional Misconduct
    DISHONESTY = "dishonesty"
    EVIDENCE_TAMPERING = "evidence_tampering"
    INTIMIDATION = "intimidation"
    RETALIATION = "retaliation"
    POLICY_VIOLATION = "policy_violation"
    CONDUCT_UNBECOMING = "conduct_unbecoming"


class ViolationOutcome(str, Enum):
    PENDING = "pending"
    SUSTAINED = "sustained"
    NOT_SUSTAINED = "not_sustained"
    EXONERATED = "exonerated"
    UNFOUNDED = "unfounded"
    POLICY_FAILURE = "policy_failure"


class DisciplinaryAction(str, Enum):
    NONE = "none"
    VERBAL_WARNING = "verbal_warning"
    WRITTEN_WARNING = "written_warning"
    RETRAINING = "retraining"
    SUSPENSION = "suspension"
    DEMOTION = "demotion"
    TERMINATION = "termination"
    CRIMINAL_CHARGES = "criminal_charges"


# ============== Officer Models ==============

class OfficerCreate(BaseModel):
    badge_number: str
    department_id: str
    first_name: str
    last_name: str
    rank: Optional[str] = "Officer"
    unit: Optional[str] = None
    hire_date: Optional[str] = None
    photo_url: Optional[str] = None


class OfficerProfile(BaseModel):
    officer_id: str
    badge_number: str
    department_id: str
    department_name: str
    first_name: str
    last_name: str
    full_name: str
    rank: str = "Officer"
    unit: Optional[str] = None
    hire_date: Optional[str] = None
    photo_url: Optional[str] = None
    
    # Accountability Metrics
    accountability_score: float = 100.0  # 0-100, starts at 100
    total_violations: int = 0
    sustained_violations: int = 0
    pending_violations: int = 0
    
    # Violation Breakdown
    violations_by_type: Dict[str, int] = {}
    violations_by_severity: Dict[str, int] = {}
    
    # Outcomes
    disciplinary_actions: List[str] = []
    settlements_involved: int = 0
    settlement_total: float = 0.0
    
    # Status
    status: str = "active"  # active, suspended, terminated, resigned
    last_incident_date: Optional[str] = None
    created_at: str
    updated_at: str


class OfficerViolation(BaseModel):
    violation_id: str
    officer_id: str
    badge_number: str
    department_id: str
    encounter_id: Optional[str] = None
    
    # Violation Details
    violation_type: ViolationType
    severity: ViolationSeverity
    description: str
    
    # Evidence Links
    evidence_ids: List[str] = []
    ai_analysis_id: Optional[str] = None
    ai_confidence: Optional[float] = None
    
    # Location/Time
    incident_date: str
    incident_location: Optional[Dict] = None
    
    # Legal References
    constitutional_amendment: Optional[str] = None
    relevant_statutes: List[str] = []
    case_law_citations: List[str] = []
    
    # Outcome
    outcome: ViolationOutcome = ViolationOutcome.PENDING
    disciplinary_action: DisciplinaryAction = DisciplinaryAction.NONE
    settlement_amount: Optional[float] = None
    
    # Reporter
    reported_by: str  # user_id
    reporter_type: str = "citizen"  # citizen, attorney, internal
    
    # Verification
    verified: bool = False
    verified_by: Optional[str] = None
    verified_at: Optional[str] = None
    
    # Chain of Custody
    evidence_hash: Optional[str] = None
    blockchain_proof: Optional[Dict] = None
    
    created_at: str
    updated_at: str


# ============== Department Models ==============

class DepartmentCreate(BaseModel):
    name: str
    city: str
    state: str
    county: Optional[str] = None
    jurisdiction_type: str = "municipal"  # municipal, county, state, federal
    total_officers: Optional[int] = None
    website: Optional[str] = None


class DepartmentProfile(BaseModel):
    department_id: str
    name: str
    city: str
    state: str
    county: Optional[str] = None
    jurisdiction_type: str = "municipal"
    total_officers: int = 0
    website: Optional[str] = None
    
    # Accountability Score (0-100)
    accountability_score: float = 100.0
    transparency_grade: str = "A"  # A, B, C, D, F
    
    # Scoring Components (each 0-100)
    use_of_force_score: float = 100.0
    complaint_resolution_score: float = 100.0
    settlement_score: float = 100.0
    officer_accountability_score: float = 100.0
    transparency_score: float = 100.0
    
    # Aggregate Stats
    total_violations: int = 0
    sustained_violations: int = 0
    pending_violations: int = 0
    
    # Officer Stats
    officers_with_violations: int = 0
    repeat_offenders: int = 0  # 3+ violations
    
    # Financial
    total_settlements: float = 0.0
    avg_settlement: float = 0.0
    
    # Violations by Type
    violations_by_type: Dict[str, int] = {}
    violations_by_severity: Dict[str, int] = {}
    
    # Rankings
    state_rank: Optional[int] = None
    national_rank: Optional[int] = None
    
    # Metadata
    last_incident_date: Optional[str] = None
    data_last_updated: str
    created_at: str


# ============== Scoring Weights ==============

VIOLATION_SEVERITY_WEIGHTS = {
    ViolationSeverity.MINOR: 1,
    ViolationSeverity.MODERATE: 3,
    ViolationSeverity.SERIOUS: 5,
    ViolationSeverity.CRITICAL: 10
}

DEPARTMENT_SCORE_WEIGHTS = {
    "use_of_force": 0.25,
    "complaint_resolution": 0.20,
    "settlements": 0.15,
    "officer_accountability": 0.20,
    "transparency": 0.20
}

# Constitutional mapping for violations
VIOLATION_AMENDMENTS = {
    ViolationType.UNLAWFUL_SEARCH: "4th Amendment",
    ViolationType.UNLAWFUL_SEIZURE: "4th Amendment",
    ViolationType.EXCESSIVE_FORCE: "4th Amendment",
    ViolationType.FALSE_ARREST: "4th Amendment",
    ViolationType.MIRANDA_VIOLATION: "5th Amendment",
    ViolationType.COERCED_CONFESSION: "5th Amendment",
    ViolationType.SELF_INCRIMINATION: "5th Amendment",
    ViolationType.RECORDING_INTERFERENCE: "1st Amendment",
    ViolationType.SPEECH_SUPPRESSION: "1st Amendment",
    ViolationType.ASSEMBLY_INTERFERENCE: "1st Amendment",
    ViolationType.RACIAL_PROFILING: "14th Amendment",
    ViolationType.DISCRIMINATORY_ENFORCEMENT: "14th Amendment",
    ViolationType.DUE_PROCESS_VIOLATION: "14th Amendment",
}
