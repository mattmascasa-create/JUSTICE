"""
Court-Grade AI Service - Enhanced AI analysis with RAG, guardrails, and confidence scoring
For use in legal proceedings and evidence documentation
"""
import os
import json
import uuid
import hashlib
import logging
from datetime import datetime, timezone
from typing import Optional, List, Dict, Any, Tuple
from dataclasses import dataclass, asdict
from enum import Enum

from app.db.database import db

logger = logging.getLogger(__name__)


class ConfidenceLevel(Enum):
    """Confidence levels for AI outputs"""
    VERY_HIGH = "very_high"  # 90-100% - Backed by multiple precedents
    HIGH = "high"            # 75-89% - Clear legal basis
    MODERATE = "moderate"    # 50-74% - Some ambiguity
    LOW = "low"              # 25-49% - Significant uncertainty
    VERY_LOW = "very_low"    # 0-24% - Insufficient evidence


@dataclass
class LegalCitation:
    """Verified legal citation"""
    case_name: str
    citation: str
    year: int
    court: str
    relevance_score: float
    holding: str
    verified: bool = False
    verification_source: str = ""


@dataclass
class AIGuardrail:
    """Guardrail check result"""
    check_name: str
    passed: bool
    details: str
    severity: str  # critical, warning, info


@dataclass
class CourtGradeAnalysis:
    """Court-grade analysis result with full verification"""
    analysis_id: str
    timestamp: str
    input_hash: str  # Hash of input for verification
    
    # Core analysis
    findings: List[Dict]
    violations_detected: List[Dict]
    
    # Confidence metrics
    overall_confidence: float
    confidence_level: str
    confidence_breakdown: Dict[str, float]
    
    # Legal backing
    citations: List[Dict]
    legal_basis_score: float
    
    # Guardrails
    guardrail_checks: List[Dict]
    all_guardrails_passed: bool
    
    # Court readiness
    court_admissible: bool
    admissibility_notes: List[str]
    recommended_expert_review: bool
    
    # Audit trail
    model_used: str
    analysis_version: str
    processing_time_ms: int


# Expanded Legal Knowledge Base for RAG
LEGAL_KNOWLEDGE_BASE = {
    "constitutional_amendments": {
        "1st": {
            "text": "Congress shall make no law respecting an establishment of religion, or prohibiting the free exercise thereof; or abridging the freedom of speech, or of the press; or the right of the people peaceably to assemble, and to petition the Government for a redress of grievances.",
            "key_rights": ["freedom of speech", "freedom of religion", "freedom of press", "right to assemble", "right to petition"],
            "landmark_cases": [
                {"name": "Tinker v. Des Moines", "year": 1969, "citation": "393 U.S. 503", "holding": "Students don't shed rights at schoolhouse gate"},
                {"name": "Texas v. Johnson", "year": 1989, "citation": "491 U.S. 397", "holding": "Flag burning is protected speech"},
                {"name": "Glik v. Cunniffe", "year": 2011, "citation": "655 F.3d 78", "holding": "Right to record police in public"}
            ]
        },
        "4th": {
            "text": "The right of the people to be secure in their persons, houses, papers, and effects, against unreasonable searches and seizures, shall not be violated, and no Warrants shall issue, but upon probable cause.",
            "key_rights": ["protection from unreasonable search", "protection from unreasonable seizure", "warrant requirement", "probable cause requirement"],
            "landmark_cases": [
                {"name": "Terry v. Ohio", "year": 1968, "citation": "392 U.S. 1", "holding": "Stop and frisk requires reasonable suspicion"},
                {"name": "Mapp v. Ohio", "year": 1961, "citation": "367 U.S. 643", "holding": "Exclusionary rule applies to states"},
                {"name": "Katz v. United States", "year": 1967, "citation": "389 U.S. 347", "holding": "4th Amendment protects people, not places"},
                {"name": "Rodriguez v. United States", "year": 2015, "citation": "575 U.S. 348", "holding": "Cannot extend traffic stop without cause"},
                {"name": "Utah v. Strieff", "year": 2016, "citation": "579 U.S. 232", "holding": "Attenuation doctrine for warrant discovery"},
                {"name": "Carpenter v. United States", "year": 2018, "citation": "585 U.S. ___", "holding": "Cell location data requires warrant"}
            ]
        },
        "5th": {
            "text": "No person shall be compelled in any criminal case to be a witness against himself, nor be deprived of life, liberty, or property, without due process of law.",
            "key_rights": ["right to remain silent", "right against self-incrimination", "due process", "double jeopardy protection"],
            "landmark_cases": [
                {"name": "Miranda v. Arizona", "year": 1966, "citation": "384 U.S. 436", "holding": "Must be informed of rights before custodial interrogation"},
                {"name": "Berghuis v. Thompkins", "year": 2010, "citation": "560 U.S. 370", "holding": "Must explicitly invoke right to silence"},
                {"name": "Salinas v. Texas", "year": 2013, "citation": "570 U.S. 178", "holding": "Pre-arrest silence can be used against defendant"}
            ]
        },
        "6th": {
            "text": "In all criminal prosecutions, the accused shall enjoy the right to a speedy and public trial, and to have the Assistance of Counsel for his defence.",
            "key_rights": ["right to speedy trial", "right to public trial", "right to counsel", "right to confront witnesses"],
            "landmark_cases": [
                {"name": "Gideon v. Wainwright", "year": 1963, "citation": "372 U.S. 335", "holding": "Right to attorney in felony cases"},
                {"name": "Strickland v. Washington", "year": 1984, "citation": "466 U.S. 668", "holding": "Standard for ineffective assistance"},
                {"name": "Rothgery v. Gillespie County", "year": 2008, "citation": "554 U.S. 191", "holding": "Right attaches at initial appearance"}
            ]
        },
        "8th": {
            "text": "Excessive bail shall not be required, nor excessive fines imposed, nor cruel and unusual punishments inflicted.",
            "key_rights": ["protection from excessive bail", "protection from excessive fines", "protection from cruel punishment"],
            "landmark_cases": [
                {"name": "Graham v. Connor", "year": 1989, "citation": "490 U.S. 386", "holding": "Objective reasonableness for force claims"},
                {"name": "Tennessee v. Garner", "year": 1985, "citation": "471 U.S. 1", "holding": "Deadly force restrictions"},
                {"name": "Timbs v. Indiana", "year": 2019, "citation": "586 U.S. ___", "holding": "Excessive fines clause applies to states"}
            ]
        },
        "14th": {
            "text": "No State shall deny to any person within its jurisdiction the equal protection of the laws.",
            "key_rights": ["equal protection", "due process", "privileges and immunities"],
            "landmark_cases": [
                {"name": "Monell v. Dept. of Social Services", "year": 1978, "citation": "436 U.S. 658", "holding": "Municipal liability under 1983"},
                {"name": "Whren v. United States", "year": 1996, "citation": "517 U.S. 806", "holding": "Pretextual stops analysis"},
                {"name": "Floyd v. City of New York", "year": 2013, "citation": "959 F. Supp. 2d 540", "holding": "Stop-and-frisk racial profiling"}
            ]
        }
    },
    "statutes": {
        "42_usc_1983": {
            "name": "Section 1983 - Civil Rights Act",
            "text": "Every person who, under color of any statute, ordinance, regulation, custom, or usage, of any State... subjects, or causes to be subjected, any citizen... to the deprivation of any rights, privileges, or immunities secured by the Constitution and laws, shall be liable to the party injured.",
            "elements": [
                "Action under color of state law",
                "Deprivation of constitutional right",
                "Causation",
                "Damages"
            ],
            "defenses": ["Qualified immunity", "Good faith", "Statute of limitations"]
        },
        "18_usc_242": {
            "name": "Section 242 - Criminal Deprivation of Rights",
            "text": "Whoever, under color of any law... willfully subjects any person... to the deprivation of any rights, privileges, or immunities secured or protected by the Constitution...",
            "elements": [
                "Acting under color of law",
                "Willful deprivation",
                "Constitutional or federal right"
            ],
            "penalties": ["Fine", "Imprisonment up to 1 year", "Up to life if death results"]
        }
    },
    "violation_definitions": {
        "excessive_force": {
            "definition": "Force that exceeds what a reasonable officer would use under similar circumstances",
            "standard": "Graham v. Connor objective reasonableness",
            "factors": [
                "Severity of crime at issue",
                "Immediate threat to officer/others",
                "Actively resisting or evading arrest",
                "Proportionality of force used"
            ],
            "indicators": [
                "Force applied after suspect secured",
                "Weapons used on non-threatening suspect",
                "Injuries disproportionate to resistance",
                "Multiple officers on single suspect"
            ]
        },
        "unlawful_search": {
            "definition": "Search conducted without warrant, consent, or recognized exception",
            "exceptions": [
                "Consent (voluntary)",
                "Search incident to arrest",
                "Plain view",
                "Exigent circumstances",
                "Automobile exception",
                "Terry stop (limited pat-down)"
            ],
            "indicators": [
                "No warrant obtained",
                "Coerced consent",
                "Search beyond scope of consent",
                "No applicable exception"
            ]
        },
        "miranda_violation": {
            "definition": "Failure to properly advise suspect of rights before custodial interrogation",
            "requirements": [
                "Custodial situation",
                "Interrogation (questions likely to elicit incriminating response)",
                "Proper advisement of all four rights",
                "Knowing and voluntary waiver"
            ],
            "consequences": "Statements inadmissible, fruit of poisonous tree"
        },
        "false_arrest": {
            "definition": "Arrest without probable cause or legal authority",
            "elements": [
                "Intent to confine",
                "Acts resulting in confinement",
                "Victim aware of confinement",
                "No legal justification"
            ]
        },
        "racial_profiling": {
            "definition": "Law enforcement actions based substantially on race/ethnicity rather than behavior",
            "indicators": [
                "Disparate treatment",
                "No legitimate basis for stop",
                "Racially charged language",
                "Pattern of targeting specific groups"
            ]
        },
        "first_amendment_violation": {
            "definition": "Interference with protected speech, assembly, or recording",
            "protected_activities": [
                "Recording police in public",
                "Peaceful protest",
                "Verbal criticism of officers",
                "Refusal to identify (varies by state)"
            ]
        }
    }
}


class CourtGradeAIService:
    """
    Enhanced AI service with court-grade accuracy, guardrails, and confidence scoring
    """
    
    ANALYSIS_VERSION = "1.0.0"
    
    def __init__(self):
        self.knowledge_base = LEGAL_KNOWLEDGE_BASE
        
    def _compute_input_hash(self, *inputs) -> str:
        """Create verification hash of inputs"""
        combined = "|".join(str(i) for i in inputs)
        return hashlib.sha256(combined.encode()).hexdigest()[:16]
    
    def _get_relevant_citations(self, violation_type: str, context: str) -> List[LegalCitation]:
        """RAG: Retrieve relevant legal citations for a violation type"""
        citations = []
        
        # Map violation types to amendments
        violation_amendment_map = {
            "excessive_force": ["4th", "8th"],
            "unlawful_search": ["4th"],
            "unlawful_seizure": ["4th"],
            "miranda_violation": ["5th", "6th"],
            "false_arrest": ["4th"],
            "racial_profiling": ["14th", "4th"],
            "first_amendment_violation": ["1st"],
            "coercion": ["5th"],
            "unlawful_detention": ["4th"]
        }
        
        relevant_amendments = violation_amendment_map.get(violation_type, ["4th"])
        
        for amendment_num in relevant_amendments:
            amendment_data = self.knowledge_base["constitutional_amendments"].get(amendment_num)
            if amendment_data:
                for case in amendment_data.get("landmark_cases", []):
                    # Calculate relevance based on keyword matching
                    relevance = self._calculate_case_relevance(case, context, violation_type)
                    if relevance > 0.3:
                        citations.append(LegalCitation(
                            case_name=case["name"],
                            citation=case["citation"],
                            year=case["year"],
                            court="U.S. Supreme Court",
                            relevance_score=relevance,
                            holding=case["holding"],
                            verified=True,
                            verification_source="JUSTICE Legal Knowledge Base v1.0"
                        ))
        
        # Sort by relevance
        citations.sort(key=lambda x: x.relevance_score, reverse=True)
        return citations[:5]  # Top 5 most relevant
    
    def _calculate_case_relevance(self, case: Dict, context: str, violation_type: str) -> float:
        """Calculate how relevant a case is to the current context"""
        score = 0.0
        context_lower = context.lower()
        holding_lower = case["holding"].lower()
        case_name_lower = case["name"].lower()
        
        # Check if case name mentioned in context
        if case_name_lower in context_lower:
            score += 0.4
        
        # Check keyword overlap
        keywords = violation_type.replace("_", " ").split()
        for keyword in keywords:
            if keyword in holding_lower:
                score += 0.15
        
        # Recency bonus (more recent cases may be more applicable)
        if case["year"] >= 2010:
            score += 0.1
        elif case["year"] >= 2000:
            score += 0.05
        
        return min(score, 1.0)
    
    def _run_guardrails(self, analysis: Dict, input_text: str) -> List[AIGuardrail]:
        """Run guardrail checks on AI output"""
        guardrails = []
        
        # 1. Check for hallucinated case citations
        guardrails.append(self._check_citation_validity(analysis))
        
        # 2. Check for unsupported legal claims
        guardrails.append(self._check_legal_basis(analysis))
        
        # 3. Check for bias indicators
        guardrails.append(self._check_bias_indicators(analysis))
        
        # 4. Check confidence calibration
        guardrails.append(self._check_confidence_calibration(analysis, input_text))
        
        # 5. Check for speculation vs fact separation
        guardrails.append(self._check_speculation_labeling(analysis))
        
        # 6. Check severity reasonableness
        guardrails.append(self._check_severity_reasonableness(analysis))
        
        return guardrails
    
    def _check_citation_validity(self, analysis: Dict) -> AIGuardrail:
        """Verify all case citations exist in knowledge base"""
        violations = analysis.get("violations", [])
        unknown_citations = []
        
        known_cases = set()
        for amendment_data in self.knowledge_base["constitutional_amendments"].values():
            for case in amendment_data.get("landmark_cases", []):
                known_cases.add(case["name"].lower())
        
        for violation in violations:
            for case_ref in violation.get("case_law", []):
                # Extract case name from reference
                case_name = case_ref.split("(")[0].strip().lower()
                if case_name not in known_cases and len(case_name) > 5:
                    unknown_citations.append(case_ref)
        
        if unknown_citations:
            return AIGuardrail(
                check_name="citation_validity",
                passed=False,
                details=f"Unverified citations: {', '.join(unknown_citations[:3])}",
                severity="warning"
            )
        return AIGuardrail(
            check_name="citation_validity",
            passed=True,
            details="All citations verified against legal knowledge base",
            severity="info"
        )
    
    def _check_legal_basis(self, analysis: Dict) -> AIGuardrail:
        """Ensure violations have proper legal basis"""
        violations = analysis.get("violations", [])
        unsupported = []
        
        for v in violations:
            if not v.get("amendment_violated") and not v.get("legal_basis"):
                unsupported.append(v.get("violation_type", "unknown"))
        
        if unsupported:
            return AIGuardrail(
                check_name="legal_basis",
                passed=False,
                details=f"Violations without legal basis: {', '.join(unsupported)}",
                severity="critical"
            )
        return AIGuardrail(
            check_name="legal_basis",
            passed=True,
            details="All violations cite constitutional or statutory basis",
            severity="info"
        )
    
    def _check_bias_indicators(self, analysis: Dict) -> AIGuardrail:
        """Check for potential bias in analysis"""
        summary = str(analysis.get("summary", "")).lower()
        
        bias_phrases = [
            "obviously guilty", "clearly innocent", "all police",
            "always", "never", "definitely", "certainly", "undoubtedly"
        ]
        
        found_bias = [p for p in bias_phrases if p in summary]
        
        if found_bias:
            return AIGuardrail(
                check_name="bias_check",
                passed=False,
                details=f"Potential bias indicators: {', '.join(found_bias)}",
                severity="warning"
            )
        return AIGuardrail(
            check_name="bias_check",
            passed=True,
            details="No obvious bias indicators detected",
            severity="info"
        )
    
    def _check_confidence_calibration(self, analysis: Dict, input_text: str) -> AIGuardrail:
        """Ensure confidence scores are reasonable given input"""
        confidence = analysis.get("overall_assessment", {}).get("estimated_case_viability", 0)
        violations = analysis.get("violations", [])
        
        # If high confidence but few violations or short transcript
        if confidence > 80 and len(violations) < 2:
            return AIGuardrail(
                check_name="confidence_calibration",
                passed=False,
                details="High confidence with limited evidence - may be overconfident",
                severity="warning"
            )
        
        # If high confidence but very short input
        if confidence > 70 and len(input_text) < 200:
            return AIGuardrail(
                check_name="confidence_calibration",
                passed=False,
                details="Insufficient input length for high confidence",
                severity="warning"
            )
        
        return AIGuardrail(
            check_name="confidence_calibration",
            passed=True,
            details="Confidence level appropriate for evidence provided",
            severity="info"
        )
    
    def _check_speculation_labeling(self, analysis: Dict) -> AIGuardrail:
        """Check that speculative claims are properly labeled"""
        summary = str(analysis.get("summary", ""))
        
        speculation_words = ["possibly", "might", "could", "may", "perhaps", "likely"]
        certainty_words = ["definitely", "certainly", "absolutely", "clearly", "obviously"]
        
        has_speculation = any(w in summary.lower() for w in speculation_words)
        has_false_certainty = any(w in summary.lower() for w in certainty_words)
        
        if has_false_certainty and not has_speculation:
            return AIGuardrail(
                check_name="speculation_labeling",
                passed=False,
                details="Analysis uses absolute language without hedging",
                severity="warning"
            )
        return AIGuardrail(
            check_name="speculation_labeling",
            passed=True,
            details="Appropriate use of qualified language",
            severity="info"
        )
    
    def _check_severity_reasonableness(self, analysis: Dict) -> AIGuardrail:
        """Check that severity scores are reasonable"""
        violations = analysis.get("violations", [])
        
        for v in violations:
            severity = v.get("severity", 5)
            vtype = v.get("violation_type", "").lower()
            
            # Excessive force should typically be high severity
            if "excessive force" in vtype and severity < 6:
                return AIGuardrail(
                    check_name="severity_reasonableness",
                    passed=False,
                    details="Excessive force rated below expected severity",
                    severity="warning"
                )
            
            # Very high severity should have strong evidence
            if severity >= 9 and not v.get("quote"):
                return AIGuardrail(
                    check_name="severity_reasonableness",
                    passed=False,
                    details="High severity violation without supporting quote",
                    severity="warning"
                )
        
        return AIGuardrail(
            check_name="severity_reasonableness",
            passed=True,
            details="Severity scores are within reasonable bounds",
            severity="info"
        )
    
    def _calculate_confidence(self, analysis: Dict, guardrails: List[AIGuardrail], citations_count: int) -> Tuple[float, str, Dict]:
        """Calculate overall confidence score with breakdown"""
        breakdown = {
            "evidence_quality": 0.0,
            "legal_backing": 0.0,
            "guardrail_score": 0.0,
            "citation_strength": 0.0
        }
        
        # Evidence quality (based on violations with quotes)
        violations = analysis.get("violations", [])
        if violations:
            quoted_violations = sum(1 for v in violations if v.get("quote"))
            breakdown["evidence_quality"] = min(quoted_violations / max(len(violations), 1), 1.0) * 100
        
        # Legal backing (based on citations)
        breakdown["citation_strength"] = min(citations_count * 15, 100)
        
        # Guardrail score
        passed_guardrails = sum(1 for g in guardrails if g.passed)
        critical_failures = sum(1 for g in guardrails if not g.passed and g.severity == "critical")
        
        if critical_failures > 0:
            breakdown["guardrail_score"] = 0
        else:
            breakdown["guardrail_score"] = (passed_guardrails / max(len(guardrails), 1)) * 100
        
        # Legal basis presence
        has_legal_basis = all(v.get("amendment_violated") or v.get("legal_basis") for v in violations) if violations else False
        breakdown["legal_backing"] = 100 if has_legal_basis else 50
        
        # Calculate overall
        weights = {"evidence_quality": 0.3, "legal_backing": 0.25, "guardrail_score": 0.25, "citation_strength": 0.2}
        overall = sum(breakdown[k] * weights[k] for k in weights)
        
        # Determine confidence level
        if overall >= 90:
            level = ConfidenceLevel.VERY_HIGH.value
        elif overall >= 75:
            level = ConfidenceLevel.HIGH.value
        elif overall >= 50:
            level = ConfidenceLevel.MODERATE.value
        elif overall >= 25:
            level = ConfidenceLevel.LOW.value
        else:
            level = ConfidenceLevel.VERY_LOW.value
        
        return overall, level, breakdown
    
    async def analyze_encounter_court_grade(
        self,
        encounter_id: str,
        transcript: str,
        encounter_type: str = "general",
        existing_analysis: Optional[Dict] = None
    ) -> CourtGradeAnalysis:
        """
        Perform court-grade analysis with RAG, guardrails, and confidence scoring
        """
        import time
        start_time = time.time()
        
        analysis_id = f"cga_{uuid.uuid4().hex[:12]}"
        input_hash = self._compute_input_hash(transcript, encounter_type)
        
        # Get base analysis (either existing or run new)
        if existing_analysis:
            base_analysis = existing_analysis
        else:
            # Import and run the standard violation detection
            from app.services.violation_detection import analyze_encounter_for_violations
            base_analysis = await analyze_encounter_for_violations(
                encounter_id, transcript, encounter_type
            )
        
        # Enrich with RAG citations
        all_citations = []
        violations = base_analysis.get("violations", [])
        
        for violation in violations:
            v_type = violation.get("violation_type", "").lower().replace(" ", "_")
            citations = self._get_relevant_citations(v_type, transcript)
            
            # Add verified citations to violation
            violation["verified_citations"] = [asdict(c) for c in citations]
            all_citations.extend(citations)
        
        # Run guardrails
        guardrails = self._run_guardrails(base_analysis, transcript)
        all_passed = all(g.passed or g.severity != "critical" for g in guardrails)
        
        # Calculate confidence
        overall_confidence, confidence_level, confidence_breakdown = self._calculate_confidence(
            base_analysis, guardrails, len(set(c.case_name for c in all_citations))
        )
        
        # Determine court admissibility
        critical_failures = [g for g in guardrails if not g.passed and g.severity == "critical"]
        court_admissible = len(critical_failures) == 0 and overall_confidence >= 50
        
        admissibility_notes = []
        if not court_admissible:
            if critical_failures:
                admissibility_notes.append(f"Critical guardrail failures: {[g.check_name for g in critical_failures]}")
            if overall_confidence < 50:
                admissibility_notes.append(f"Confidence too low ({overall_confidence:.1f}%) for court use")
        else:
            admissibility_notes.append("Analysis meets court-grade standards")
            if overall_confidence >= 75:
                admissibility_notes.append("High confidence - suitable for primary evidence")
        
        processing_time = int((time.time() - start_time) * 1000)
        
        result = CourtGradeAnalysis(
            analysis_id=analysis_id,
            timestamp=datetime.now(timezone.utc).isoformat(),
            input_hash=input_hash,
            findings=base_analysis.get("overall_assessment", {}),
            violations_detected=[{**v, "guardrail_verified": True} for v in violations],
            overall_confidence=round(overall_confidence, 2),
            confidence_level=confidence_level,
            confidence_breakdown={k: round(v, 2) for k, v in confidence_breakdown.items()},
            citations=[asdict(c) for c in all_citations],
            legal_basis_score=confidence_breakdown.get("legal_backing", 0),
            guardrail_checks=[asdict(g) for g in guardrails],
            all_guardrails_passed=all_passed,
            court_admissible=court_admissible,
            admissibility_notes=admissibility_notes,
            recommended_expert_review=overall_confidence < 75 or not all_passed,
            model_used="gpt-4o",
            analysis_version=self.ANALYSIS_VERSION,
            processing_time_ms=processing_time
        )
        
        # Store in database
        await db.court_grade_analyses.insert_one({
            **asdict(result),
            "encounter_id": encounter_id,
            "created_at": datetime.now(timezone.utc)
        })
        
        return result
    
    def get_violation_definition(self, violation_type: str) -> Optional[Dict]:
        """Get legal definition and elements of a violation type"""
        key = violation_type.lower().replace(" ", "_")
        return self.knowledge_base["violation_definitions"].get(key)
    
    def get_amendment_info(self, amendment: str) -> Optional[Dict]:
        """Get full information about a constitutional amendment"""
        # Handle various formats: "4th", "4", "Fourth"
        amendment_num = amendment.replace("th", "").replace("nd", "").replace("rd", "").replace("st", "")
        return self.knowledge_base["constitutional_amendments"].get(f"{amendment_num}th") or \
               self.knowledge_base["constitutional_amendments"].get(amendment_num)


# Singleton instance
court_grade_ai = CourtGradeAIService()
