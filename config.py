"""Sandstone configuration — reads from env vars with sensible defaults."""

import os
from dotenv import load_dotenv

load_dotenv()

# --- AWS (must be defined before get_secret) ---
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

# --- Database ---
DATABASE_PATH = os.getenv('DATABASE_PATH', 'db/sandstone.db')
DB_HOST = os.getenv('DB_HOST', 'localhost')
DB_PORT = int(os.getenv('DB_PORT', '5432'))
DB_NAME = os.getenv('DB_NAME', 'sandstone')
DB_USER = os.getenv('DB_USER', 'sandstone_admin')
DB_PASSWORD = os.getenv('DB_PASSWORD') or get_secret('sandstone/db-password') or ''
USE_POSTGRES = os.getenv('USE_POSTGRES', 'false').lower() == 'true'

# --- Redis ---
REDIS_HOST = os.getenv('REDIS_HOST', 'localhost')
REDIS_PORT = int(os.getenv('REDIS_PORT', '6379'))
REDIS_ENABLED = os.getenv('REDIS_ENABLED', 'false').lower() == 'true'

# --- Decay ---
DECAY_SCHEDULE_HOURS = int(os.getenv('DECAY_SCHEDULE_HOURS', '24'))
BASE_DECAY_RATE = 0.01
PROCESSING_BOOST = 0.5  # CRITICAL: must be 0.5 for validation study
MIN_SALIENCE = 0.01

# --- Scoring ---
DEFAULT_WEIGHTS = [float(w) for w in os.getenv('DEFAULT_WEIGHTS', '0.2,0.2,0.2,0.2,0.2').split(',')]
INGESTION_THRESHOLD = 0.25  # Bug fix #6: raised from 0.15
MIN_EMOTIONAL_WORDS = 2     # Bug fix #6: require minimum

# --- TDS ---
TDS_DELTA = 0.3
TDS_WEIGHTS = {'ncs': 0.35, 'acd': 0.35, 'ccm': 0.20, 'ssi': 0.10}

# --- AWS ---
ARCHIVE_BUCKET = os.getenv('ARCHIVE_BUCKET', 'sandstone-memory-archive')
ARCHIVE_THRESHOLD = float(os.getenv('ARCHIVE_THRESHOLD', '0.05'))

# --- LLM ---
CLAUDE_MODEL = os.getenv('CLAUDE_MODEL', 'claude-sonnet-4-5-20250929')
MAX_TOKENS = 1000

# --- Bedrock (replaces direct Anthropic API) ---
BEDROCK_DEFAULT_MODEL = os.getenv('BEDROCK_DEFAULT_MODEL', 'us.anthropic.claude-sonnet-4-5-v1')
BEDROCK_REGION = os.getenv('BEDROCK_REGION', AWS_DEFAULT_REGION)

# Supported models for dropdown
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
