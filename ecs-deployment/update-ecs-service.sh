#!/bin/bash

# Configuration
AWS_REGION="us-east-1"
ECR_REPOSITORY="eks-mcp-server"
ECS_CLUSTER="eks-mcp-cluster"
ECS_SERVICE="eks-mcp-service"
IMAGE_TAG="latest"

# Get AWS account ID
AWS_ACCOUNT_ID=$(aws sts get-caller-identity --query "Account" --output text)
ECR_REPOSITORY_URI="${AWS_ACCOUNT_ID}.dkr.ecr.${AWS_REGION}.amazonaws.com/${ECR_REPOSITORY}"

# Navigate to the project root directory
cd "$(dirname "$0")/.."

echo "Building Docker image..."
docker build -t ${ECR_REPOSITORY}:${IMAGE_TAG} .

echo "Logging in to Amazon ECR..."
aws ecr get-login-password --region ${AWS_REGION} | docker login --username AWS --password-stdin ${ECR_REPOSITORY_URI}

# Create repository if it doesn't exist
aws ecr describe-repositories --repository-names ${ECR_REPOSITORY} --region ${AWS_REGION} || \
    aws ecr create-repository --repository-name ${ECR_REPOSITORY} --region ${AWS_REGION}

echo "Tagging image..."
docker tag ${ECR_REPOSITORY}:${IMAGE_TAG} ${ECR_REPOSITORY_URI}:${IMAGE_TAG}

echo "Pushing image to ECR..."
docker push ${ECR_REPOSITORY_URI}:${IMAGE_TAG}

echo "Updating ECS service..."
aws ecs update-service --cluster ${ECS_CLUSTER} --service ${ECS_SERVICE} --force-new-deployment --region ${AWS_REGION}

echo "Deployment initiated. You can check the status with:"
echo "aws ecs describe-services --cluster ${ECS_CLUSTER} --services ${ECS_SERVICE} --region ${AWS_REGION}"
