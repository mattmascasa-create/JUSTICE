"""
Core configuration for JUSTICE application
"""
import os
from pathlib import Path
from dotenv import load_dotenv

# Load environment variables
ROOT_DIR = Path(__file__).parent.parent.parent
load_dotenv(ROOT_DIR / '.env')

# API Keys
EMERGENT_LLM_KEY = os.environ.get('EMERGENT_LLM_KEY')
PINATA_JWT = os.environ.get('PINATA_JWT')
AWS_ACCESS_KEY_ID = os.environ.get('AWS_ACCESS_KEY_ID')
AWS_SECRET_ACCESS_KEY = os.environ.get('AWS_SECRET_ACCESS_KEY')
S3_BUCKET_NAME = os.environ.get('S3_BUCKET_NAME')

# Twilio SMS
TWILIO_ACCOUNT_SID = os.environ.get('TWILIO_ACCOUNT_SID')
TWILIO_AUTH_TOKEN = os.environ.get('TWILIO_AUTH_TOKEN')
TWILIO_PHONE_NUMBER = os.environ.get('TWILIO_PHONE_NUMBER')
TWILIO_ENABLED = bool(TWILIO_ACCOUNT_SID and TWILIO_AUTH_TOKEN and TWILIO_PHONE_NUMBER)

# SendGrid Email
SENDGRID_API_KEY = os.environ.get('SENDGRID_API_KEY')
SENDGRID_SENDER_EMAIL = os.environ.get('SENDGRID_SENDER_EMAIL')
SENDGRID_ENABLED = bool(SENDGRID_API_KEY)

# Frontend URL (for share links in SMS/email)
FRONTEND_URL = os.environ.get('FRONTEND_URL', 'https://police-watch-2.preview.emergentagent.com')

# JWT Settings
JWT_SECRET = os.environ.get('JWT_SECRET', 'your-super-secret-key-change-in-production')
JWT_ALGORITHM = "HS256"
JWT_EXPIRATION_HOURS = 24

# MongoDB Settings
MONGO_URL = os.environ.get('MONGO_URL', 'mongodb://localhost:27017')
DB_NAME = os.environ.get('DB_NAME', 'justice_db')

# File Storage
ENCOUNTERS_DIR = ROOT_DIR / "encounters"
ENCOUNTERS_DIR.mkdir(exist_ok=True)

UPLOADS_DIR = ROOT_DIR / "uploads"
UPLOADS_DIR.mkdir(exist_ok=True)

# Google OAuth (if configured)
GOOGLE_CLIENT_ID = os.environ.get('GOOGLE_CLIENT_ID')
GOOGLE_CLIENT_SECRET = os.environ.get('GOOGLE_CLIENT_SECRET')
EMERGENT_AUTH_URL = os.environ.get('EMERGENT_AUTH_URL')
GOOGLE_OAUTH_ENABLED = bool(EMERGENT_AUTH_URL)

# Feature flags
IPFS_ENABLED = bool(PINATA_JWT)
S3_ENABLED = bool(AWS_ACCESS_KEY_ID and AWS_SECRET_ACCESS_KEY and S3_BUCKET_NAME)
