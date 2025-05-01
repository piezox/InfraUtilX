# InfraUtilX Blueprints

This directory contains deployment blueprints - ready-to-use architectural patterns for common infrastructure scenarios built with InfraUtilX components. These blueprints provide production-grade templates that can be quickly deployed and customized.

## Available Blueprints

| Blueprint | Description |
|-----------|-------------|
| [EC2 with EBS](./ec2_with_ebs/) | Deploy an EC2 instance with an attached EBS volume and security group configured with your local IP address |

## Using the Blueprints

Each blueprint contains:
- A `README.md` with comprehensive instructions
- A deployment script (`deploy.sh`) to run the blueprint
- Pulumi code implementing the infrastructure pattern
- A `requirements.txt` for the dependencies

To deploy a blueprint:
1. Navigate to the blueprint directory
2. Run the deployment script with the desired options
   ```bash
   ./deploy.sh [options]
   ```
3. Follow the specific instructions in the blueprint's README

The deployment script will:
- Set up a Python virtual environment
- Install both InfraUtilX and the blueprint-specific dependencies
- Initialize a Pulumi stack
- Deploy the infrastructure

## Creating New Blueprints

If you want to contribute a new blueprint:

1. Create a new directory in the appropriate category (e.g., `ec2`, `storage`, etc.)
2. Include a comprehensive README with prerequisites, architecture diagram and usage instructions
3. Implement a `deploy.sh` script for easy deployment
4. Add a `requirements.txt` file with the necessary dependencies
5. Ensure your blueprint follows infrastructure best practices
6. Add a test script to validate the blueprint works correctly
7. Submit a pull request with your blueprint 