#!/usr/bin/env python3
"""
Debug script to test EKS authentication
"""

import boto3
import json
import os
import subprocess
import tempfile
import base64
import time

def create_kubeconfig_with_token(cluster_name, region):
    """Create a kubeconfig file with a token for EKS authentication"""
    try:
        # Get cluster info
        eks_client = boto3.client('eks', region_name=region)
        cluster_info = eks_client.describe_cluster(name=cluster_name)
        cluster_endpoint = cluster_info['cluster']['endpoint']
        cluster_cert = cluster_info['cluster']['certificateAuthority']['data']
        
        # Create a temporary directory for kubeconfig
        temp_dir = tempfile.mkdtemp(prefix='kube-')
        kubeconfig_path = os.path.join(temp_dir, 'config')
        
        # Create kubeconfig content with aws-cli token generator
        kubeconfig = {
            'apiVersion': 'v1',
            'kind': 'Config',
            'clusters': [{
                'name': cluster_name,
                'cluster': {
                    'server': cluster_endpoint,
                    'certificate-authority-data': cluster_cert
                }
            }],
            'users': [{
                'name': f'eks-user-{cluster_name}',
                'user': {
                    'exec': {
                        'apiVersion': 'client.authentication.k8s.io/v1beta1',
                        'command': 'aws',
                        'args': [
                            'eks',
                            'get-token',
                            '--cluster-name',
                            cluster_name,
                            '--region',
                            region
                        ],
                        'interactiveMode': 'Never'
                    }
                }
            }],
            'contexts': [{
                'name': f'eks-{cluster_name}',
                'context': {
                    'cluster': cluster_name,
                    'user': f'eks-user-{cluster_name}'
                }
            }],
            'current-context': f'eks-{cluster_name}'
        }
        
        # Write to temporary file
        with open(kubeconfig_path, 'w') as f:
            json.dump(kubeconfig, f)
        
        print(f"Created temporary kubeconfig at {kubeconfig_path}")
        return kubeconfig_path
    except Exception as e:
        print(f"Error creating kubeconfig: {str(e)}")
        raise

def test_kubectl_command(kubeconfig_path):
    """Test kubectl command with the kubeconfig"""
    try:
        env = os.environ.copy()
        env['KUBECONFIG'] = kubeconfig_path
        
        # Test kubectl version
        print("Testing kubectl version...")
        result = subprocess.run(
            ["kubectl", "version", "--client"],
            capture_output=True,
            text=True,
            env=env
        )
        print(f"kubectl version output: {result.stdout}")
        
        # Test kubectl get namespaces
        print("\nTesting kubectl get namespaces...")
        result = subprocess.run(
            ["kubectl", "get", "namespaces"],
            capture_output=True,
            text=True,
            env=env
        )
        if result.returncode == 0:
            print(f"kubectl get namespaces output: {result.stdout}")
        else:
            print(f"Error getting namespaces: {result.stderr}")
        
        # Test kubectl auth can-i
        print("\nTesting kubectl auth can-i...")
        result = subprocess.run(
            ["kubectl", "auth", "can-i", "list", "namespaces"],
            capture_output=True,
            text=True,
            env=env
        )
        if result.returncode == 0:
            print(f"kubectl auth can-i output: {result.stdout}")
        else:
            print(f"Error checking auth: {result.stderr}")
            
    except Exception as e:
        print(f"Error testing kubectl: {str(e)}")

def test_direct_token_auth(cluster_name, region):
    """Test authentication with a directly generated token"""
    try:
        # Get cluster info
        eks_client = boto3.client('eks', region_name=region)
        cluster_info = eks_client.describe_cluster(name=cluster_name)
        cluster_endpoint = cluster_info['cluster']['endpoint']
        cluster_cert = cluster_info['cluster']['certificateAuthority']['data']
        
        # Get token using aws eks get-token
        print("\nGetting token using aws eks get-token...")
        result = subprocess.run(
            ["aws", "eks", "get-token", "--cluster-name", cluster_name, "--region", region],
            capture_output=True,
            text=True
        )
        if result.returncode == 0:
            token_data = json.loads(result.stdout)
            token = token_data['status']['token']
            print(f"Successfully obtained token")
            
            # Create a temporary kubeconfig with this token
            temp_dir = tempfile.mkdtemp(prefix='kube-direct-')
            kubeconfig_path = os.path.join(temp_dir, 'config')
            
            kubeconfig = {
                'apiVersion': 'v1',
                'kind': 'Config',
                'clusters': [{
                    'name': cluster_name,
                    'cluster': {
                        'server': cluster_endpoint,
                        'certificate-authority-data': cluster_cert
                    }
                }],
                'users': [{
                    'name': f'eks-user-{cluster_name}',
                    'user': {
                        'token': token
                    }
                }],
                'contexts': [{
                    'name': f'eks-{cluster_name}',
                    'context': {
                        'cluster': cluster_name,
                        'user': f'eks-user-{cluster_name}'
                    }
                }],
                'current-context': f'eks-{cluster_name}'
            }
            
            with open(kubeconfig_path, 'w') as f:
                json.dump(kubeconfig, f)
            
            print(f"Created temporary kubeconfig with direct token at {kubeconfig_path}")
            
            # Test with this kubeconfig
            test_kubectl_command(kubeconfig_path)
        else:
            print(f"Error getting token: {result.stderr}")
    except Exception as e:
        print(f"Error testing direct token auth: {str(e)}")

def main():
    """Main function"""
    cluster_name = "sample-eks-cluster"
    region = "us-east-1"
    
    print(f"Testing EKS authentication for cluster {cluster_name} in region {region}")
    
    # Test with kubeconfig using exec plugin
    print("\n=== Testing with kubeconfig using exec plugin ===")
    kubeconfig_path = create_kubeconfig_with_token(cluster_name, region)
    test_kubectl_command(kubeconfig_path)
    
    # Test with direct token
    print("\n=== Testing with direct token ===")
    test_direct_token_auth(cluster_name, region)

if __name__ == "__main__":
    main()
