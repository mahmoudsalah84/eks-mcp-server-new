#!/usr/bin/env python3
"""
AWS Authentication utilities for EKS
"""

import base64
import boto3
import json
import os
import tempfile
from datetime import datetime

def get_eks_token(cluster_name, region):
    """
    Get a token for EKS authentication using AWS CLI
    This is more reliable than using the boto3 API directly
    """
    try:
        # Use AWS CLI to get the token
        import subprocess
        cmd = f"aws eks get-token --cluster-name {cluster_name} --region {region}"
        result = subprocess.run(cmd, shell=True, check=True, capture_output=True, text=True)
        token_data = json.loads(result.stdout)
        return token_data['status']['token']
    except Exception as e:
        print(f"Error getting EKS token via CLI: {str(e)}")
        
        # Fall back to STS method
        try:
            # Get STS client
            sts_client = boto3.client('sts', region_name=region)
            
            # Get caller identity
            response = sts_client.get_caller_identity()
            
            # Create token manually
            token = {
                "kind": "ExecCredential",
                "apiVersion": "client.authentication.k8s.io/v1beta1",
                "spec": {},
                "status": {
                    "expirationTimestamp": datetime.utcnow().strftime('%Y-%m-%dT%H:%M:%SZ'),
                    "token": f"k8s-aws-v1.{base64.urlsafe_b64encode(json.dumps({
                        'clusterName': cluster_name,
                        'roleName': response['Arn']
                    }).encode('utf-8')).decode('utf-8')}"
                }
            }
            
            return token['status']['token']
        except Exception as fallback_error:
            print(f"Error getting EKS token via STS fallback: {str(fallback_error)}")
            raise

def create_kubeconfig(cluster_name, region):
    """
    Create a kubeconfig file for the EKS cluster
    Returns the path to the kubeconfig file
    """
    try:
        # Get EKS client
        eks_client = boto3.client('eks', region_name=region)
        
        # Get cluster info
        response = eks_client.describe_cluster(name=cluster_name)
        endpoint = response['cluster']['endpoint']
        ca_data = response['cluster']['certificateAuthority']['data']
        
        # Get token
        token = get_eks_token(cluster_name, region)
        
        # Create kubeconfig
        kubeconfig = {
            "apiVersion": "v1",
            "kind": "Config",
            "clusters": [
                {
                    "cluster": {
                        "server": endpoint,
                        "certificate-authority-data": ca_data
                    },
                    "name": cluster_name
                }
            ],
            "contexts": [
                {
                    "context": {
                        "cluster": cluster_name,
                        "user": "aws"
                    },
                    "name": cluster_name
                }
            ],
            "current-context": cluster_name,
            "preferences": {},
            "users": [
                {
                    "name": "aws",
                    "user": {
                        "token": token
                    }
                }
            ]
        }
        
        # Write kubeconfig to temp file
        fd, kubeconfig_path = tempfile.mkstemp(prefix='kubeconfig-', suffix='.json')
        with os.fdopen(fd, 'w') as f:
            json.dump(kubeconfig, f)
        
        return kubeconfig_path
    except Exception as e:
        print(f"Error creating kubeconfig: {str(e)}")
        raise
