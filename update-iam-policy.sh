#!/bin/bash

# Script to update the IAM policy for the ECS task role
# to allow it to access the EKS cluster

# Set variables
ROLE_NAME="eks-mcp-server-role"
POLICY_NAME="eks-mcp-server-policy"

# Create the policy document
cat > policy.json << EOF
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Effect": "Allow",
      "Action": [
        "eks:DescribeCluster",
        "eks:ListClusters",
        "eks:DescribeNodegroup",
        "eks:ListNodegroups",
        "eks:ListFargateProfiles",
        "eks:DescribeFargateProfile",
        "eks:ListAddons",
        "eks:DescribeAddon",
        "eks:ListIdentityProviderConfigs",
        "eks:DescribeIdentityProviderConfig"
      ],
      "Resource": "*"
    },
    {
      "Effect": "Allow",
      "Action": [
        "sts:AssumeRole",
        "sts:GetCallerIdentity"
      ],
      "Resource": "*"
    },
    {
      "Effect": "Allow",
      "Action": [
        "logs:CreateLogStream",
        "logs:PutLogEvents"
      ],
      "Resource": "arn:aws:logs:*:*:log-group:/ecs/eks-mcp-server-new:*"
    },
    {
      "Effect": "Allow",
      "Action": [
        "eks:DescribeCluster"
      ],
      "Resource": "arn:aws:eks:us-east-1:264477013790:cluster/sample-eks-cluster"
    }
  ]
}
EOF

# Update the inline policy
echo "Updating IAM policy for role $ROLE_NAME..."
aws iam put-role-policy --role-name $ROLE_NAME --policy-name $POLICY_NAME --policy-document file://policy.json

# Verify the policy was updated
echo "Verifying IAM policy..."
aws iam get-role-policy --role-name $ROLE_NAME --policy-name $POLICY_NAME

echo "Done! The IAM policy has been updated."
