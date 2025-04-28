# EC2 VS Code Server Connection Tool

A secure and dynamic solution for connecting to VS Code Server running on an AWS EC2 instance.

## Overview

This repository contains a script that automates the process of:

1. Dynamically updating EC2 security groups based on your current IP address
2. Establishing a secure SSH tunnel to a VS Code Server running on an EC2 instance
3. Handling instance reboots and IP address changes automatically

## Features

- **Dynamic IP Management**: Automatically updates security group rules when your IP address changes
- **Instance Resilience**: Uses instance ID instead of hostname to handle EC2 public DNS changes after reboots
- **Least Privilege Security**: Implements security best practices by restricting SSH access to only your current IP
- **Efficient Updates**: Avoids unnecessary AWS API calls by checking if your IP has changed since last connection
- **User-Friendly Feedback**: Provides clear, color-coded status messages during the connection process

## Prerequisites

- AWS CLI installed and configured with appropriate permissions
- `jq` command-line JSON processor
- An EC2 instance running VS Code Server on port 8080
- SSH key pair for EC2 authentication
- A running VS Code Server on AWS EC2; I used: https://github.com/coder/deploy-code-server/blob/main/guides/aws-ec2.md as a reference

## Installation

1. Clone this repository:
   ```
   git clone https://github.com/yourusername/ec2utility_script.git
   cd ec2utility_script
   ```

2. Make the script executable:
   ```
   chmod +x launch_vscode_server.sh
   ```

3. Update the configuration variables in the script:
   - `INSTANCE_ID`: Your EC2 instance ID
   - `EC2_USER`: The username for SSH connection (typically "ubuntu" or "ec2-user")
   - `KEY_PATH`: Path to your SSH private key
   - `SECURITY_GROUP_ID`: The security group ID associated with your EC2 instance
   - `AWS_REGION`: The AWS region where your instance is running

## Usage

Simply run the script:

```
./launch_vscode_server.sh
```

The script will:
1. Get your current public IP address
2. Update the EC2 security group if your IP has changed
3. Establish an SSH tunnel to the VS Code Server
4. Provide the URL to access VS Code Server in your browser

## Security Considerations

This script implements several security best practices:

- Restricts SSH access to only your current IP address
- Uses SSH key authentication instead of passwords
- Creates an encrypted tunnel for all VS Code Server traffic
- Avoids exposing the VS Code Server directly to the internet

## Troubleshooting

If you encounter issues:

1. Ensure your EC2 instance is running
2. Verify your AWS CLI is properly configured
3. Check that your SSH key has the correct permissions (600)
4. Confirm that VS Code Server is running on port 8080 on the EC2 instance

## License

MIT

## Contributing

Contributions are welcome! Please feel free to submit a Pull Request.
