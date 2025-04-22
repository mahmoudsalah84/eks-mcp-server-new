"""
Kubernetes authentication configuration for EKS
"""

import os
import json
import boto3
import tempfile
import logging
from typing import Dict, Any, Optional

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class KubernetesAuthConfig:
    """Class for managing Kubernetes authentication configuration"""
    
    @staticmethod
    def get_eks_token(cluster_name: str, region: str) -> str:
        """Get a token for EKS authentication"""
        try:
            # Create a STS client
            sts_client = boto3.client('sts', region_name=region)
            
            # Get caller identity to verify permissions
            identity = sts_client.get_caller_identity()
            logger.info(f"Current identity: {identity['Arn']}")
            
            # Create token
            session = boto3.Session(region_name=region)
            client = session.client('eks')
            
            # Get token
            response = client.get_token(clusterName=cluster_name)
            token = response['token']
            
            logger.info(f"Successfully obtained EKS token for cluster {cluster_name}")
            return token
        except Exception as e:
            logger.error(f"Error getting EKS token: {str(e)}")
            
            # Try alternative method using AWS CLI
            try:
                import subprocess
                cmd = f"aws eks get-token --cluster-name {cluster_name} --region {region}"
                result = subprocess.run(cmd, shell=True, check=True, capture_output=True, text=True)
                token_data = json.loads(result.stdout)
                logger.info(f"Successfully obtained EKS token via CLI for cluster {cluster_name}")
                return token_data['status']['token']
            except Exception as e2:
                logger.error(f"Error getting EKS token via CLI: {str(e2)}")
                raise RuntimeError(f"Failed to get EKS token: {str(e)}, CLI error: {str(e2)}")
    
    @staticmethod
    def get_cluster_info(cluster_name: str, region: str) -> Dict[str, Any]:
        """Get cluster information including endpoint and CA data"""
        try:
            eks_client = boto3.client('eks', region_name=region)
            response = eks_client.describe_cluster(name=cluster_name)
            
            cluster_info = {
                'endpoint': response['cluster']['endpoint'],
                'ca_data': response['cluster']['certificateAuthority']['data']
            }
            
            logger.info(f"Successfully retrieved cluster info for {cluster_name}")
            return cluster_info
        except Exception as e:
            logger.error(f"Error getting cluster info: {str(e)}")
            raise RuntimeError(f"Failed to get cluster info: {str(e)}")
    
    @staticmethod
    def create_kubeconfig(cluster_name: str, region: str) -> str:
        """Create a kubeconfig file for the EKS cluster"""
        try:
            # Get cluster info
            cluster_info = KubernetesAuthConfig.get_cluster_info(cluster_name, region)
            endpoint = cluster_info['endpoint']
            ca_data = cluster_info['ca_data']
            
            # Get token
            token = KubernetesAuthConfig.get_eks_token(cluster_name, region)
            
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
            
            logger.info(f"Created kubeconfig file at {kubeconfig_path}")
            return kubeconfig_path
        except Exception as e:
            logger.error(f"Error creating kubeconfig: {str(e)}")
            raise RuntimeError(f"Failed to create kubeconfig: {str(e)}")
    
    @staticmethod
    def get_persistent_kubeconfig_path(cluster_name: str, region: str) -> str:
        """Get or create a persistent kubeconfig file"""
        # Define the path for the persistent kubeconfig
        kubeconfig_dir = os.path.join(os.path.expanduser("~"), ".kube")
        os.makedirs(kubeconfig_dir, exist_ok=True)
        kubeconfig_path = os.path.join(kubeconfig_dir, f"config-{cluster_name}")
        
        # Check if the kubeconfig exists and is recent (less than 10 minutes old)
        if os.path.exists(kubeconfig_path):
            # Check if the file is recent
            import time
            file_age = time.time() - os.path.getmtime(kubeconfig_path)
            if file_age < 600:  # 10 minutes in seconds
                logger.info(f"Using existing kubeconfig file at {kubeconfig_path}")
                return kubeconfig_path
        
        # Create a new kubeconfig
        try:
            # Get cluster info
            cluster_info = KubernetesAuthConfig.get_cluster_info(cluster_name, region)
            endpoint = cluster_info['endpoint']
            ca_data = cluster_info['ca_data']
            
            # Get token
            token = KubernetesAuthConfig.get_eks_token(cluster_name, region)
            
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
            
            # Write kubeconfig to file
            with open(kubeconfig_path, 'w') as f:
                json.dump(kubeconfig, f)
            
            logger.info(f"Created persistent kubeconfig file at {kubeconfig_path}")
            return kubeconfig_path
        except Exception as e:
            logger.error(f"Error creating persistent kubeconfig: {str(e)}")
            raise RuntimeError(f"Failed to create persistent kubeconfig: {str(e)}")
    
    @staticmethod
    def setup_environment_for_kubectl(cluster_name: str, region: str) -> Dict[str, str]:
        """Set up environment variables for kubectl"""
        kubeconfig_path = KubernetesAuthConfig.get_persistent_kubeconfig_path(cluster_name, region)
        
        # Return environment variables
        return {
            "KUBECONFIG": kubeconfig_path
        }
