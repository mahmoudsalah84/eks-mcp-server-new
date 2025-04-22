# ECS Deployment for EKS MCP Server

This directory contains scripts and configuration files for deploying the EKS MCP Server to Amazon ECS.

## Prerequisites

1. AWS CLI installed and configured with appropriate permissions
2. Docker installed locally
3. An existing EKS cluster that you want the MCP server to interact with
4. An ECR repository for the container image
5. ECS cluster created

## IAM Role Setup

The ECS task needs an IAM role with permissions to:
1. Access the EKS API
2. Use kubectl to interact with the EKS cluster

Create the task role:

```bash
# Create the task role
aws iam create-role --role-name eks-mcp-server-task-role --assume-role-policy-document file://trust-policy.json

# Attach the policy
aws iam put-role-policy --role-name eks-mcp-server-task-role --policy-name eks-mcp-server-policy --policy-document file://eks-access-policy.json
```

## EKS Authentication Setup

For the ECS task to authenticate with the EKS cluster, you need to add the task role to the EKS cluster's auth config map:

```bash
kubectl edit configmap aws-auth -n kube-system
```

Add the following entry to the `mapRoles` section:

```yaml
- groups:
  - system:masters
  rolearn: arn:aws:iam::<AWS_ACCOUNT_ID>:role/eks-mcp-server-task-role
  username: eks-mcp-server
```

You can also use the provided script to get the task role ARN:

```bash
# Get the task role ARN
TASK_ROLE_ARN=$(aws ecs describe-task-definition --task-definition eks-mcp-server-new:4 --query "taskDefinition.taskRoleArn" --output text)
echo $TASK_ROLE_ARN
```

## Deployment Scripts

This directory includes several scripts for deploying and updating the EKS MCP Server:

1. `deploy.sh`: Initial deployment script
2. `update-service.sh`: Update an existing ECS service with a new container image
3. `update-task-role.sh`: Update the IAM role for the ECS task
4. `update-aws-auth.md`: Instructions for updating the aws-auth ConfigMap

## Deployment Steps

1. Build and push the Docker image to ECR:

```bash
./update-service.sh
```

This script will:
- Build the Docker image
- Log in to Amazon ECR
- Tag and push the image
- Update the ECS service with the new image

2. Update the task role permissions:

```bash
./update-task-role.sh
```

This script will:
- Get the current task definition
- Get the task role ARN
- Update the role with the necessary permissions

3. Update the aws-auth ConfigMap in the EKS cluster:

Follow the instructions in `update-aws-auth.md` to add the task role to the aws-auth ConfigMap.

## Verifying the Deployment

1. Check if the service is running:

```bash
aws ecs describe-services --cluster eks-mcp-cluster-new --services eks-mcp-service-new
```

2. Get the public IP:

```bash
# Get the task ARN
TASK_ARN=$(aws ecs list-tasks --cluster eks-mcp-cluster-new --service-name eks-mcp-service-new --query 'taskArns[0]' --output text)

# Get the network interface ID
NETWORK_INTERFACE_ID=$(aws ecs describe-tasks --cluster eks-mcp-cluster-new --tasks $TASK_ARN --query 'tasks[0].attachments[0].details[?name==`networkInterfaceId`].value' --output text)

# Get the public IP
PUBLIC_IP=$(aws ec2 describe-network-interfaces --network-interface-ids $NETWORK_INTERFACE_ID --query 'NetworkInterfaces[0].Association.PublicIp' --output text)

echo "Public IP: $PUBLIC_IP"
```

3. Test the API:

```bash
# Test the health endpoint
curl -X GET http://$PUBLIC_IP:8000/health

# Test the operations endpoint
curl -X GET http://$PUBLIC_IP:8000/mcp/v1/operations -H "X-API-Key: YOUR_API_KEY_HERE"
```

## Current Deployment

The server is currently deployed to ECS and accessible at:
- Endpoint: http://3.90.45.69:8000
- Health check: http://3.90.45.69:8000/health
- Operations discovery: http://3.90.45.69:8000/mcp/v1/operations

## Troubleshooting

If you encounter issues with the deployment:

1. Check the ECS task logs:

```bash
# Get the task ARN
TASK_ARN=$(aws ecs list-tasks --cluster eks-mcp-cluster-new --service-name eks-mcp-service-new --query 'taskArns[0]' --output text)

# Get the logs
aws logs get-log-events --log-group-name /ecs/eks-mcp-server-new --log-stream-name ecs/eks-mcp-server-new/$(echo $TASK_ARN | cut -d '/' -f 3)
```

2. Verify the IAM role permissions:

```bash
aws iam get-role-policy --role-name eks-mcp-server-role --policy-name EKSAccessPolicy
```

3. Verify the aws-auth ConfigMap:

```bash
kubectl describe configmap aws-auth -n kube-system
```

4. Test the authentication from the ECS task:

```bash
# Execute a command in the running task
aws ecs execute-command --cluster eks-mcp-cluster-new --task $TASK_ARN --container eks-mcp-server-new --command "/bin/bash" --interactive

# Inside the container, test the authentication
aws eks get-token --cluster-name sample-eks-cluster --region us-east-1
kubectl get namespaces
```

## IAM Policy

The ECS task role needs the following permissions:

```json
{
    "Version": "2012-10-17",
    "Statement": [
        {
            "Effect": "Allow",
            "Action": [
                "eks:DescribeCluster",
                "eks:ListClusters",
                "eks:ListNodegroups",
                "eks:DescribeNodegroup",
                "eks:ListFargateProfiles",
                "eks:DescribeFargateProfile",
                "eks:ListAddons",
                "eks:DescribeAddon"
            ],
            "Resource": "*"
        },
        {
            "Effect": "Allow",
            "Action": [
                "sts:GetCallerIdentity",
                "sts:AssumeRole"
            ],
            "Resource": "*"
        }
    ]
}
```
