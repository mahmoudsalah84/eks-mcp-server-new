#!/bin/bash

# Script to update the aws-auth ConfigMap in an EKS cluster
# to allow the ECS task role to access the cluster

# Set variables
CLUSTER_NAME="sample-eks-cluster"
REGION="us-east-1"
ECS_TASK_ROLE_ARN="arn:aws:iam::264477013790:role/eks-mcp-server-role"

# Update kubeconfig to connect to the EKS cluster
echo "Updating kubeconfig for cluster $CLUSTER_NAME..."
aws eks update-kubeconfig --name $CLUSTER_NAME --region $REGION

# Get the current aws-auth ConfigMap
echo "Getting current aws-auth ConfigMap..."
kubectl get configmap aws-auth -n kube-system -o yaml > aws-auth-current.yaml

# Create a new aws-auth ConfigMap with the ECS task role added
cat > aws-auth-new.yaml << EOF
apiVersion: v1
kind: ConfigMap
metadata:
  name: aws-auth
  namespace: kube-system
data:
  mapRoles: |
    - rolearn: ${ECS_TASK_ROLE_ARN}
      username: system:node:{{EC2PrivateDNSName}}
      groups:
        - system:bootstrappers
        - system:nodes
        - system:masters
EOF

# Apply the new ConfigMap
echo "Applying updated aws-auth ConfigMap..."
kubectl apply -f aws-auth-new.yaml

# Verify the ConfigMap was updated
echo "Verifying aws-auth ConfigMap..."
kubectl get configmap aws-auth -n kube-system -o yaml

echo "Done! The ECS task role should now have access to the EKS cluster."
