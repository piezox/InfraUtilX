# EC2 with EBS Blueprint

This blueprint provides a production-ready pattern for deploying an EC2 instance with an attached EBS volume.

## Features

- Launches an EC2 instance with all supporting infrastructure (VPC, subnet, internet gateway, route tables)
- Proper subnet routing configuration for public internet access
- Attaches and automatically initializes an EBS volume for additional storage
- Configures security groups using your local machine's IP address
- Automated key pair management in the correct region
- Enhanced SSH connectivity testing and troubleshooting

## Prerequisites

- Pulumi CLI installed
- AWS CLI installed and configured
- Python 3.8 or higher

## Quick Start

```bash
# Navigate to the blueprint directory
cd blueprints/ec2_with_ebs

# Deploy (interactive setup)
./deploy.sh

# Destroy when done
./destroy.sh
```

On first run, the script will guide you through setting up all necessary configuration options.

## SSH Connectivity Testing

The deployment script automatically tests SSH connectivity to the instance after deployment. If you want to run the test manually:

```bash
# Test SSH connectivity
./test_ssh.sh

# Test with verbose output
./test_ssh.sh --verbose

# Test with custom timeout
./test_ssh.sh --timeout 10
```

If SSH connectivity fails, the script provides detailed troubleshooting steps.

## Configuration

This blueprint uses a `.env` file for configuration. The deployment script will interactively ask for all necessary values when first run.

### Environment Variables

| Variable | Description | Default |
|----------|-------------|---------|
| `PULUMI_CONFIG_PASSPHRASE` | Passphrase for encrypting Pulumi secrets | (empty) |
| `PULUMI_ACCESS_TOKEN` | Leave empty to use AWS SDK's credential chain | (empty) |
| `AWS_REGION` | AWS region to deploy to | us-west-2 |
| `AWS_PROFILE` | AWS CLI profile to use | default |
| `AWS_SSO_PROFILE` | AWS SSO profile name (if using SSO) | (empty) |
| `INSTANCE_TYPE` | EC2 instance type | t2.micro |
| `EBS_SIZE` | Size of the EBS volume in GB | 20 |
| `PROJECT_NAME` | Name of the project | infrautilx-example |
| `ENVIRONMENT` | Environment name | dev |
| `PULUMI_STACK` | Pulumi stack name | dev |

## AWS SSO Configuration

If you're using AWS SSO, the script will ask for your SSO profile name during setup. You can also:

1. Use the `--sso-login` flag when deploying to force an SSO login:
   ```bash
   ./deploy.sh --sso-login
   ```

2. Check your AWS SSO configuration:
   ```bash
   # Check your AWS config file
   cat ~/.aws/config
   ```

## Usage

### Deployment

To deploy the blueprint:

```bash
# Deploy with interactive setup (first run)
./deploy.sh

# Deploy with existing configuration
./deploy.sh

# Deploy with a specific region (overrides .env setting)
./deploy.sh --region us-east-1

# Deploy with a specific AWS profile (overrides .env setting)
./deploy.sh --profile my-profile

# Deploy with AWS SSO login
./deploy.sh --sso-login

# Deploy with non-interactive mode (uses defaults or existing .env)
./deploy.sh --skip-prompts

# Deploy without SSH connectivity testing
./deploy.sh --no-test-ssh
```

### Destruction

To destroy the deployed resources:

```bash
# Using the deploy script
./deploy.sh --destroy

# Or using the dedicated destroy script
./destroy.sh

# Destroy with AWS SSO login
./destroy.sh --sso-login
```

## Troubleshooting SSH Connectivity Issues

If you're having trouble connecting to the instance via SSH, here are some common issues and solutions:

### 1. Security Group Configuration

- **Issue**: Security group doesn't allow SSH access from your IP
- **Solution**: The blueprint now allows SSH from anywhere (0.0.0.0/0) for initial troubleshooting

### 2. Network Configuration

- **Issue**: VPC or subnet routing is not properly configured
- **Solution**: The blueprint ensures proper route table configuration with internet gateway

### 3. SSH Service Issues

- **Issue**: SSH service not running or misconfigured on the instance
- **Solution**: The user data script now explicitly configures and restarts the SSH service

### 4. AMI Issues

- **Issue**: Some Ubuntu AMIs have issues with SSH
- **Solution**: The blueprint now uses a known working AMI (ami-075686beab831bb7f)

### 5. Instance Initialization

- **Issue**: Instance still initializing when SSH test runs
- **Solution**: The deploy script now waits 60 seconds before testing SSH connectivity

### 6. Detailed Logs

- **Issue**: Hard to diagnose what's happening on the instance
- **Solution**: The user data script now creates detailed logs at `/var/log/infrautilx-startup.log`

## How It Works

1. The script asks for configuration values and creates a `.env` file
2. It loads environment variables from the `.env` file
3. It handles AWS SSO login if needed
4. It sets up a Python virtual environment and installs dependencies
5. It initializes or selects the Pulumi stack
6. It configures the stack with values from the `.env` file
7. It deploys the infrastructure using Pulumi
8. It tests SSH connectivity to the instance
9. It provides detailed troubleshooting information if needed