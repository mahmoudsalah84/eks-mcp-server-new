#!/bin/bash

# Configuration
AWS_REGION="us-east-1"
ECR_REPOSITORY="eks-mcp-server-new"
ECS_CLUSTER="eks-mcp-cluster-new"
ECS_SERVICE="eks-mcp-service-new"
IMAGE_TAG="latest"

# Get AWS account ID
AWS_ACCOUNT_ID=$(aws sts get-caller-identity --query "Account" --output text)
ECR_REPOSITORY_URI="${AWS_ACCOUNT_ID}.dkr.ecr.${AWS_REGION}.amazonaws.com/${ECR_REPOSITORY}"

# Navigate to the project root directory
cd "$(dirname "$0")/.."

echo "Building Docker image..."
docker buildx build --platform linux/amd64 -t ${ECR_REPOSITORY}:${IMAGE_TAG} -f Dockerfile.amd64 .

echo "Logging in to Amazon ECR..."
aws ecr get-login-password --region ${AWS_REGION} | docker login --username AWS --password-stdin ${ECR_REPOSITORY_URI}

echo "Tagging image..."
docker tag ${ECR_REPOSITORY}:${IMAGE_TAG} ${ECR_REPOSITORY_URI}:${IMAGE_TAG}

echo "Pushing image to ECR..."
docker push ${ECR_REPOSITORY_URI}:${IMAGE_TAG}

echo "Updating ECS service..."
aws ecs update-service --cluster ${ECS_CLUSTER} --service ${ECS_SERVICE} --force-new-deployment --region ${AWS_REGION}

echo "Waiting for service to be stable..."
aws ecs wait services-stable --cluster ${ECS_CLUSTER} --services ${ECS_SERVICE} --region ${AWS_REGION}

# Get task details
echo "Getting service details..."
TASK_ARN=$(aws ecs list-tasks --cluster ${ECS_CLUSTER} --service-name ${ECS_SERVICE} --region ${AWS_REGION} --query "taskArns[0]" --output text)
TASK_DETAILS=$(aws ecs describe-tasks --cluster ${ECS_CLUSTER} --tasks ${TASK_ARN} --region ${AWS_REGION})
ENI_ID=$(echo $TASK_DETAILS | jq -r '.tasks[0].attachments[0].details[] | select(.name=="networkInterfaceId").value')
PUBLIC_IP=$(aws ec2 describe-network-interfaces --network-interface-ids ${ENI_ID} --region ${AWS_REGION} --query "NetworkInterfaces[0].Association.PublicIp" --output text)

echo "EKS MCP Server has been updated!"
echo "Public IP: ${PUBLIC_IP}"
echo "Endpoint: http://${PUBLIC_IP}:8000"
echo "Health check: http://${PUBLIC_IP}:8000/health"
echo "Operations discovery endpoint: http://${PUBLIC_IP}:8000/mcp/v1/operations"

# Update client_config.json with the new server URL
if [ -f "client_config.json" ]; then
    echo "Updating client_config.json with the new server URL..."
    API_KEY=$(jq -r '.mcp_api_key' client_config.json)
    NEW_SERVER_URL="http://${PUBLIC_IP}:8000"
    
    # Create a new client_config.json with the updated server URL
    echo '{
  "mcp_server_url": "'${NEW_SERVER_URL}'",
  "mcp_api_key": "'${API_KEY}'",
  "region": "us-east-1"
}' > client_config.json
    
    echo "✅ client_config.json updated with new server URL: ${NEW_SERVER_URL}"
fi
