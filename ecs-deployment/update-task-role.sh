#!/bin/bash

# Configuration
AWS_REGION="us-east-1"
ECS_CLUSTER="eks-mcp-cluster-new"
ECS_SERVICE="eks-mcp-service-new"

# Get the task definition ARN
TASK_DEF_ARN=$(aws ecs describe-services --cluster $ECS_CLUSTER --services $ECS_SERVICE --region $AWS_REGION --query "services[0].taskDefinition" --output text)
echo "Current task definition: $TASK_DEF_ARN"

# Get the task role ARN
TASK_ROLE_ARN=$(aws ecs describe-task-definition --task-definition $TASK_DEF_ARN --region $AWS_REGION --query "taskDefinition.taskRoleArn" --output text)
echo "Task role ARN: $TASK_ROLE_ARN"

# Extract the role name from the ARN
TASK_ROLE_NAME=$(echo $TASK_ROLE_ARN | awk -F'/' '{print $NF}')
echo "Task role name: $TASK_ROLE_NAME"

# Check if the role exists
if [ -z "$TASK_ROLE_NAME" ] || [ "$TASK_ROLE_NAME" == "null" ]; then
    echo "No task role found. Creating a new role..."
    
    # Create a new role
    TASK_ROLE_NAME="eks-mcp-server-task-role"
    aws iam create-role --role-name $TASK_ROLE_NAME \
        --assume-role-policy-document '{
            "Version": "2012-10-17",
            "Statement": [
                {
                    "Effect": "Allow",
                    "Principal": {
                        "Service": "ecs-tasks.amazonaws.com"
                    },
                    "Action": "sts:AssumeRole"
                }
            ]
        }' \
        --region $AWS_REGION
    
    # Attach the AmazonECR-FullAccess policy
    aws iam attach-role-policy --role-name $TASK_ROLE_NAME \
        --policy-arn arn:aws:iam::aws:policy/AmazonECR-FullAccess \
        --region $AWS_REGION
    
    echo "Created new task role: $TASK_ROLE_NAME"
fi

# Update the role with the EKS access policy
echo "Updating task role with EKS access policy..."
aws iam put-role-policy --role-name $TASK_ROLE_NAME \
    --policy-name EKSAccessPolicy \
    --policy-document file://$(dirname "$0")/eks-access-policy.json \
    --region $AWS_REGION

echo "Task role updated successfully!"

# If we created a new role, update the task definition
if [ "$TASK_ROLE_ARN" == "null" ]; then
    echo "Updating task definition with the new role..."
    
    # Get the current task definition
    aws ecs describe-task-definition --task-definition $TASK_DEF_ARN --region $AWS_REGION > task-def.json
    
    # Extract the container definitions and other required fields
    CONTAINER_DEFS=$(jq '.taskDefinition.containerDefinitions' task-def.json)
    EXECUTION_ROLE_ARN=$(jq -r '.taskDefinition.executionRoleArn' task-def.json)
    NETWORK_MODE=$(jq -r '.taskDefinition.networkMode' task-def.json)
    CPU=$(jq -r '.taskDefinition.cpu' task-def.json)
    MEMORY=$(jq -r '.taskDefinition.memory' task-def.json)
    FAMILY=$(jq -r '.taskDefinition.family' task-def.json)
    
    # Get the new task role ARN
    NEW_TASK_ROLE_ARN=$(aws iam get-role --role-name $TASK_ROLE_NAME --query "Role.Arn" --output text --region $AWS_REGION)
    
    # Create a new task definition with the task role
    cat > new-task-def.json << EOF
{
    "family": "$FAMILY",
    "executionRoleArn": "$EXECUTION_ROLE_ARN",
    "taskRoleArn": "$NEW_TASK_ROLE_ARN",
    "networkMode": "$NETWORK_MODE",
    "containerDefinitions": $CONTAINER_DEFS,
    "requiresCompatibilities": ["FARGATE"],
    "cpu": "$CPU",
    "memory": "$MEMORY"
}
EOF
    
    # Register the new task definition
    NEW_TASK_DEF_ARN=$(aws ecs register-task-definition --cli-input-json file://new-task-def.json --region $AWS_REGION --query "taskDefinition.taskDefinitionArn" --output text)
    
    echo "New task definition registered: $NEW_TASK_DEF_ARN"
    
    # Update the service to use the new task definition
    aws ecs update-service --cluster $ECS_CLUSTER --service $ECS_SERVICE --task-definition $NEW_TASK_DEF_ARN --region $AWS_REGION
    
    echo "Service updated with new task definition!"
    
    # Clean up temporary files
    rm task-def.json new-task-def.json
fi

echo "Task role update completed!"
