# InfraUtilX

A reusable AWS infrastructure library built with Pulumi for managing cloud resources efficiently and consistently.

## Overview

InfraUtilX provides a collection of reusable components and utilities for AWS infrastructure management using Pulumi. It's designed to be a foundation for building cloud infrastructure projects, promoting best practices and consistency across deployments.

## Features

- **EC2 Management**: Reusable components for EC2 instances, security groups, and key pairs
- **Storage Solutions**: EBS volumes and S3 bucket management
- **Networking**: VPC components and security utilities
- **Utilities**: Common utilities for tagging, AMI lookup, and more

## Installation

1. Clone the repository:
```bash
git clone https://github.com/yourusername/InfraUtilX.git  # TODO: Replace with your actual repository URL
cd InfraUtilX
```

2. Create and activate a virtual environment:
```bash
python3 -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
```

3. Install the package in development mode:
```bash
pip install -e .
```

## Running Tests

1. Install test dependencies:
```bash
pip install -r requirements-test.txt
```

2. Run all tests:
```bash
pytest tests/
```

3. Run tests for a specific module:
```bash
pytest tests/ec2/  # For EC2 tests
pytest tests/storage/  # For storage tests
pytest tests/utils/  # For utility tests
```

4. Run tests with coverage report:
```bash
pytest --cov=infrastructure tests/
```

## Usage

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

## Project Structure

```
InfraUtilX/
├── infrastructure/          # Main package code
│   ├── ec2/               # EC2 instance components
│   ├── networking/        # Networking components
│   ├── storage/          # Storage components
│   └── utils/            # Utility functions
├── tests/                 # Test files
│   ├── ec2/              # EC2 tests
│   ├── networking/       # Networking tests
│   ├── storage/         # Storage tests
│   └── utils/           # Utility tests
├── OldScriptX/           # Legacy scripts
├── scripts/              # Shell script utilities
├── setup.py             # Package configuration
├── requirements-test.txt # Test dependencies
└── README.md            # Project documentation
```

## Contributing

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Run tests to ensure everything works
5. Submit a pull request

## License

This project is licensed under the MIT License.
