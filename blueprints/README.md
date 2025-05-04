# InfraUtilX Blueprints

This directory contains deployment blueprints - ready-to-use architectural patterns for common infrastructure scenarios built with InfraUtilX components. These blueprints provide production-grade templates that can be quickly deployed and customized.

## Available Blueprints

| Blueprint | Description |
|-----------|-------------|
| [EC2 with EBS](./ec2_with_ebs/) | Deploy an EC2 instance with an attached EBS volume and security group configured with your local IP address |
| [VS Code Server](./vscode_server/) | Deploy a browser-based VS Code development environment with persistent storage and secure access |

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

### Using AWS Profiles with Blueprints

To deploy a blueprint using a specific AWS profile:

1. List available AWS profiles to choose from:
   ```bash
   ../scripts/manage_profiles.py list --all-accounts
   ```

2. Set the desired AWS profile:
   ```bash
   export AWS_PROFILE=profile_name
   ```
   
   Or using the shell helper:
   ```bash
   source ~/.aws_profile_helpers.sh
   awsp switch profile_name
   ```

3. Deploy the blueprint:
   ```bash
   ./deploy.sh
   ```

## Blueprint Categories

### Development Environments

- **[VS Code Server](./vscode_server/)**: A cloud-based VS Code environment with persistent storage, accessible from any browser. Perfect for remote development or working across multiple devices.

### Compute Infrastructure

- **[EC2 with EBS](./ec2_with_ebs/)**: A fully configured EC2 instance with attached persistent storage, proper networking, and security settings.

## Creating New Blueprints

If you want to contribute a new blueprint:

1. Create a new directory in the appropriate category (e.g., `ec2`, `storage`, etc.)
2. Include a comprehensive README with prerequisites, architecture diagram and usage instructions
3. Implement a `deploy.sh` script for easy deployment
4. Add a `requirements.txt` file with the necessary dependencies
5. Ensure your blueprint follows infrastructure best practices
6. Add a test script to validate the blueprint works correctly
7. Submit a pull request with your blueprint 