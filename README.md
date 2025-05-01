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
- Launching an EC2 instance with all supporting infrastructure
- Attaching an EBS volume for additional storage
- Configuring security groups using your local machine's IP address

To use this blueprint:

```bash
# Navigate to the blueprint directory
cd blueprints/ec2_with_ebs

# Create a key and deploy
./deploy.sh --create-key
```

See the [blueprints directory](./blueprints/) for more detailed information.

## Project Structure

```
InfraUtilX/
├── infrastructure/          # Main package code
│   ├── ec2/               # EC2 instance components
│   ├── networking/        # Networking components
│   ├── storage/           # Storage components
│   └── utils/             # Utility functions
├── blueprints/             # Deployment blueprints
│   └── ec2_with_ebs/      # EC2 with EBS blueprint
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
