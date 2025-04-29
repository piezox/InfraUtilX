# VS Code Server on AWS

This project provides scripts to easily set up and connect to a VS Code Server running on an AWS EC2 instance. The server includes persistent storage for your projects and extensions, making it a reliable development environment in the cloud. All scripts include robust error handling and recovery mechanisms to ensure a smooth experience across different AWS configurations.

## Features

- One-click setup of VS Code Server on AWS EC2
- Persistent EBS volume for your code and extensions
- Automatic security group management
- SSH tunneling for secure access
- Robust error handling and recovery
- Comprehensive cleanup script to remove all resources

## Prerequisites

- AWS CLI installed and configured with appropriate permissions
- `jq` command-line JSON processor
- SSH client
- Bash shell environment

## Quick Start

1. Clone this repository or download the scripts to your local machine
2. Make the scripts executable:
   ```bash
   chmod +x *.sh
   ```
3. Launch the VS Code Server:
   ```bash
   ./launch_vscode_server.sh
   ```
4. Follow the prompts to set up a new server or connect to an existing one
5. Access VS Code in your browser at http://localhost:8080 (default password: vscode123)

## Scripts Overview

### launch_vscode_server.sh

This script handles connecting to your VS Code Server. It will:

- Check if you have an existing VS Code Server configuration
- Start the instance if it's stopped
- Update security group rules to allow access from your current IP address
- Create an SSH tunnel to the server
- Prompt to set up a new server if none exists

### setup_vscode_server.sh

This script sets up a new VS Code Server on AWS. It will:

- Create a key pair for SSH access (or use existing one)
- Create a security group with appropriate rules
- Create a persistent EBS volume for your data
- Launch an EC2 instance with the latest Ubuntu AMI
- Install and configure VS Code Server on the instance
- Set up the persistent storage volume
- Install common development tools
- Create a separate security group update script on the instance

### destroy_vscode_server.sh

This script cleans up all AWS resources created for the VS Code Server. It will:

- Terminate the EC2 instance
- Delete the EBS volume
- Delete the security group
- Delete the key pair (optional)
- Remove local configuration files (optional)

## Configuration

The scripts create and use configuration files in `~/.vscode_server/`:

- `config`: Contains instance ID, volume ID, security group ID, and other settings
- `last_ip`: Caches your last IP address to avoid unnecessary security group updates

## Troubleshooting

### No Public IP or DNS Name

The script includes robust handling for instances that don't immediately receive a public DNS name:
- It will retry multiple times with increasing delays (up to 3 minutes)
- It will fall back to using the public IP address if no DNS name is available
- It ensures the instance is launched with a public IP by using the `--associate-public-ip-address` flag
- It provides clear error messages and troubleshooting guidance if connectivity issues persist

### Security Group Rule Issues

The scripts use `jq` instead of JMESPath queries to properly check for existing security group rules before adding new ones, avoiding the "duplicate rule" error and syntax issues. This approach works reliably across different AWS CLI versions and configurations.

### SSH Connection Issues

If you can't connect to your instance:
1. Check that your security group allows SSH access from your IP
2. Verify that your key pair is valid and has the correct permissions
3. Ensure the instance is in the "running" state

### Key Pair Management

If you encounter key pair issues:
1. The script will detect if a key exists locally but not in AWS
2. It will back up your old key and create a new one
3. This ensures seamless recovery after running the destroy script

## Advanced Usage

### Customizing Instance Type

Edit the `setup_vscode_server.sh` script to change the `INSTANCE_TYPE` variable:

```bash
INSTANCE_TYPE="t2.micro"  # Change to your preferred instance type
```

### Changing the Volume Size

Edit the `setup_vscode_server.sh` script to change the `VOLUME_SIZE` variable:

```bash
VOLUME_SIZE=20  # Size in GB
```

### Using a Different Port

Edit the `launch_vscode_server.sh` script to change the `LOCAL_PORT` variable:

```bash
LOCAL_PORT=8080  # Change to your preferred local port
```

## Security Considerations

- The default password for VS Code Server is "vscode123". Change this after first login.
- The security group is automatically updated to allow access only from your current IP address.
- All data is stored on an encrypted EBS volume.
- SSH keys are stored with appropriate permissions (600).

## Cost Management

This setup uses:
- An EC2 instance (default: t2.micro)
- A 20GB EBS volume
- Standard networking (no Elastic IP)

Remember to stop or terminate your instance when not in use to avoid unnecessary charges.

## License

This project is licensed under the MIT License - see the LICENSE file for details.
