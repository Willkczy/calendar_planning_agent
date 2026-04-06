#!/usr/bin/env bash
# =============================================================================
# infrastructure/scripts/deploy.sh — AWS deployment helper
# =============================================================================
# Builds the Docker image, pushes to ECR, and deploys via CloudFormation.
#
# NOT NEEDED FOR THE FIRST THREE WEEKS — placeholder for production.
#
# USAGE:
#   ./infrastructure/scripts/deploy.sh <ecr-repo-uri> <stack-name>
#
# PREREQUISITES:
#   - AWS CLI configured with appropriate permissions
#   - Docker installed and running
#   - ECR repository already created
# =============================================================================

set -euo pipefail

ECR_REPO="${1:?Usage: deploy.sh <ecr-repo-uri> <stack-name>}"
STACK_NAME="${2:?Usage: deploy.sh <ecr-repo-uri> <stack-name>}"
REGION="${AWS_REGION:-us-east-1}"

echo "=== Step 1: Authenticate Docker to ECR ==="
# TODO: aws ecr get-login-password --region "$REGION" | docker login --username AWS --password-stdin "$ECR_REPO"

echo "=== Step 2: Build Docker image ==="
# TODO: docker build -t calendar-agent .

echo "=== Step 3: Tag and push image ==="
# TODO: docker tag calendar-agent:latest "$ECR_REPO:latest"
# TODO: docker push "$ECR_REPO:latest"

echo "=== Step 4: Deploy CloudFormation stack ==="
# TODO: aws cloudformation deploy \
#   --template-file infrastructure/cloudformation/template.yaml \
#   --stack-name "$STACK_NAME" \
#   --parameter-overrides DockerImage="$ECR_REPO:latest" \
#   --capabilities CAPABILITY_IAM \
#   --region "$REGION"

echo "=== Done ==="
