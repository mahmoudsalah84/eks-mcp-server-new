# EKS MCP Client V6 with Bedrock Inline Agents

This client provides a conversational interface to the EKS MCP (Model Context Protocol) Server using Amazon Bedrock. It supports Amazon Bedrock inline agents functionality for more efficient operation execution.

## Features

- Automatic discovery of available operations from the MCP server
- Conversational interface using Amazon Bedrock models
- Support for Amazon Bedrock inline agents functionality
- Conversation context tracking
- Comprehensive logging
- Flexible configuration options

## Client Versions

The client directory contains multiple versions of the client:
- `mcp_client.py`: Base client for interacting with the MCP server
- `mcp_chat_client.py`: Original chat client
- `mcp_chat_client_v5.py`: Version 5 with improved conversation handling
- `mcp_chat_client_v6.py`: Latest version with Bedrock inline agents support
- `cli.py`: Command-line interface for the client

## Requirements

- Python 3.8+
- AWS credentials with access to Amazon Bedrock
- Access to an EKS MCP Server

## Installation

1. Install the required dependencies:

```bash
pip install -r requirements.txt
```

2. Configure your AWS credentials:

```bash
aws configure
```

## Configuration

The client can be configured in several ways:

1. Command-line arguments
2. Configuration file
3. Environment variables

### Configuration File

Create a `client_config.json` file with the following structure:

```json
{
  "mcp_server_url": "http://your-mcp-server:8000",
  "mcp_api_key": "your-api-key"
}
```

The client will look for this file in the following locations:
- Current directory
- Client directory
- Parent directory
- User's home directory (`~/.eks-mcp/config.json`)

### Environment Variables

You can also set the following environment variables:

```bash
export MCP_SERVER_URL="http://your-mcp-server:8000"
export MCP_API_KEY="your-api-key"
```

## Usage

```bash
python mcp_chat_client_v6.py [options]
```

### Options

- `--server-url`: MCP server URL (overrides config file)
- `--api-key`: API key for authentication (overrides config file)
- `--config`: Path to config file
- `--region`: AWS region (default: us-east-1)
- `--model`: Bedrock model ID (default: anthropic.claude-3-sonnet-20240229-v1:0)
- `--debug`: Enable debug logging
- `--list-operations`: List available MCP operations and exit
- `--disable-inline-agents`: Disable Bedrock inline agents functionality
- `--verbose`: Enable verbose output of API requests and responses

## Inline Agents Functionality

The client supports Amazon Bedrock inline agents functionality, which allows the model to execute MCP operations directly. This enables more efficient and accurate responses to user queries about EKS clusters.

When the model needs to retrieve information from the MCP server, it can use the `mcp_operation` tool to execute operations directly, rather than suggesting AWS CLI or kubectl commands.

## Example

```bash
python mcp_chat_client_v6.py --region us-east-1
```

This will start a conversation with the assistant, which can help you interact with your EKS clusters.

## Commands

During the conversation, you can use the following commands:

- `exit` or `quit`: End the conversation
- `operations`: List available MCP operations
- `verbose`: Toggle verbose output

## Current Configuration

The client is currently configured to connect to the MCP server at:
- Server URL: http://3.90.45.69:8000
- API Key: [REDACTED - Configure in your environment]

## Logging

Logs are stored in the `logs` directory with timestamps. Each session creates a new log file.

## Troubleshooting

If you encounter issues with the client:

1. Enable debug logging with the `--debug` flag
2. Enable verbose output with the `--verbose` flag or by typing `verbose` during the conversation
3. Check the log files in the `logs` directory
4. Verify that the MCP server is accessible and that the API key is correct
5. Ensure that you have the necessary AWS permissions to use Amazon Bedrock

## Example Conversation

```
EKS MCP Chat Assistant V6 with Bedrock Inline Agents
Type 'exit' or 'quit' to end the conversation
Type 'operations' to list available MCP operations
Type 'verbose' to toggle verbose output
--------------------------------------------------

You: list my clusters

I'll help you list your EKS clusters. Let me fetch that information for you.

Your EKS clusters in us-east-1:
- sample-eks-cluster (ACTIVE)
  Created on: 2025-04-15 08:28:02+00:00
  Kubernetes version: 1.28
  Endpoint: https://ABCDEF1234567890ABCDEF1234567890.gr7.us-east-1.eks.amazonaws.com

You: tell me about the nodegroups in sample-eks-cluster

I'll get information about the nodegroups in the sample-eks-cluster for you.

The sample-eks-cluster has 1 nodegroup:

Nodegroup: standard-workers
- Status: ACTIVE
- Instance type: t3.medium
- Capacity: 3 nodes (min: 2, max: 4)
- Created on: 2025-04-15 08:30:22+00:00
- AMI type: AL2023_x86_64_STANDARD
- Disk size: 20 GB

This nodegroup is currently active and running 3 t3.medium instances with Amazon Linux 2023.

You: what namespaces are in the cluster?

I'll retrieve the namespaces in your sample-eks-cluster.

The sample-eks-cluster has the following namespaces:

1. default (Active) - Created on: 2025-04-15 08:28:02Z
2. kube-node-lease (Active) - Created on: 2025-04-15 08:28:02Z
3. kube-public (Active) - Created on: 2025-04-15 08:28:02Z
4. kube-system (Active) - Created on: 2025-04-15 08:28:02Z
5. mcp-test-namespace (Active) - Created on: 2025-04-16 11:04:12Z
6. mcp-test-namespace-2 (Active) - Created on: 2025-04-16 11:18:43Z

The first four are default Kubernetes namespaces, and there are two additional test namespaces that have been created.

You: show me the pods in mcp-test-namespace

I'll retrieve the pods in the mcp-test-namespace for you.

Pods in mcp-test-namespace:

1. mcp-test-app-5fc69cf89c-dqf2z
   - Status: Running
   - Node: ip-172-31-21-87.ec2.internal
   - IP: 172.31.16.70
   - Containers: 1

2. mcp-test-app-5fc69cf89c-j6hwv
   - Status: Running
   - Node: ip-172-31-79-205.ec2.internal
   - IP: 172.31.74.178
   - Containers: 1

Both pods are running successfully as part of the mcp-test-app deployment.

You: exit
```

## Server Integration

The client is designed to work with the EKS MCP Server, which provides a standardized interface for GenAI agents to interact with EKS clusters. See the [Server README](../README.md) for details on the server implementation.

## Recent Updates

- Added support for Bedrock inline agents functionality
- Improved error handling and logging
- Updated to work with the latest server implementation using kubectl authentication
- Added support for all server operations
- Improved conversation context tracking
