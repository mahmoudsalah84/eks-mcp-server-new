#!/usr/bin/env python3
"""
Update the EKS MCP Server to use kubectl with proper authentication
"""

import os
import shutil
import subprocess
import sys
import datetime

def backup_file(file_path):
    """Backup a file with timestamp"""
    timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
    backup_path = f"{file_path}.{timestamp}.bak"
    print(f"Backing up {file_path} to {backup_path}")
    shutil.copy2(file_path, backup_path)

def update_server():
    """Update the server to use kubectl with proper authentication"""
    # Define paths
    base_dir = os.path.dirname(os.path.abspath(__file__))
    main_py = os.path.join(base_dir, "main.py")
    
    # Check if files exist
    if not os.path.exists(main_py):
        print(f"Error: {main_py} not found")
        sys.exit(1)
    
    # Backup files
    backup_file(main_py)
    
    # Update main.py to use the new implementation
    print("Updating main.py to use kubectl with proper authentication")
    with open(main_py, "r") as f:
        content = f.read()
    
    # Add import for the new implementation
    if "from k8s_operations_kubectl import KubernetesOperationsKubectl" not in content:
        content = content.replace(
            "from k8s_operations_sdk import KubernetesOperationsSDK",
            "from k8s_operations_sdk import KubernetesOperationsSDK\n# Import the KubernetesOperationsKubectl class\nfrom k8s_operations_kubectl import KubernetesOperationsKubectl"
        )
    
    # Initialize the new implementation
    if "k8s_kubectl_ops = KubernetesOperationsKubectl()" not in content:
        content = content.replace(
            "# Initialize KubernetesOperationsSDK\nk8s_sdk_ops = KubernetesOperationsSDK()",
            "# Initialize KubernetesOperationsSDK\nk8s_sdk_ops = KubernetesOperationsSDK()\n# Initialize KubernetesOperationsKubectl\nk8s_kubectl_ops = KubernetesOperationsKubectl()"
        )
    
    # Update the handler functions to use the new implementation
    handlers = [
        "handle_list_namespaces",
        "handle_list_pods",
        "handle_describe_pod",
        "handle_get_deployments",
        "handle_describe_deployment",
        "handle_get_services",
        "handle_get_pod_logs"
    ]
    
    for handler in handlers:
        if handler in content:
            # Find the try block in the handler function
            start_idx = content.find(f"def {handler}(")
            if start_idx == -1:
                continue
                
            try_idx = content.find("try:", start_idx)
            if try_idx == -1:
                continue
                
            # Find the line with k8s_sdk_ops
            sdk_idx = content.find("k8s_sdk_ops", try_idx)
            if sdk_idx == -1:
                continue
                
            # Find the line end
            line_end_idx = content.find("\n", sdk_idx)
            if line_end_idx == -1:
                continue
                
            # Get the line
            line = content[sdk_idx:line_end_idx]
            
            # Replace with the new implementation
            new_line = line.replace("k8s_sdk_ops", "k8s_kubectl_ops")
            
            # Update the content
            content = content[:sdk_idx] + new_line + content[line_end_idx:]
    
    # Write the updated content
    with open(main_py, "w") as f:
        f.write(content)
    
    # Create IAM policy file for EKS access
    iam_policy_file = os.path.join(base_dir, "ecs-deployment", "eks-access-policy.json")
    os.makedirs(os.path.dirname(iam_policy_file), exist_ok=True)
    
    with open(iam_policy_file, "w") as f:
        f.write("""
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
""")
    
    # Create instructions for updating aws-auth ConfigMap
    aws_auth_instructions = os.path.join(base_dir, "ecs-deployment", "update-aws-auth.md")
    with open(aws_auth_instructions, "w") as f:
        f.write("""# Updating the aws-auth ConfigMap

To allow the ECS task to access the EKS cluster, you need to add the ECS task role to the aws-auth ConfigMap in the EKS cluster.

## 1. Get the ECS task role ARN

```bash
TASK_ROLE_ARN=$(aws ecs describe-task-definition --task-definition eks-mcp-server-new:4 --query "taskDefinition.taskRoleArn" --output text)
echo $TASK_ROLE_ARN
```

## 2. Edit the aws-auth ConfigMap

```bash
kubectl edit configmap aws-auth -n kube-system
```

Add the following entry to the `mapRoles` section:

```yaml
- rolearn: <TASK_ROLE_ARN>
  username: eks-mcp-server
  groups:
    - system:masters
```

Replace `<TASK_ROLE_ARN>` with the actual task role ARN.

## 3. Verify the update

```bash
kubectl describe configmap aws-auth -n kube-system
```

## 4. Test the access

```bash
aws eks update-kubeconfig --name sample-eks-cluster --region us-east-1
kubectl get namespaces
```
""")
    
    print(f"Created IAM policy file: {iam_policy_file}")
    print(f"Created aws-auth instructions: {aws_auth_instructions}")
    print("Server updated successfully")
    print("\nIMPORTANT: You need to update the aws-auth ConfigMap in your EKS cluster.")
    print(f"See the instructions in {aws_auth_instructions}")

if __name__ == "__main__":
    update_server()
