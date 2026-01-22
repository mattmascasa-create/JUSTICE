"""
Database connection and initialization
"""
from motor.motor_asyncio import AsyncIOMotorClient
from app.core.config import MONGO_URL, DB_NAME

# MongoDB connection
client = AsyncIOMotorClient(MONGO_URL)
db = client[DB_NAME]

# Collections (for easy access)
users = db.users
cases = db.cases
evidence = db.evidence
messages = db.messages
attorneys = db.attorneys
sos_alerts = db.sos_alerts
ai_conversations = db.ai_conversations
departments = db.departments
incidents = db.incidents
encounters = db.encounters
transcriptions = db.transcriptions
encounter_marks = db.encounter_marks
community_evidence = db.community_evidence
blockchain_evidence = db.blockchain_evidence
policy_reports = db.policy_reports
document_analyses = db.document_analyses
emergency_contacts = db.emergency_contacts
push_subscriptions = db.push_subscriptions
