#!/usr/bin/env bash
# Run this once after `docker compose up -d`, to create the S3 bucket and
# DynamoDB table inside LocalStack (they don't exist until you create them,
# same as real AWS).
#
# Requires the AWS CLI (just for talking to LocalStack's emulated API --
# no real AWS account or credentials needed; the values below are dummy
# placeholders LocalStack accepts for any request).

export AWS_ACCESS_KEY_ID=test
export AWS_SECRET_ACCESS_KEY=test
export AWS_DEFAULT_REGION=us-east-1
ENDPOINT="http://localhost:4566"

echo "Creating S3 bucket..."
aws --endpoint-url=$ENDPOINT s3 mb s3://billwise-bills

echo "Creating DynamoDB table..."
aws --endpoint-url=$ENDPOINT dynamodb create-table \
  --table-name billwise-sessions \
  --attribute-definitions AttributeName=user_id,AttributeType=S \
  --key-schema AttributeName=user_id,KeyType=HASH \
  --billing-mode PAY_PER_REQUEST

echo "Done. Verify with:"
echo "  aws --endpoint-url=$ENDPOINT s3 ls"
echo "  aws --endpoint-url=$ENDPOINT dynamodb list-tables"