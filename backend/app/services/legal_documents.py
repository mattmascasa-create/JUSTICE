"""
AI Legal Document Generator Service
Auto-generate legal documents from encounter data
"""
import os
import uuid
from datetime import datetime, timezone
from typing import Optional, Dict, List
from enum import Enum

from app.db.database import db


class DocumentType(str, Enum):
    COMPLAINT_LETTER = "complaint_letter"
    CIVIL_RIGHTS_REPORT = "civil_rights_report"
    ATTORNEY_BRIEF = "attorney_brief"
    EVIDENCE_SUMMARY = "evidence_summary"
    WITNESS_STATEMENT = "witness_statement"


DOCUMENT_TEMPLATES = {
    DocumentType.COMPLAINT_LETTER: {
        "title": "Formal Complaint Letter",
        "description": "Official complaint to police department",
        "sections": ["header", "incident_summary", "violations", "demands", "closing"]
    },
    DocumentType.CIVIL_RIGHTS_REPORT: {
        "title": "Civil Rights Violation Report",
        "description": "Detailed incident report for legal action",
        "sections": ["incident_details", "constitutional_violations", "evidence", "witnesses", "impact_statement"]
    },
    DocumentType.ATTORNEY_BRIEF: {
        "title": "Attorney Case Brief",
        "description": "Summary for legal consultation",
        "sections": ["case_overview", "facts", "legal_issues", "evidence_summary", "recommended_actions"]
    },
    DocumentType.EVIDENCE_SUMMARY: {
        "title": "Evidence Summary",
        "description": "Comprehensive evidence list with descriptions",
        "sections": ["evidence_inventory", "timeline", "chain_of_custody"]
    },
    DocumentType.WITNESS_STATEMENT: {
        "title": "Witness Statement Template",
        "description": "Template for witness accounts",
        "sections": ["witness_info", "incident_observation", "declaration"]
    }
}


class LegalDocumentService:
    """Service for generating legal documents from encounter data"""

    def __init__(self):
        self.llm_key = os.environ.get("EMERGENT_LLM_KEY")

    def get_document_types(self) -> List[Dict]:
        """Get available document types"""
        return [
            {
                "type": doc_type.value,
                "title": info["title"],
                "description": info["description"]
            }
            for doc_type, info in DOCUMENT_TEMPLATES.items()
        ]

    async def generate_document(
        self,
        user_id: str,
        encounter_id: str,
        document_type: DocumentType,
        additional_info: Optional[Dict] = None
    ) -> Dict:
        """Generate a legal document from encounter data"""
        
        # Get encounter data
        encounter = await db.encounters.find_one(
            {"encounter_id": encounter_id, "user_id": user_id},
            {"_id": 0}
        )
        
        if not encounter:
            return {"success": False, "error": "Encounter not found"}
        
        # Get user info
        user = await db.users.find_one({"user_id": user_id}, {"_id": 0, "name": 1, "email": 1})
        
        # Get violation analysis if available
        violation_report = await db.violation_reports.find_one(
            {"encounter_id": encounter_id},
            {"_id": 0}
        )
        
        # Generate document using AI
        document_content = await self._generate_with_ai(
            document_type,
            encounter,
            user,
            violation_report,
            additional_info
        )
        
        # Store the generated document
        doc_id = f"doc_{uuid.uuid4().hex[:12]}"
        doc_record = {
            "document_id": doc_id,
            "user_id": user_id,
            "encounter_id": encounter_id,
            "document_type": document_type.value,
            "title": DOCUMENT_TEMPLATES[document_type]["title"],
            "content": document_content,
            "created_at": datetime.now(timezone.utc).isoformat(),
            "status": "generated"
        }
        
        await db.legal_documents.insert_one(doc_record)
        
        return {
            "success": True,
            "document_id": doc_id,
            "document_type": document_type.value,
            "title": DOCUMENT_TEMPLATES[document_type]["title"],
            "content": document_content
        }

    async def _generate_with_ai(
        self,
        document_type: DocumentType,
        encounter: Dict,
        user: Dict,
        violation_report: Optional[Dict],
        additional_info: Optional[Dict]
    ) -> str:
        """Generate document content using AI"""
        
        try:
            from emergentintegrations.llm.chat import LlmChat
            
            chat = LlmChat(
                api_key=self.llm_key,
                model="gpt-5.2",
                system_prompt=self._get_system_prompt(document_type)
            )
            
            # Build context
            context = self._build_context(encounter, user, violation_report, additional_info)
            
            prompt = f"""Generate a {DOCUMENT_TEMPLATES[document_type]['title']} based on the following information:

{context}

Generate a professional, formal document that could be used for legal purposes. Include all relevant details from the encounter data. Use proper legal language and formatting."""

            response = await chat.send_message(prompt)
            return response
            
        except Exception as e:
            print(f"AI generation error: {e}")
            # Fallback to template-based generation
            return self._generate_template(document_type, encounter, user, violation_report, additional_info)

    def _get_system_prompt(self, document_type: DocumentType) -> str:
        """Get system prompt for AI document generation"""
        base_prompt = """You are a legal document assistant specializing in civil rights cases. 
Generate professional, formal legal documents that are clear, comprehensive, and suitable for official use.
Use proper legal terminology and formatting. Be factual and precise."""
        
        type_prompts = {
            DocumentType.COMPLAINT_LETTER: "Focus on clearly stating the complaint, relevant facts, and requested remedies.",
            DocumentType.CIVIL_RIGHTS_REPORT: "Emphasize constitutional violations, supporting evidence, and legal precedents.",
            DocumentType.ATTORNEY_BRIEF: "Provide a concise but thorough case summary for legal review.",
            DocumentType.EVIDENCE_SUMMARY: "Create a detailed inventory of all evidence with descriptions and significance.",
            DocumentType.WITNESS_STATEMENT: "Format as a formal witness statement with clear, factual observations."
        }
        
        return f"{base_prompt}\n\n{type_prompts.get(document_type, '')}"

    def _build_context(
        self,
        encounter: Dict,
        user: Dict,
        violation_report: Optional[Dict],
        additional_info: Optional[Dict]
    ) -> str:
        """Build context string for AI"""
        context_parts = []
        
        # User info
        context_parts.append(f"Complainant: {user.get('name', 'Not provided')}")
        
        # Encounter details
        context_parts.append("\n## Incident Details")
        context_parts.append(f"Date: {encounter.get('started_at', 'Unknown')}")
        context_parts.append(f"Location: {encounter.get('address', encounter.get('location', {}).get('address', 'Unknown'))}")
        context_parts.append(f"Type: {encounter.get('encounter_type', 'Unknown')}")
        
        if encounter.get('officers'):
            officers = encounter['officers']
            context_parts.append(f"Officers involved: {', '.join([o.get('badge_number', 'Unknown') for o in officers])}")
        
        # Transcript
        if encounter.get('transcript'):
            context_parts.append("\n## Transcript")
            context_parts.append(encounter['transcript'][:3000])  # Limit length
        
        # Violations
        if violation_report and violation_report.get('violations'):
            context_parts.append("\n## Identified Violations")
            for v in violation_report['violations']:
                context_parts.append(f"- {v.get('violation_type', 'Unknown')}: {v.get('explanation', '')}")
                if v.get('case_law'):
                    context_parts.append(f"  Relevant cases: {', '.join(v['case_law'])}")
        
        # Additional info
        if additional_info:
            context_parts.append("\n## Additional Information")
            if additional_info.get('user_statement'):
                context_parts.append(f"User statement: {additional_info['user_statement']}")
            if additional_info.get('injuries'):
                context_parts.append(f"Injuries: {additional_info['injuries']}")
            if additional_info.get('witnesses'):
                context_parts.append(f"Witnesses: {additional_info['witnesses']}")
        
        return "\n".join(context_parts)

    def _generate_template(
        self,
        document_type: DocumentType,
        encounter: Dict,
        user: Dict,
        violation_report: Optional[Dict],
        additional_info: Optional[Dict]
    ) -> str:
        """Generate template-based document as fallback"""
        
        date_str = datetime.now(timezone.utc).strftime("%B %d, %Y")
        incident_date = encounter.get('started_at', 'Unknown date')
        location = encounter.get('address', encounter.get('location', {}).get('address', 'Unknown location'))
        user_name = user.get('name', '[Your Name]')
        
        if document_type == DocumentType.COMPLAINT_LETTER:
            violations_text = ""
            if violation_report and violation_report.get('violations'):
                violations_text = "\n".join([
                    f"• {v.get('violation_type', 'Unknown violation')}: {v.get('explanation', '')}"
                    for v in violation_report['violations']
                ])
            else:
                violations_text = "• Details to be specified"
            
            return f"""FORMAL COMPLAINT

Date: {date_str}

To: Chief of Police / Internal Affairs Division
[Police Department Name]
[Address]

From: {user_name}
[Contact Information]

RE: Formal Complaint Regarding Incident on {incident_date}

Dear Sir/Madam,

I am writing to file a formal complaint regarding an incident that occurred on {incident_date} at {location}.

INCIDENT SUMMARY:
{encounter.get('transcript', 'Detailed incident description to be provided')[:500]}

VIOLATIONS IDENTIFIED:
{violations_text}

REQUESTED ACTION:
1. A full investigation into this incident
2. Appropriate disciplinary action against the officer(s) involved
3. Written response regarding the outcome of this investigation

I have documentation and evidence to support this complaint, including audio/video recordings and witness information.

Please contact me to discuss this matter further.

Sincerely,

{user_name}

---
Generated by JUSTICE Platform
This document was auto-generated and should be reviewed before submission.
"""

        elif document_type == DocumentType.ATTORNEY_BRIEF:
            violations_list = ""
            if violation_report and violation_report.get('violations'):
                violations_list = "\n".join([
                    f"  - {v.get('violation_type')}: Severity {v.get('severity', 'N/A')}/10"
                    for v in violation_report['violations']
                ])
            
            return f"""ATTORNEY CASE BRIEF

Case: Civil Rights Violation - {encounter.get('encounter_type', 'Police Encounter')}
Date Prepared: {date_str}
Client: {user_name}

1. CASE OVERVIEW
   Incident Date: {incident_date}
   Location: {location}
   Encounter Type: {encounter.get('encounter_type', 'Unknown')}

2. FACTS OF THE CASE
{encounter.get('transcript', 'Transcript to be provided')[:1000]}

3. LEGAL ISSUES
{violations_list if violations_list else '   To be analyzed'}

4. EVIDENCE AVAILABLE
   - Audio/Video Recording: {'Yes' if encounter.get('media_files') else 'To be confirmed'}
   - Transcript: {'Yes' if encounter.get('transcript') else 'No'}
   - Witness Information: {additional_info.get('witnesses', 'To be gathered') if additional_info else 'To be gathered'}

5. RECOMMENDED ACTIONS
   - Review all available evidence
   - Obtain police report and body camera footage via FOIA
   - Interview witnesses
   - Assess viability of civil rights claim under 42 U.S.C. § 1983

---
Generated by JUSTICE Platform
This brief is for preliminary review only.
"""

        else:
            # Generic template for other types
            return f"""LEGAL DOCUMENT

Type: {DOCUMENT_TEMPLATES[document_type]['title']}
Date: {date_str}
Reference: Incident on {incident_date}

INCIDENT INFORMATION:
Location: {location}
Type: {encounter.get('encounter_type', 'Unknown')}

DETAILS:
{encounter.get('transcript', 'Details to be provided')[:1500]}

---
Generated by JUSTICE Platform
"""

    async def get_user_documents(self, user_id: str) -> List[Dict]:
        """Get all documents for a user"""
        docs = await db.legal_documents.find(
            {"user_id": user_id},
            {"_id": 0}
        ).sort("created_at", -1).to_list(100)
        return docs

    async def get_document(self, document_id: str, user_id: str) -> Optional[Dict]:
        """Get a specific document"""
        doc = await db.legal_documents.find_one(
            {"document_id": document_id, "user_id": user_id},
            {"_id": 0}
        )
        return doc

    async def delete_document(self, document_id: str, user_id: str) -> bool:
        """Delete a document"""
        result = await db.legal_documents.delete_one(
            {"document_id": document_id, "user_id": user_id}
        )
        return result.deleted_count > 0


# Global service instance
legal_document_service = LegalDocumentService()
