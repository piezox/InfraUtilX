# VS Code Server Blueprint

This blueprint extends the EC2 with EBS blueprint to deploy a VS Code Server for remote development in the cloud. It provides a browser-based VS Code experience with persistent storage and secure access.

## Features

- **Extends EC2 with EBS Blueprint**: Inherits all functionality from the base blueprint including networking, security, and storage
- **VS Code Server**: Installs and configures code-server, a browser-based VS Code environment
- **Secure Access**: Restricts access to your local IP address only
- **Persistent Storage**: Uses a 40GB EBS volume for storing code, configuration, and dependencies
- **Performance Optimized**: Runs on a t3.medium instance for smooth development experience
- **Automatic Configuration**: Handles all the setup complexity, including user accounts and persistent storage
- **Password Protection**: Generates a secure random password for VS Code Server access

## Usage

### Prerequisites

- Pulumi CLI installed
- AWS CLI installed and configured
- Python 3.8 or higher

### Deployment

```bash
# Navigate to the blueprint directory
cd blueprints/vscode_server

# Deploy with interactive setup
./deploy.sh

# Destroy when finished
./destroy.sh
```

After deployment completes, you'll receive:
- URL to access VS Code Server in your browser
- Secure password for authentication
- SSH command for direct access to the instance

### Remote Development Features

This blueprint enables:

1. **Browser-Based Development**: Access your development environment from any device with a browser
2. **Persistent Workspace**: Your code and configuration persist between sessions
3. **Full Terminal Access**: Run commands directly in the browser terminal
4. **Extension Support**: Install VS Code extensions as needed
5. **Git Integration**: Pre-configured for source control management
6. **Workspace Sync**: Automatically syncs with the EBS volume mounted at `/data/workspace`

## Blueprint Architecture

This blueprint demonstrates best practices for extending existing blueprints:

1. **Component Reuse**: Leverages the existing EC2 with EBS infrastructure
2. **Configuration Override**: Customizes instance type and EBS size without duplicating code
3. **Template Approach**: Uses a template for user data script with variable substitution
4. **Security Focus**: Restricts access to your IP address only
5. **Clear Outputs**: Provides all necessary information for connecting to the server

## Configuration Options

The blueprint provides these customizable parameters:

| Parameter | Default | Description |
|-----------|---------|-------------|
| instance_type | t3.medium | EC2 instance type for VS Code Server |
| ebs_size | 40 | Size in GB for the attached EBS volume |
| vscode_port | 8080 | Port for VS Code Server access |
| project | vscode-server | Project name for tagging resources |
| environment | dev | Environment name for tagging |

## Security Considerations

- Access to VS Code Server is restricted to your local IP address
- SSH access is restricted to your local IP address
- A secure random password is generated for VS Code Server authentication
- The password is displayed only in Pulumi outputs (not stored in the code)
- For production use, consider enabling HTTPS with a proper SSL certificate

## Troubleshooting

### Connecting to VS Code Server

If you're having trouble connecting:

1. Verify your IP address hasn't changed (check outputs with `pulumi stack output authorized_ip`)
2. Ensure the security group allows traffic from your IP address
3. Check the instance is running (`pulumi stack output instance_id`)
4. Confirm VS Code Server is running by SSH into the instance and checking:
   ```bash
   sudo systemctl status code-server
   ```

### Logs and Debugging

Important log files:
- VS Code Server setup: `/var/log/vscode-server-setup.log`
- VS Code Server runtime: `/home/ubuntu/.local/share/code-server/logs/`
- System logs: `/var/log/syslog`

## Extending This Blueprint

To customize this blueprint:

1. Modify the `CONFIG` object in `__main__.py` to change instance type, EBS size, etc.
2. Update `user_data.sh.tpl` to install additional tools or packages
3. Add new security group rules for additional ports/services
4. Add more Pulumi exports to expose additional information

## How It Works

1. Creates VPC, subnet, internet gateway, security groups, and routing
2. Generates a secure random password for VS Code Server
3. Launches an EC2 instance with our user data script
4. Creates and attaches an EBS volume
5. Installs and configures VS Code Server on the instance
6. Sets up the EBS volume for persistent storage
7. Configures a web server to expose VS Code Server
8. Outputs the URL and login credentials

By extending the EC2 with EBS blueprint, this blueprint ensures future improvements to the base blueprint are automatically inherited.

## Known Issues and Fixes

### EBS Volume Mounting
The script now includes enhanced error handling for EBS volume mounting:
- Correctly detects the actual device name, avoiding confusion with the root volume
- Checks if the device is already mounted before attempting to format
- Verifies if the device already has a filesystem before formatting
- Creates proper mount point directories with appropriate permissions

### Code-Server Installation
The installation script has been improved to:
- Ensure the HOME environment variable is always set correctly
- Verify the successful installation of code-server
- Include a fallback installation method through apt if the curl method fails
- Add explicit environment variables in the systemd service
- Provide better error handling and logging