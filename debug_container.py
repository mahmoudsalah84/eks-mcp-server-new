#!/usr/bin/env python3
"""
Debug script to run inside the container to test EKS authentication
"""

import boto3
import json
import os
import subprocess
import tempfile
import logging
import sys

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

def test_aws_credentials():
    """Test AWS credentials"""
    try:
        logger.info("Testing AWS credentials...")
        sts_client = boto3.client('sts')
        identity = sts_client.get_caller_identity()
        logger.info(f"AWS Identity: {json.dumps(identity, default=str)}")
        
        # Test EKS access
        logger.info("Testing EKS access...")
        eks_client = boto3.client('eks', region_name='us-east-1')
        clusters = eks_client.list_clusters()
        logger.info(f"EKS Clusters: {json.dumps(clusters, default=str)}")
        
        return True
    except Exception as e:
        logger.error(f"Error testing AWS credentials: {str(e)}")
        return False

def create_kubeconfig(cluster_name, region):
    """Create a kubeconfig file for kubectl"""
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
        
        logger.info(f"Created temporary kubeconfig at {kubeconfig_path}")
        return kubeconfig_path
    except Exception as e:
        logger.error(f"Error creating kubeconfig: {str(e)}")
        return None

def test_kubectl_command(kubeconfig_path):
    """Test kubectl command with the kubeconfig"""
    try:
        env = os.environ.copy()
        env['KUBECONFIG'] = kubeconfig_path
        
        # Test kubectl version
        logger.info("Testing kubectl version...")
        result = subprocess.run(
            ["kubectl", "version", "--client"],
            capture_output=True,
            text=True,
            env=env
        )
        logger.info(f"kubectl version output: {result.stdout}")
        if result.stderr:
            logger.error(f"kubectl version stderr: {result.stderr}")
        
        # Test kubectl get namespaces
        logger.info("\nTesting kubectl get namespaces...")
        result = subprocess.run(
            ["kubectl", "get", "namespaces"],
            capture_output=True,
            text=True,
            env=env
        )
        if result.returncode == 0:
            logger.info(f"kubectl get namespaces output: {result.stdout}")
        else:
            logger.error(f"Error getting namespaces: {result.stderr}")
        
        # Test kubectl auth can-i
        logger.info("\nTesting kubectl auth can-i...")
        result = subprocess.run(
            ["kubectl", "auth", "can-i", "list", "namespaces"],
            capture_output=True,
            text=True,
            env=env
        )
        if result.returncode == 0:
            logger.info(f"kubectl auth can-i output: {result.stdout}")
        else:
            logger.error(f"Error checking auth: {result.stderr}")
            
    except Exception as e:
        logger.error(f"Error testing kubectl: {str(e)}")

def test_direct_token_auth(cluster_name, region):
    """Test authentication with a directly generated token"""
    try:
        # Get cluster info
        eks_client = boto3.client('eks', region_name=region)
        cluster_info = eks_client.describe_cluster(name=cluster_name)
        cluster_endpoint = cluster_info['cluster']['endpoint']
        cluster_cert = cluster_info['cluster']['certificateAuthority']['data']
        
        # Get token using aws eks get-token
        logger.info("\nGetting token using aws eks get-token...")
        result = subprocess.run(
            ["aws", "eks", "get-token", "--cluster-name", cluster_name, "--region", region],
            capture_output=True,
            text=True
        )
        if result.returncode == 0:
            token_data = json.loads(result.stdout)
            token = token_data['status']['token']
            logger.info(f"Successfully obtained token")
            
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
            
            logger.info(f"Created temporary kubeconfig with direct token at {kubeconfig_path}")
            
            # Test with this kubeconfig
            test_kubectl_command(kubeconfig_path)
        else:
            logger.error(f"Error getting token: {result.stderr}")
    except Exception as e:
        logger.error(f"Error testing direct token auth: {str(e)}")

def main():
    """Main function"""
    cluster_name = "sample-eks-cluster"
    region = "us-east-1"
    
    logger.info(f"Testing EKS authentication for cluster {cluster_name} in region {region}")
    
    # Test AWS credentials
    if not test_aws_credentials():
        logger.error("AWS credentials test failed")
        sys.exit(1)
    
    # Test with kubeconfig using exec plugin
    logger.info("\n=== Testing with kubeconfig using exec plugin ===")
    kubeconfig_path = create_kubeconfig(cluster_name, region)
    if kubeconfig_path:
        test_kubectl_command(kubeconfig_path)
    
    # Test with direct token
    logger.info("\n=== Testing with direct token ===")
    test_direct_token_auth(cluster_name, region)

if __name__ == "__main__":
    main()
