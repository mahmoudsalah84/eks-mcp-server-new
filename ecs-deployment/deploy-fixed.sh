#!/bin/bash
set -e

# Configuration
AWS_REGION="us-east-1"
AWS_ACCOUNT_ID=$(aws sts get-caller-identity --query Account --output text)
ECR_REPOSITORY="eks-mcp-server-new"
MCP_API_KEY=$(openssl rand -hex 16)
JWT_SECRET_KEY=$(openssl rand -hex 32)

echo "Using AWS Account: $AWS_ACCOUNT_ID"
echo "Using AWS Region: $AWS_REGION"
echo "Generated MCP API Key: $MCP_API_KEY"
echo "Generated JWT Secret: $JWT_SECRET_KEY"

# Create ECR repository if it doesn't exist
echo "Creating ECR repository..."
aws ecr describe-repositories --repository-names $ECR_REPOSITORY --region $AWS_REGION || \
  aws ecr create-repository --repository-name $ECR_REPOSITORY --region $AWS_REGION

# Login to ECR
echo "Logging in to ECR..."
aws ecr get-login-password --region $AWS_REGION | docker login --username AWS --password-stdin $AWS_ACCOUNT_ID.dkr.ecr.$AWS_REGION.amazonaws.com

# Build and push Docker image
echo "Building Docker image..."
cd ..
docker build -t $ECR_REPOSITORY:latest .
docker tag $ECR_REPOSITORY:latest $AWS_ACCOUNT_ID.dkr.ecr.$AWS_REGION.amazonaws.com/$ECR_REPOSITORY:latest

echo "Pushing Docker image to ECR..."
docker push $AWS_ACCOUNT_ID.dkr.ecr.$AWS_REGION.amazonaws.com/$ECR_REPOSITORY:latest

# Create IAM roles if they don't exist
echo "Creating IAM roles..."

# Check if ecsTaskExecutionRole exists, create if it doesn't
aws iam get-role --role-name ecsTaskExecutionRole > /dev/null 2>&1 || \
  aws iam create-role --role-name ecsTaskExecutionRole \
    --assume-role-policy-document '{"Version":"2012-10-17","Statement":[{"Effect":"Allow","Principal":{"Service":"ecs-tasks.amazonaws.com"},"Action":"sts:AssumeRole"}]}' && \
  aws iam attach-role-policy --role-name ecsTaskExecutionRole --policy-arn arn:aws:iam::aws:policy/service-role/AmazonECSTaskExecutionRolePolicy

# Create EKS MCP server role
aws iam get-role --role-name eks-mcp-server-role > /dev/null 2>&1 || \
  aws iam create-role --role-name eks-mcp-server-role \
    --assume-role-policy-document '{"Version":"2012-10-17","Statement":[{"Effect":"Allow","Principal":{"Service":"ecs-tasks.amazonaws.com"},"Action":"sts:AssumeRole"}]}'

# Create and attach policy for EKS MCP server role
aws iam put-role-policy --role-name eks-mcp-server-role \
  --policy-name eks-mcp-server-policy \
  --policy-document file://ecs-deployment/iam-policy.json

# Create CloudWatch log group
echo "Creating CloudWatch log group..."
aws logs create-log-group --log-group-name /ecs/eks-mcp-server-new --region $AWS_REGION || true

# Replace placeholders in task definition
echo "Preparing task definition..."
cd ecs-deployment
sed -e "s/\${AWS_ACCOUNT_ID}/$AWS_ACCOUNT_ID/g" \
    -e "s/\${AWS_REGION}/$AWS_REGION/g" \
    -e "s/\${MCP_API_KEY}/$MCP_API_KEY/g" \
    -e "s/\${JWT_SECRET_KEY}/$JWT_SECRET_KEY/g" \
    task-definition.json > task-definition-final.json

# Register task definition
echo "Registering task definition..."
TASK_DEFINITION_ARN=$(aws ecs register-task-definition \
  --cli-input-json file://task-definition-final.json \
  --region $AWS_REGION \
  --query 'taskDefinition.taskDefinitionArn' \
  --output text)

echo "Task definition registered: $TASK_DEFINITION_ARN"

# Create ECS cluster if it doesn't exist
echo "Creating ECS cluster..."
aws ecs describe-clusters --clusters eks-mcp-cluster-new --region $AWS_REGION || \
  aws ecs create-cluster --cluster-name eks-mcp-cluster-new --region $AWS_REGION

# Get VPC ID
VPC_ID=$(aws ec2 describe-vpcs --query 'Vpcs[0].VpcId' --output text)
echo "Using VPC: $VPC_ID"

# Check if security group exists
SECURITY_GROUP_ID=$(aws ec2 describe-security-groups \
  --filters "Name=group-name,Values=eks-mcp-server-new-sg" "Name=vpc-id,Values=$VPC_ID" \
  --query 'SecurityGroups[0].GroupId' \
  --output text)

if [ "$SECURITY_GROUP_ID" == "None" ] || [ -z "$SECURITY_GROUP_ID" ]; then
  echo "Creating security group..."
  SECURITY_GROUP_ID=$(aws ec2 create-security-group \
    --group-name eks-mcp-server-new-sg \
    --description "Security group for EKS MCP Server New" \
    --vpc-id $VPC_ID \
    --region $AWS_REGION \
    --query 'GroupId' \
    --output text)
  
  # Allow inbound traffic on port 8000
  aws ec2 authorize-security-group-ingress \
    --group-id $SECURITY_GROUP_ID \
    --protocol tcp \
    --port 8000 \
    --cidr 0.0.0.0/0 \
    --region $AWS_REGION
else
  echo "Using existing security group: $SECURITY_GROUP_ID"
fi

# Get subnet IDs
SUBNET_IDS=$(aws ec2 describe-subnets \
  --filters "Name=vpc-id,Values=$VPC_ID" \
  --query 'Subnets[0:2].SubnetId' \
  --output text | tr '\t' ',')

echo "Using subnets: $SUBNET_IDS"

# Check if service exists
SERVICE_EXISTS=$(aws ecs describe-services \
  --cluster eks-mcp-cluster-new \
  --services eks-mcp-service-new \
  --region $AWS_REGION \
  --query 'services[0].status' \
  --output text 2>/dev/null || echo "MISSING")

if [ "$SERVICE_EXISTS" == "MISSING" ] || [ "$SERVICE_EXISTS" == "None" ]; then
  # Create ECS service
  echo "Creating ECS service..."
  aws ecs create-service \
    --cluster eks-mcp-cluster-new \
    --service-name eks-mcp-service-new \
    --task-definition $TASK_DEFINITION_ARN \
    --desired-count 1 \
    --launch-type FARGATE \
    --platform-version LATEST \
    --network-configuration "awsvpcConfiguration={subnets=[$SUBNET_IDS],securityGroups=[$SECURITY_GROUP_ID],assignPublicIp=ENABLED}" \
    --region $AWS_REGION
else
  # Update existing service
  echo "Updating existing ECS service..."
  aws ecs update-service \
    --cluster eks-mcp-cluster-new \
    --service eks-mcp-service-new \
    --task-definition $TASK_DEFINITION_ARN \
    --force-new-deployment \
    --region $AWS_REGION
fi

# Wait for service to be stable
echo "Waiting for service to be stable..."
aws ecs wait services-stable \
  --cluster eks-mcp-cluster-new \
  --services eks-mcp-service-new \
  --region $AWS_REGION

# Get the public IP of the task
echo "Getting service details..."
TASK_ARN=$(aws ecs list-tasks \
  --cluster eks-mcp-cluster-new \
  --service-name eks-mcp-service-new \
  --region $AWS_REGION \
  --query 'taskArns[0]' \
  --output text)

ENI_ID=$(aws ecs describe-tasks \
  --cluster eks-mcp-cluster-new \
  --tasks $TASK_ARN \
  --region $AWS_REGION \
  --query 'tasks[0].attachments[0].details[?name==`networkInterfaceId`].value' \
  --output text)

PUBLIC_IP=$(aws ec2 describe-network-interfaces \
  --network-interface-ids $ENI_ID \
  --region $AWS_REGION \
  --query 'NetworkInterfaces[0].Association.PublicIp' \
  --output text)

echo "EKS MCP Server New is deployed!"
echo "Public IP: $PUBLIC_IP"
echo "API Key: $MCP_API_KEY"
echo "Endpoint: http://$PUBLIC_IP:8000"

# Save configuration for client
echo "{\"mcp_server_url\": \"http://$PUBLIC_IP:8000\", \"mcp_api_key\": \"$MCP_API_KEY\"}" > ../client_config.json
echo "Client configuration saved to client_config.json"
