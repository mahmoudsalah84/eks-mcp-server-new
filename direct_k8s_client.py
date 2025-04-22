"""
Direct Kubernetes client implementation using AWS SDK and requests
No kubectl dependency
"""

import boto3
import base64
import json
import requests
import tempfile
import os
import logging
from typing import Dict, List, Any, Optional

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class DirectK8sClient:
    """Direct Kubernetes client using AWS SDK and requests"""
    
    def __init__(self, cluster_name: str, region: str):
        """Initialize the client"""
        self.cluster_name = cluster_name
        self.region = region
        self.cluster_info = self._get_cluster_info()
        self.token = self._get_token()
        self.ca_file = self._create_ca_file()
    
    def __del__(self):
        """Clean up resources"""
        if hasattr(self, 'ca_file') and self.ca_file and os.path.exists(self.ca_file):
            os.remove(self.ca_file)
    
    def _get_cluster_info(self) -> Dict[str, str]:
        """Get cluster information"""
        try:
            eks_client = boto3.client('eks', region_name=self.region)
            response = eks_client.describe_cluster(name=self.cluster_name)
            
            return {
                'endpoint': response['cluster']['endpoint'],
                'ca_data': response['cluster']['certificateAuthority']['data']
            }
        except Exception as e:
            logger.error(f"Error getting cluster info: {str(e)}")
            raise RuntimeError(f"Error getting cluster info: {str(e)}")
    
    def _get_token(self) -> str:
        """Get a token for EKS authentication"""
        try:
            # Get STS client
            sts_client = boto3.client('sts', region_name=self.region)
            
            # Get caller identity
            identity = sts_client.get_caller_identity()
            logger.info(f"Current identity: {identity['Arn']}")
            
            # Create token
            session = boto3.Session(region_name=self.region)
            client = session.client('eks')
            
            # Get token
            response = client.get_token(clusterName=self.cluster_name)
            token = response['token']
            
            return token
        except Exception as e:
            logger.error(f"Error getting token: {str(e)}")
            
            # Try alternative method
            try:
                cmd = f"aws eks get-token --cluster-name {self.cluster_name} --region {self.region}"
                import subprocess
                result = subprocess.run(cmd, shell=True, check=True, capture_output=True, text=True)
                token_data = json.loads(result.stdout)
                return token_data['status']['token']
            except Exception as e2:
                logger.error(f"Error getting token via CLI: {str(e2)}")
                raise RuntimeError(f"Error getting token: {str(e)}, CLI error: {str(e2)}")
    
    def _create_ca_file(self) -> str:
        """Create a temporary CA file"""
        try:
            fd, ca_file = tempfile.mkstemp(prefix='eks-ca-', suffix='.crt')
            with os.fdopen(fd, 'w') as f:
                f.write(base64.b64decode(self.cluster_info['ca_data']).decode('utf-8'))
            
            return ca_file
        except Exception as e:
            logger.error(f"Error creating CA file: {str(e)}")
            raise RuntimeError(f"Error creating CA file: {str(e)}")
    
    def _make_request(self, path: str, method: str = 'GET', data: Optional[Dict] = None) -> Any:
        """Make a request to the Kubernetes API"""
        try:
            # Build URL
            url = f"{self.cluster_info['endpoint']}{path}"
            
            # Set headers
            headers = {
                'Authorization': f'Bearer {self.token}',
                'Accept': 'application/json',
                'Content-Type': 'application/json'
            }
            
            # Make request
            if method == 'GET':
                response = requests.get(url, headers=headers, verify=self.ca_file)
            elif method == 'POST':
                response = requests.post(url, headers=headers, json=data, verify=self.ca_file)
            elif method == 'PUT':
                response = requests.put(url, headers=headers, json=data, verify=self.ca_file)
            elif method == 'DELETE':
                response = requests.delete(url, headers=headers, verify=self.ca_file)
            else:
                raise ValueError(f"Unsupported HTTP method: {method}")
            
            response.raise_for_status()
            
            # Return JSON response if content exists
            if response.content:
                return response.json()
            return None
        except requests.exceptions.RequestException as e:
            logger.error(f"Error making request: {str(e)}")
            if hasattr(e, 'response') and e.response is not None:
                logger.error(f"Response: {e.response.text}")
            raise RuntimeError(f"Error making request: {str(e)}")
    
    def get_namespaces(self) -> List[Dict[str, Any]]:
        """Get all namespaces"""
        try:
            response = self._make_request('/api/v1/namespaces')
            
            namespaces = []
            for item in response.get("items", []):
                namespaces.append({
                    "name": item.get("metadata", {}).get("name"),
                    "status": item.get("status", {}).get("phase"),
                    "created": item.get("metadata", {}).get("creationTimestamp")
                })
            
            logger.info(f"Found {len(namespaces)} namespaces")
            return namespaces
        except Exception as e:
            logger.error(f"Error getting namespaces: {str(e)}")
            raise RuntimeError(f"Error getting namespaces: {str(e)}")
    
    def get_pods(self, namespace: str) -> List[Dict[str, Any]]:
        """Get all pods in a namespace"""
        try:
            response = self._make_request(f'/api/v1/namespaces/{namespace}/pods')
            
            pods = []
            for item in response.get("items", []):
                pod_name = item.get("metadata", {}).get("name")
                pod_status = item.get("status", {}).get("phase")
                pod_ip = item.get("status", {}).get("podIP", "N/A")
                node_name = item.get("spec", {}).get("nodeName", "N/A")
                containers = len(item.get("spec", {}).get("containers", []))
                
                pods.append({
                    "name": pod_name,
                    "status": pod_status,
                    "node": node_name,
                    "ip": pod_ip,
                    "containers": containers
                })
            
            logger.info(f"Found {len(pods)} pods in namespace {namespace}")
            return pods
        except Exception as e:
            logger.error(f"Error getting pods: {str(e)}")
            raise RuntimeError(f"Error getting pods: {str(e)}")
    
    def describe_pod(self, namespace: str, pod_name: str) -> Dict[str, Any]:
        """Get detailed information about a pod"""
        try:
            response = self._make_request(f'/api/v1/namespaces/{namespace}/pods/{pod_name}')
            
            # Extract relevant information
            metadata = response.get("metadata", {})
            spec = response.get("spec", {})
            status = response.get("status", {})
            
            pod_info = {
                "name": metadata.get("name"),
                "namespace": metadata.get("namespace"),
                "uid": metadata.get("uid"),
                "creationTimestamp": metadata.get("creationTimestamp"),
                "labels": metadata.get("labels", {}),
                "nodeName": spec.get("nodeName"),
                "hostIP": status.get("hostIP"),
                "podIP": status.get("podIP"),
                "phase": status.get("phase"),
                "containers": []
            }
            
            # Extract container information
            for container in spec.get("containers", []):
                container_info = {
                    "name": container.get("name"),
                    "image": container.get("image"),
                    "ports": container.get("ports", []),
                    "resources": container.get("resources", {})
                }
                pod_info["containers"].append(container_info)
            
            logger.info(f"Retrieved details for pod {pod_name} in namespace {namespace}")
            return pod_info
        except Exception as e:
            logger.error(f"Error describing pod: {str(e)}")
            raise RuntimeError(f"Error describing pod: {str(e)}")
    
    def get_deployments(self, namespace: str) -> List[Dict[str, Any]]:
        """Get all deployments in a namespace"""
        try:
            response = self._make_request(f'/apis/apps/v1/namespaces/{namespace}/deployments')
            
            deployments = []
            for item in response.get("items", []):
                metadata = item.get("metadata", {})
                spec = item.get("spec", {})
                status = item.get("status", {})
                
                deployments.append({
                    "name": metadata.get("name"),
                    "namespace": metadata.get("namespace"),
                    "replicas": spec.get("replicas"),
                    "available": status.get("availableReplicas", 0),
                    "ready": status.get("readyReplicas", 0),
                    "updated": status.get("updatedReplicas", 0),
                    "created": metadata.get("creationTimestamp")
                })
            
            logger.info(f"Found {len(deployments)} deployments in namespace {namespace}")
            return deployments
        except Exception as e:
            logger.error(f"Error getting deployments: {str(e)}")
            raise RuntimeError(f"Error getting deployments: {str(e)}")
    
    def describe_deployment(self, namespace: str, deployment_name: str) -> Dict[str, Any]:
        """Get detailed information about a deployment"""
        try:
            response = self._make_request(f'/apis/apps/v1/namespaces/{namespace}/deployments/{deployment_name}')
            
            # Extract relevant information
            metadata = response.get("metadata", {})
            spec = response.get("spec", {})
            status = response.get("status", {})
            
            deployment_info = {
                "name": metadata.get("name"),
                "namespace": metadata.get("namespace"),
                "uid": metadata.get("uid"),
                "creationTimestamp": metadata.get("creationTimestamp"),
                "labels": metadata.get("labels", {}),
                "replicas": spec.get("replicas"),
                "strategy": spec.get("strategy", {}).get("type"),
                "selector": spec.get("selector", {}).get("matchLabels", {}),
                "status": {
                    "availableReplicas": status.get("availableReplicas", 0),
                    "readyReplicas": status.get("readyReplicas", 0),
                    "updatedReplicas": status.get("updatedReplicas", 0),
                    "conditions": status.get("conditions", [])
                },
                "containers": []
            }
            
            # Extract container information from template
            template = spec.get("template", {}).get("spec", {})
            for container in template.get("containers", []):
                container_info = {
                    "name": container.get("name"),
                    "image": container.get("image"),
                    "ports": container.get("ports", []),
                    "resources": container.get("resources", {})
                }
                deployment_info["containers"].append(container_info)
            
            logger.info(f"Retrieved details for deployment {deployment_name} in namespace {namespace}")
            return deployment_info
        except Exception as e:
            logger.error(f"Error describing deployment: {str(e)}")
            raise RuntimeError(f"Error describing deployment: {str(e)}")
    
    def get_services(self, namespace: str) -> List[Dict[str, Any]]:
        """Get all services in a namespace"""
        try:
            response = self._make_request(f'/api/v1/namespaces/{namespace}/services')
            
            services = []
            for item in response.get("items", []):
                metadata = item.get("metadata", {})
                spec = item.get("spec", {})
                
                services.append({
                    "name": metadata.get("name"),
                    "namespace": metadata.get("namespace"),
                    "type": spec.get("type"),
                    "clusterIP": spec.get("clusterIP"),
                    "externalIP": spec.get("externalIPs", ["None"])[0] if spec.get("externalIPs") else "None",
                    "ports": spec.get("ports", []),
                    "created": metadata.get("creationTimestamp")
                })
            
            logger.info(f"Found {len(services)} services in namespace {namespace}")
            return services
        except Exception as e:
            logger.error(f"Error getting services: {str(e)}")
            raise RuntimeError(f"Error getting services: {str(e)}")
    
    def get_pod_logs(self, namespace: str, pod_name: str, container: Optional[str] = None, tail: int = 100) -> str:
        """Get logs from a pod"""
        try:
            # Build path
            path = f'/api/v1/namespaces/{namespace}/pods/{pod_name}/log?tailLines={tail}'
            if container:
                path += f'&container={container}'
            
            # Build URL
            url = f"{self.cluster_info['endpoint']}{path}"
            
            # Set headers
            headers = {
                'Authorization': f'Bearer {self.token}',
                'Accept': 'text/plain'
            }
            
            # Make request
            response = requests.get(url, headers=headers, verify=self.ca_file)
            response.raise_for_status()
            
            logger.info(f"Retrieved logs for pod {pod_name} in namespace {namespace}")
            return response.text
        except requests.exceptions.RequestException as e:
            logger.error(f"Error getting pod logs: {str(e)}")
            if hasattr(e, 'response') and e.response is not None:
                logger.error(f"Response: {e.response.text}")
            raise RuntimeError(f"Error getting pod logs: {str(e)}")
        except Exception as e:
            logger.error(f"Error in get_pod_logs: {str(e)}")
            raise RuntimeError(f"Error in get_pod_logs: {str(e)}")
