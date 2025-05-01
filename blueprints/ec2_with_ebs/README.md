# EC2 with EBS Blueprint

This blueprint provides a production-ready infrastructure pattern for deploying:
- A properly configured VPC and networking infrastructure
- An EC2 instance with correct security settings
- An attached EBS volume for additional storage
- Security group configured with your local machine's IP address for secure access

## Architecture

```
┌────────────────────────────────────────────────┐
│                      VPC                       │
│  ┌─────────────────────────────────────────┐  │
│  │               Public Subnet             │  │
│  │  ┌───────────┐        ┌──────────────┐  │  │
│  │  │           │        │              │  │  │
│  │  │    EC2    │━━━━━━━━│ EBS Volume   │  │  │
│  │  │           │        │              │  │  │
│  │  └───────────┘        └──────────────┘  │  │
│  │         │                                │  │
│  │         ▼                                │  │
│  │  ┌───────────┐                           │  │
│  │  │ Security  │ Allow SSH from your IP    │  │
│  │  │  Group    │ Allow HTTP/HTTPS from all │  │
│  │  └───────────┘                           │  │
│  └─────────────────────────────────────────┘  │
│                       │                        │
│                       ▼                        │
│  ┌─────────────────────────────────────────┐  │
│  │          Internet Gateway               │  │
└──┴─────────────────────────────────────────┴──┘
                       │
                       ▼
                    Internet
```

## Features

- **Automatic IP Detection**: Automatically detects your local machine's IP address and configures the security group to only allow SSH access from your IP.
- **Complete Infrastructure**: Creates all necessary components (VPC, subnet, route tables, etc.) for a production-ready deployment.
- **EBS Storage**: Includes additional EBS storage attached to your instance.
- **Security Best Practices**: Implements security group rules following best practices.

## Prerequisites

1. Install Python 3.8+
2. Install Pulumi CLI: https://www.pulumi.com/docs/install/
3. AWS CLI configured with credentials: `aws configure`

## Quick Start

Run the deployment script with automatic SSH key creation:

```bash
./deploy.sh --create-key
```

This will:
1. Check for required tools
2. Create an SSH key pair in AWS (if needed)
3. Set up a Python virtual environment
4. Install dependencies
5. Initialize a Pulumi stack
6. Deploy the infrastructure
7. Show the instance's public IP address

## Command Options

The deployment script supports these options:

```bash
# Create a key if needed and deploy
./deploy.sh --create-key

# Specify a region
./deploy.sh --region us-east-1

# Clean up all resources
./deploy.sh --destroy

# Show help
./deploy.sh --help
```

## Customization

You can customize the deployment by editing the `__main__.py` file:

- Change instance type: `CONFIG["instance_type"]`
- Modify EBS volume size: `CONFIG["ebs_size"]`
- Change CIDR ranges for VPC and subnet
- Add additional security group rules
- Modify user data script for instance initialization

## Accessing the Instance

After deployment completes, you can connect to your instance using SSH:

```bash
ssh -i ~/.ssh/demo-key.pem ubuntu@<public_ip>
```

Where `<public_ip>` is the output from the deployment script.

## Storage Setup

The EBS volume is attached to the instance but not formatted or mounted. After connecting to your instance:

1. Check the volume:
   ```bash
   lsblk
   ```

2. Format the volume (first time only):
   ```bash
   sudo mkfs -t ext4 /dev/nvme1n1  # Device name may vary
   ```

3. Create a mount point and mount:
   ```bash
   sudo mkdir /data
   sudo mount /dev/nvme1n1 /data
   ```

4. For persistent mounting, add to /etc/fstab:
   ```bash
   sudo bash -c 'echo "/dev/nvme1n1 /data ext4 defaults,nofail 0 2" >> /etc/fstab'
   ```

## Cleanup

When you're done, destroy the resources:
```bash
./deploy.sh --destroy
``` 