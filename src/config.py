"""
Same shape as the AWS-cloud version's config.py, but every boto3 client/
resource gets an extra `endpoint_url` pointing at LocalStack (running in
Docker on your own machine) instead of real AWS. Dummy credentials are fine
here -- LocalStack doesn't check them, it just needs *something* present.
"""
import os

from dotenv import load_dotenv

load_dotenv()

SESSIONS_TABLE = os.environ.get("SESSIONS_TABLE", "billwise-sessions")
BILLS_BUCKET = os.environ.get("BILLS_BUCKET", "billwise-bills")
LOCALSTACK_ENDPOINT = os.environ.get("AWS_ENDPOINT_URL", "http://localhost:4566")
AWS_REGION = os.environ.get("AWS_DEFAULT_REGION", "us-east-1")

ANTHROPIC_API_KEY = os.environ["ANTHROPIC_API_KEY"]


def boto3_kwargs() -> dict:
    """Common kwargs every boto3 client/resource in this project should use."""
    return {"endpoint_url": LOCALSTACK_ENDPOINT, "region_name": AWS_REGION}