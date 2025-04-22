"""
EKS operations for the EKS MCP Server
"""

import boto3
import logging
from typing import Dict, List, Any, Optional
from botocore.exceptions import ClientError

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class EKSOperations:
    """Class for EKS operations"""
    
    @staticmethod
    def get_eks_client(region: str):
        """Get an EKS client for the specified region"""
        return boto3.client('eks', region_name=region)
    
    @staticmethod
    def list_clusters(region: str) -> List[Dict[str, Any]]:
        """List all EKS clusters in a region"""
        try:
            client = EKSOperations.get_eks_client(region)
            response = client.list_clusters()
            
            clusters = []
            for cluster_name in response.get('clusters', []):
                try:
                    # Get detailed information for each cluster
                    cluster_info = client.describe_cluster(name=cluster_name)['cluster']
                    
                    clusters.append({
                        "name": cluster_info.get('name'),
                        "status": cluster_info.get('status'),
                        "version": cluster_info.get('version'),
                        "endpoint": cluster_info.get('endpoint'),
                        "created": cluster_info.get('createdAt').isoformat() if cluster_info.get('createdAt') else None
                    })
                except ClientError as e:
                    logger.error(f"Error describing cluster {cluster_name}: {str(e)}")
                    # Include basic information if detailed info can't be retrieved
                    clusters.append({
                        "name": cluster_name,
                        "status": "UNKNOWN",
                        "version": "UNKNOWN",
                        "endpoint": "UNKNOWN",
                        "created": None
                    })
            
            logger.info(f"Found {len(clusters)} EKS clusters in region {region}")
            return clusters
        except ClientError as e:
            logger.error(f"Error listing EKS clusters in region {region}: {str(e)}")
            raise RuntimeError(f"Error listing EKS clusters: {str(e)}")
    
    @staticmethod
    def describe_cluster(region: str, cluster_name: str) -> Dict[str, Any]:
        """Get detailed information about an EKS cluster"""
        try:
            client = EKSOperations.get_eks_client(region)
            response = client.describe_cluster(name=cluster_name)
            cluster_info = response.get('cluster', {})
            
            # Extract and format the relevant information
            result = {
                "name": cluster_info.get('name'),
                "status": cluster_info.get('status'),
                "version": cluster_info.get('version'),
                "endpoint": cluster_info.get('endpoint'),
                "created": cluster_info.get('createdAt').isoformat() if cluster_info.get('createdAt') else None,
                "roleArn": cluster_info.get('roleArn'),
                "resourcesVpcConfig": cluster_info.get('resourcesVpcConfig', {}),
                "logging": cluster_info.get('logging', {}),
                "identity": cluster_info.get('identity', {}),
                "tags": cluster_info.get('tags', {})
            }
            
            logger.info(f"Retrieved details for EKS cluster {cluster_name} in region {region}")
            return result
        except ClientError as e:
            logger.error(f"Error describing EKS cluster {cluster_name} in region {region}: {str(e)}")
            raise RuntimeError(f"Error describing EKS cluster: {str(e)}")
    
    @staticmethod
    def list_nodegroups(region: str, cluster_name: str) -> List[Dict[str, Any]]:
        """List all nodegroups in an EKS cluster"""
        try:
            client = EKSOperations.get_eks_client(region)
            response = client.list_nodegroups(clusterName=cluster_name)
            
            nodegroups = []
            for nodegroup_name in response.get('nodegroups', []):
                try:
                    # Get detailed information for each nodegroup
                    nodegroup_info = client.describe_nodegroup(
                        clusterName=cluster_name,
                        nodegroupName=nodegroup_name
                    )['nodegroup']
                    
                    nodegroups.append({
                        "name": nodegroup_info.get('nodegroupName'),
                        "status": nodegroup_info.get('status'),
                        "instanceType": nodegroup_info.get('instanceTypes', ['unknown'])[0] if nodegroup_info.get('instanceTypes') else 'unknown',
                        "desiredSize": nodegroup_info.get('scalingConfig', {}).get('desiredSize'),
                        "minSize": nodegroup_info.get('scalingConfig', {}).get('minSize'),
                        "maxSize": nodegroup_info.get('scalingConfig', {}).get('maxSize'),
                        "created": nodegroup_info.get('createdAt').isoformat() if nodegroup_info.get('createdAt') else None
                    })
                except ClientError as e:
                    logger.error(f"Error describing nodegroup {nodegroup_name}: {str(e)}")
                    # Include basic information if detailed info can't be retrieved
                    nodegroups.append({
                        "name": nodegroup_name,
                        "status": "UNKNOWN",
                        "instanceType": "UNKNOWN",
                        "desiredSize": None,
                        "minSize": None,
                        "maxSize": None,
                        "created": None
                    })
            
            logger.info(f"Found {len(nodegroups)} nodegroups in EKS cluster {cluster_name}")
            return nodegroups
        except ClientError as e:
            logger.error(f"Error listing nodegroups for EKS cluster {cluster_name} in region {region}: {str(e)}")
            raise RuntimeError(f"Error listing nodegroups: {str(e)}")
    
    @staticmethod
    def describe_nodegroup(region: str, cluster_name: str, nodegroup_name: str) -> Dict[str, Any]:
        """Get detailed information about a nodegroup"""
        try:
            client = EKSOperations.get_eks_client(region)
            response = client.describe_nodegroup(
                clusterName=cluster_name,
                nodegroupName=nodegroup_name
            )
            nodegroup_info = response.get('nodegroup', {})
            
            # Extract and format the relevant information
            result = {
                "name": nodegroup_info.get('nodegroupName'),
                "status": nodegroup_info.get('status'),
                "clusterName": nodegroup_info.get('clusterName'),
                "instanceType": nodegroup_info.get('instanceTypes', ['unknown'])[0] if nodegroup_info.get('instanceTypes') else 'unknown',
                "desiredSize": nodegroup_info.get('scalingConfig', {}).get('desiredSize'),
                "minSize": nodegroup_info.get('scalingConfig', {}).get('minSize'),
                "maxSize": nodegroup_info.get('scalingConfig', {}).get('maxSize'),
                "created": nodegroup_info.get('createdAt').isoformat() if nodegroup_info.get('createdAt') else None,
                "amiType": nodegroup_info.get('amiType'),
                "diskSize": nodegroup_info.get('diskSize'),
                "subnets": nodegroup_info.get('subnets', []),
                "remoteAccess": nodegroup_info.get('remoteAccess', {}),
                "tags": nodegroup_info.get('tags', {}),
                "health": nodegroup_info.get('health', {})
            }
            
            logger.info(f"Retrieved details for nodegroup {nodegroup_name} in EKS cluster {cluster_name}")
            return result
        except ClientError as e:
            logger.error(f"Error describing nodegroup {nodegroup_name} in EKS cluster {cluster_name} in region {region}: {str(e)}")
            raise RuntimeError(f"Error describing nodegroup: {str(e)}")
