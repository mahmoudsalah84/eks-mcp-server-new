#!/usr/bin/env python3
"""
Test AWS Authentication utilities for EKS
"""

import os
import requests
import json
import urllib3
from aws_auth import get_eks_token, create_kubeconfig

# Disable SSL warnings for self-signed certificates
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

# Test parameters
CLUSTER_NAME = "sample-eks-cluster"
REGION = "us-east-1"
TEST_NAMESPACE = "mcp-test-namespace"

def test_get_token():
    """Test getting an EKS token"""
    print("\n=== Testing get_eks_token ===")
    try:
        token = get_eks_token(CLUSTER_NAME, REGION)
        print(f"Token: {token[:30]}...")
        return token
    except Exception as e:
        print(f"Error getting token: {str(e)}")
        return None

def test_create_kubeconfig():
    """Test creating a kubeconfig file"""
    print("\n=== Testing create_kubeconfig ===")
    try:
        kubeconfig_path = create_kubeconfig(CLUSTER_NAME, REGION)
        print(f"Kubeconfig created at: {kubeconfig_path}")
        
        # Read the kubeconfig file
        with open(kubeconfig_path, 'r') as f:
            kubeconfig = json.load(f)
        
        print(f"Kubeconfig contains:")
        print(f"  Cluster: {kubeconfig['clusters'][0]['name']}")
        print(f"  Endpoint: {kubeconfig['clusters'][0]['cluster']['server']}")
        print(f"  CA Data: {kubeconfig['clusters'][0]['cluster']['certificate-authority-data'][:30]}...")
        print(f"  Token: {kubeconfig['users'][0]['user']['token'][:30]}...")
        
        return kubeconfig_path
    except Exception as e:
        print(f"Error creating kubeconfig: {str(e)}")
        return None

def test_kubectl_with_kubeconfig(kubeconfig_path):
    """Test kubectl with the kubeconfig file"""
    print("\n=== Testing kubectl with kubeconfig ===")
    try:
        import subprocess
        cmd = f"KUBECONFIG={kubeconfig_path} kubectl get namespaces"
        print(f"Running command: {cmd}")
        result = subprocess.run(cmd, shell=True, capture_output=True, text=True)
        
        if result.returncode == 0:
            print("kubectl command succeeded:")
            print(result.stdout)
            return True
        else:
            print("kubectl command failed:")
            print(result.stderr)
            return False
    except Exception as e:
        print(f"Error running kubectl: {str(e)}")
        return False

def main():
    """Main function"""
    print("Starting AWS Auth Test")
    
    # Test getting a token
    token = test_get_token()
    if not token:
        print("❌ Failed to get token, aborting further tests")
        return
    
    # Test creating a kubeconfig file
    kubeconfig_path = test_create_kubeconfig()
    if not kubeconfig_path:
        print("❌ Failed to create kubeconfig, aborting further tests")
        return
    
    # Test kubectl with the kubeconfig file
    success = test_kubectl_with_kubeconfig(kubeconfig_path)
    if success:
        print("✅ Successfully authenticated with kubectl")
    else:
        print("❌ Failed to authenticate with kubectl")
    
    # Clean up
    os.remove(kubeconfig_path)
    print(f"Removed temporary kubeconfig file: {kubeconfig_path}")

if __name__ == "__main__":
    main()
