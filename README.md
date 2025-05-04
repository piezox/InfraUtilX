# InfraUtilX

A reusable AWS infrastructure library built with Pulumi for managing cloud resources efficiently and consistently.

## Overview

InfraUtilX provides a collection of reusable components and utilities for AWS infrastructure management using Pulumi. It's designed to be a foundation for building cloud infrastructure projects, promoting best practices and consistency across deployments.

## Features

- **EC2 Management**: Reusable components for EC2 instances, security groups, and key pairs
- **Storage Solutions**: EBS volumes and S3 bucket management
- **Networking**: VPC components and security utilities
- **Utilities**: Common utilities for tagging, AMI lookup, IP address handling, and more
- **Blueprints**: Ready-to-use architectural patterns for common deployment scenarios
- **Stack Management**: Tools for managing access to deployed infrastructure when your IP changes

## Installation

### Basic Installation

For basic usage, clone the repository and install the package:

```bash
git clone https://github.com/piezox/InfraUtilX.git
cd InfraUtilX
pip install -e .
```

### Development Installation

If you're developing or contributing to InfraUtilX, install with development dependencies:

```bash
# Install the package with development dependencies
pip install -e ".[dev]"

# Alternatively, use the requirements files
pip install -r requirements.txt
pip install -r requirements-test.txt
```

## Running Tests

Run tests with pytest:

```bash
# Run all tests
pytest tests/

# Run tests for a specific module
pytest tests/ec2/     # For EC2 tests
pytest tests/storage/ # For storage tests
pytest tests/utils/   # For utility tests

# Run tests with coverage report
pytest --cov=infrastructure tests/
```

## Managing Access to Deployed Infrastructure

InfraUtilX includes a utility for managing access to your deployed infrastructure when your IP address changes. This is particularly useful for SSH access to EC2 instances.

### Prerequisites

Before using the access management utilities, make sure you have:

1. **Pulumi CLI** installed and configured
   ```bash
   # Install Pulumi CLI
   curl -fsSL https://get.pulumi.com | sh
   
   # Login to Pulumi
   pulumi login
   ```

### Usage

```bash
# List all stacks
./scripts/manage_access.py list

# Check if your current IP has access to all stacks
./scripts/manage_access.py check

# Update a security group to allow access from your current IP
./scripts/manage_access.py update dev/infrautilx-example
```

See the [scripts README](./scripts/README.md) for more details and troubleshooting information.

## Managing AWS Profiles

InfraUtilX includes a powerful AWS profile management utility that helps you work with multiple AWS profiles, accounts, and credentials. This is particularly useful when working across multiple AWS accounts or roles.

### AWS Profile Management Features

- **Profile Discovery**: Automatically detects all AWS profiles from your `~/.aws/config` and `~/.aws/credentials` files
- **Account Identification**: Shows AWS account numbers for each profile to easily identify which account you're working with
- **Authentication Method**: Identifies how each profile authenticates (API keys, SSO, assumed roles)
- **Identity Information**: Shows IAM user or role names to understand permissions context
- **Shell Integration**: Provides helper functions for your shell for easy profile switching and management
- **Credential Validation**: Verifies credentials are valid for each profile
- **SSO Support**: Handles AWS SSO refreshing for SSO-based profiles

### Prerequisites

Before using the AWS profile management utility, make sure you have:

1. **AWS CLI** installed and configured with profiles
2. **Pulumi CLI** installed (for credential validation)

### Command-Line Usage

```bash
# List all profiles (with basic information)
./scripts/manage_profiles.py list

# List all profiles with account IDs and identity info
./scripts/manage_profiles.py list --all-accounts

# Show current active profile
./scripts/manage_profiles.py current

# Switch to a different profile
./scripts/manage_profiles.py switch profile_name

# Validate credentials for a profile
./scripts/manage_profiles.py validate --profile profile_name

# Refresh SSO credentials for a profile
./scripts/manage_profiles.py refresh-sso profile_name

# Get shell helper functions
./scripts/manage_profiles.py shell-helpers
```

### Shell Integration

For easier day-to-day use, add the shell helper function to your `.bashrc` or `.zshrc`:

```bash
# Save the helper functions
./scripts/manage_profiles.py shell-helpers > ~/.aws_profile_helpers.sh

# Add it to your shell config
echo 'source ~/.aws_profile_helpers.sh' >> ~/.zshrc

# Source it in your current shell
source ~/.aws_profile_helpers.sh
```

This adds a unified `awsp` command for profile management:

```bash
# Show help
awsp

# List profiles (without account IDs)
awsp ls

# List profiles with account IDs and identity info
awsp ls -a

# Show current profile
awsp current

# Switch to a profile
awsp switch profile_name
# or
awsp use profile_name

# Validate credentials
awsp validate [profile_name]

# Refresh SSO credentials
awsp sso profile_name
```

### Example Output

```
AWS Profiles:
  default - us-east-1 - Account: 123456789012 [api_key, admin] (DEFAULT)
→ dev-account - us-west-2 - Account: 234567890123 [sso, AdministratorAccess] (ACTIVE, SSO)
  prod-account - us-east-1 - Account: 345678901234 [role, PowerUserAccess]

Active profile: dev-account
```

The output shows:
- Profile name and region
- AWS account ID
- Authentication method and identity (user/role)
- Status indicators (ACTIVE, DEFAULT, SSO)
- Current active profile (indicated by →)

See the [scripts README](./scripts/README.md) for more details and troubleshooting information.

## Usage

### Basic Component Usage

```python
from infrastructure.ec2.instances import create_instance
from infrastructure.networking.vpc import create_vpc

# Create a VPC
vpc = create_vpc("my-vpc", cidr_block="10.0.0.0/16")

# Create an EC2 instance
instance = create_instance(
    "my-instance",
    instance_type="t2.micro",
    vpc=vpc,
    subnet_id="subnet-123456"
)
```

### Blueprints

We provide several deployment blueprints that show how to use the InfraUtilX components together to build complete infrastructure patterns:

#### EC2 with EBS Blueprint

This blueprint provides a production-ready pattern for:
- Launching an EC2 instance with all supporting infrastructure (VPC, subnet, internet gateway, route tables)
- Proper subnet routing configuration for public internet access
- Attaching and automatically initializing an EBS volume for additional storage
- Configuring security groups using your local machine's IP address
- Automated key pair management in the correct region
- Enhanced SSH connectivity testing and troubleshooting

To use this blueprint:

```bash
# Navigate to the blueprint directory
cd blueprints/ec2_with_ebs

# Deploy (will create .env file on first run)
./deploy.sh

# Deploy with a specific region (overrides .env setting)
./deploy.sh --region us-east-1

# Test SSH connectivity manually
./test_ssh.sh

# Destroy resources when done
./destroy.sh
```

Features of the EC2 with EBS blueprint:
- Interactive configuration with environment variable management
- AWS SSO support for credential management
- Automatically creates a VPC with proper internet gateway and route table configuration
- Associates the subnet with the route table to ensure instances have internet access
- Detects your local IP address and configures security group rules for SSH access
- Automatically formats and mounts the EBS volume on instance startup
- Configures the EBS volume to persist across instance reboots via /etc/fstab
- Properly manages key pairs in the selected AWS region
- Comprehensive SSH connectivity testing with troubleshooting guidance
- Detailed logging for easier debugging

See the [blueprints directory](./blueprints/) for more detailed information.

## Scripts

InfraUtilX includes several utility scripts to help manage your infrastructure:

### Stack Management Scripts

- **manage_access.py**: Manages access to your deployed infrastructure when your IP changes
  ```bash
  ./scripts/manage_access.py list    # List all stacks
  ./scripts/manage_access.py check   # Check if your IP has access
  ./scripts/manage_access.py update  # Update security group with your IP
  ```

### AWS Profile Management

- **manage_profiles.py**: Manages AWS profiles and credentials with Pulumi integration
  ```bash
  ./scripts/manage_profiles.py list            # List all profiles
  ./scripts/manage_profiles.py current         # Show current profile
  ./scripts/manage_profiles.py switch PROFILE  # Switch to profile
  ./scripts/manage_profiles.py validate        # Validate credentials
  ./scripts/manage_profiles.py refresh-sso PROFILE  # Refresh SSO credentials
  ./scripts/manage_profiles.py shell-helpers   # Get shell helper functions
  ```

### Blueprint Scripts

- **deploy.sh**: Interactive deployment script for blueprints
  ```bash
  ./blueprints/ec2_with_ebs/deploy.sh              # Deploy with interactive setup
  ./blueprints/ec2_with_ebs/deploy.sh --sso-login  # Deploy with AWS SSO login
  ./blueprints/ec2_with_ebs/deploy.sh --destroy    # Destroy resources
  ```

- **test_ssh.sh**: Tests SSH connectivity to deployed instances
  ```bash
  ./blueprints/ec2_with_ebs/test_ssh.sh            # Test SSH connectivity
  ./blueprints/ec2_with_ebs/test_ssh.sh --verbose  # Test with verbose output
  ```

- **destroy.sh**: Dedicated script for destroying resources
  ```bash
  ./blueprints/ec2_with_ebs/destroy.sh             # Destroy resources
  ```

All scripts include detailed help information accessible via the `--help` flag.

## Project Structure

```
InfraUtilX/
├── infrastructure/          # Main package code
│   ├── ec2/               # EC2 instance components
│   ├── networking/        # Networking components
│   ├── storage/           # Storage components
│   └── utils/             # Utility functions and stack management
├── blueprints/             # Deployment blueprints
│   └── ec2_with_ebs/      # EC2 with EBS blueprint
├── scripts/                # Utility scripts
│   └── manage_access.py   # Script for managing access to stacks
├── tests/                  # Test files
│   ├── ec2/               # EC2 tests
│   ├── networking/        # Networking tests
│   ├── storage/           # Storage tests
│   └── utils/             # Utility tests
├── OldScriptX.zip          # Legacy scripts (archived)
├── setup.py                # Package configuration
├── requirements.txt        # Runtime dependencies
├── requirements-test.txt   # Test dependencies (extends requirements.txt)
└── README.md               # Project documentation
```

## Contributing

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Run tests to ensure everything works
5. Submit a pull request

## License

This project is licensed under the MIT License.