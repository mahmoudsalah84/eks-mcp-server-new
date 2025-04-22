#!/usr/bin/env python3
"""
Debug script for EKS MCP Server SDK operations
"""

import boto3
import requests
import json
import urllib3
import sys
import base64
import os
from botocore.signers import RequestSigner

# Disable SSL warnings for self-signed certificates
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

# Test parameters
CLUSTER_NAME = "sample-eks-cluster"
REGION = "us-east-1"
TEST_NAMESPACE = "mcp-test-namespace"

def get_cluster_info():
    """Get cluster information including endpoint and CA data"""
    try:
        eks_client = boto3.client('eks', region_name=REGION)
        response = eks_client.describe_cluster(name=CLUSTER_NAME)
        
        print("Cluster Info:")
        print(f"  Endpoint: {response['cluster']['endpoint']}")
        print(f"  CA Data: {response['cluster']['certificateAuthority']['data'][:30]}...")
        
        return {
            'endpoint': response['cluster']['endpoint'],
            'ca_data': response['cluster']['certificateAuthority']['data']
        }
    except Exception as e:
        print(f"Error getting cluster info: {str(e)}")
        sys.exit(1)

def get_token():
    """Get a token for EKS authentication using STS"""
    try:
        # Create a STS client
        sts_client = boto3.client('sts', region_name=REGION)
        
        # Get caller identity to verify permissions
        identity = sts_client.get_caller_identity()
        print(f"Current identity: {identity['Arn']}")
        
        # Create a request signer
        service = 'sts'
        signer = RequestSigner(
            service,
            REGION,
            'sts',
            'v4',
            sts_client._request_signer._credentials,
            sts_client._request_signer._region_name
        )
        
        # Generate the URL
        url = f"https://sts.{REGION}.amazonaws.com/?Action=GetCallerIdentity&Version=2011-06-15"
        
        # Sign the request
        headers = {'x-k8s-aws-id': CLUSTER_NAME}
        signed_url = signer.generate_presigned_url(
            {'method': 'GET', 'url': url, 'body': {}, 'headers': headers, 'context': {}}
        )
        
        # Create the token
        token = f"k8s-aws-v1.{base64.urlsafe_b64encode(signed_url.encode('utf-8')).decode('utf-8')}"
        
        print("Token Info:")
        print(f"  Token: {token[:30]}...")
        
        return token
    except Exception as e:
        print(f"Error getting token: {str(e)}")
        sys.exit(1)

def test_direct_api_call():
    """Test direct API call to Kubernetes API"""
    try:
        # Get cluster info
        cluster_info = get_cluster_info()
        endpoint = cluster_info['endpoint']
        ca_data = cluster_info['ca_data']
        
        # Get token
        token = get_token()
        
        # Build URL for namespaces
        url = f"{endpoint}/api/v1/namespaces"
        
        # Set headers
        headers = {
            'Authorization': f'Bearer {token}',
            'Accept': 'application/json'
        }
        
        print(f"\nMaking direct API request to: {url}")
        print(f"Headers: {json.dumps(headers, indent=2)}")
        
        # Create a temporary CA file
        ca_file = "/tmp/eks-ca.crt"
        with open(ca_file, "w") as f:
            f.write(base64.b64decode(ca_data).decode('utf-8'))
        
        print(f"Created temporary CA file: {ca_file}")
        
        # Make request
        response = requests.get(url, headers=headers, verify=ca_file)
        
        print(f"Response Status Code: {response.status_code}")
        
        if response.status_code == 200:
            data = response.json()
            namespaces = [item.get("metadata", {}).get("name") for item in data.get("items", [])]
            print(f"Found namespaces: {namespaces}")
            
            if TEST_NAMESPACE in namespaces:
                print(f"✅ Test namespace '{TEST_NAMESPACE}' found!")
            else:
                print(f"❌ Test namespace '{TEST_NAMESPACE}' not found.")
        else:
            print(f"Error response: {response.text}")
            
        # Clean up
        os.remove(ca_file)
    except Exception as e:
        print(f"Error making direct API call: {str(e)}")

def main():
    """Main function"""
    print("Starting EKS MCP Server SDK debug")
    
    # Test direct API call
    test_direct_api_call()

if __name__ == "__main__":
    main()
