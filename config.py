"""Sandstone configuration — reads from env vars with sensible defaults.

CHANGELOG v2.1:
  - Renamed TDS_* -> LDS_* (Linguistic Divergence Score)
  - Updated DEFAULT_WEIGHTS to patent v2.1 values: 0.20/0.30/0.20/0.15/0.15
  - Changed LDS_EPSILON from 0.3 to 0.15 (patent-specified)
  - Added INJECTION_THRESHOLD = 0.25 (patent-specified)
  - Added PDV_THRESHOLD = 3 (patent-specified)
  - Added PDV_BOOST_DELTA = 0.10 (patent-specified)
  - Removed DATABASE_PATH / USE_POSTGRES (always PostgreSQL)
"""

import os
from dotenv import load_dotenv

load_dotenv()

# --- AWS ---
AWS_DEFAULT_REGION = os.getenv('AWS_DEFAULT_REGION', 'us-east-1')


def get_secret(secret_name):
    """Try AWS Secrets Manager, fall back to env var."""
    try:
        import boto3
        client = boto3.client('secretsmanager', region_name=AWS_DEFAULT_REGION)
        response = client.get_secret_value(SecretId=secret_name)
        return response['SecretString']
    except Exception:
        return None


# --- API ---
ANTHROPIC_API_KEY = os.getenv('ANTHROPIC_API_KEY') or get_secret('sandstone/anthropic-api-key') or ''

# --- Database (PostgreSQL) ---
DB_HOST = os.getenv('DB_HOST', 'localhost')
DB_PORT = int(os.getenv('DB_PORT', '5432'))
DB_NAME = os.getenv('DB_NAME', 'sandstone')
DB_USER = os.getenv('DB_USER', 'sandstone_admin')
DB_PASSWORD = os.getenv('DB_PASSWORD') or get_secret('sandstone/db-password') or ''

# --- Redis ---
REDIS_HOST = os.getenv('REDIS_HOST', 'localhost')
REDIS_PORT = int(os.getenv('REDIS_PORT', '6379'))
REDIS_ENABLED = os.getenv('REDIS_ENABLED', 'false').lower() == 'true'

# --- Decay (patent v2.1 aligned) ---
DECAY_SCHEDULE_HOURS = int(os.getenv('DECAY_SCHEDULE_HOURS', '24'))
BASE_DECAY_RATE = 0.01          # lambda_base = 0.01/hr (patent: range 0.001-0.050)
PROCESSING_BOOST = 0.5          # beta = 0.50 (patent: range 0.10-1.00)
                                # lambda = lambda_base * (1 + beta * processing_event_count)
                                # lambda INCREASES with processing: processed topics decay FASTER
MIN_SALIENCE = 0.01
RESIDUAL_FLOOR_FRACTION = 0.10  # gamma = 0.10 (patent: range 0.05-0.20)
                                # kappa = gamma * base_score

# --- Scoring (patent v2.1 aligned) ---
# B = a1*SDV + a2*CSCV + a3*LCS + a4*SWV + a5*PDV
DEFAULT_WEIGHTS = [float(w) for w in os.getenv(
    'DEFAULT_WEIGHTS', '0.20,0.30,0.20,0.15,0.15').split(',')]
INGESTION_THRESHOLD = 0.25
MIN_EMOTIONAL_WORDS = 2

# --- LDS (Linguistic Divergence Score — renamed from TDS) ---
LDS_EPSILON = 0.15              # epsilon = 0.15 (patent: range 0.05-0.25)
                                # salience_correction = lds_score * epsilon (ADDITIVE)
LDS_WEIGHTS = {
    'csd': 0.35,    # Cross-Session Divergence (was NCS)
    'icd': 0.35,    # Intra-Message Consistency Detector (was ACD)
    'ccs': 0.20,    # Cross-Context Consistency Score (was CCM)
    'vsi': 0.10,    # Valence Shift Index (was SSI)
}

# --- Context Injection (patent v2.1 aligned) ---
INJECTION_THRESHOLD = float(os.getenv('INJECTION_THRESHOLD', '0.25'))  # range 0.10-0.50
PDV_THRESHOLD = int(os.getenv('PDV_THRESHOLD', '3'))                   # range 2-5
PDV_BOOST_DELTA = float(os.getenv('PDV_BOOST_DELTA', '0.10'))         # range 0.05-0.20

# --- AWS ---
ARCHIVE_BUCKET = os.getenv('ARCHIVE_BUCKET', 'sandstone-memory-archive')
ARCHIVE_THRESHOLD = float(os.getenv('ARCHIVE_THRESHOLD', '0.05'))

# --- LLM ---
CLAUDE_MODEL = os.getenv('CLAUDE_MODEL', 'claude-sonnet-4-5-20250929')
MAX_TOKENS = 1000

# --- Bedrock ---
BEDROCK_DEFAULT_MODEL = os.getenv('BEDROCK_DEFAULT_MODEL', 'us.anthropic.claude-sonnet-4-5-v1')
BEDROCK_REGION = os.getenv('BEDROCK_REGION', AWS_DEFAULT_REGION)

BEDROCK_MODELS = {
    'claude-sonnet': 'us.anthropic.claude-sonnet-4-5-v1',
    'claude-haiku': 'us.anthropic.claude-haiku-4-5-v1',
    'claude-opus': 'us.anthropic.claude-opus-4-v1',
    'llama-70b': 'us.meta.llama3-1-70b-instruct-v1:0',
    'mistral-large': 'mistral.mistral-large-2407-v1:0',
    'titan-text': 'amazon.titan-text-premier-v1:0',
}

# --- Cognito ---
COGNITO_USER_POOL_ID = os.getenv('COGNITO_USER_POOL_ID', '')
COGNITO_APP_CLIENT_ID = os.getenv('COGNITO_APP_CLIENT_ID', '')
COGNITO_REGION = os.getenv('COGNITO_REGION', AWS_DEFAULT_REGION)
JWT_SECRET_KEY = os.getenv('JWT_SECRET_KEY', 'sandstone-dev-secret-change-in-prod')

# --- CORS ---
CORS_ORIGINS = os.getenv('CORS_ORIGINS', 'http://localhost:3000,http://localhost:5173').split(',')

# --- Admin ---
ADMIN_USERNAME = os.getenv('ADMIN_USERNAME', 'Sandstone-Admin')
ADMIN_PASSWORD = os.getenv('ADMIN_PASSWORD', 'Iamgeekn!')
