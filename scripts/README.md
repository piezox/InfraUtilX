# InfraUtilX Scripts

This directory contains utility scripts for working with InfraUtilX deployments.

## Manage Access Script

The `manage_access.py` script provides a command-line interface for managing access to InfraUtilX stacks, including listing stacks, checking access, and updating security group rules.

## Pulumi Security Group Update Script

The `update_sg.py` script provides a way to update security groups with your current IP address using Pulumi's Python SDK directly, without requiring a full Pulumi project setup.

### Prerequisites

Before using these scripts, make sure you have:

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
./manage_access.py list

# List stacks for a specific project
./manage_access.py list --project infrautilx-example

# Check if your current IP has access to all stacks
./manage_access.py check

# Check if your current IP has access to a specific stack
./manage_access.py check --stack dev/infrautilx-example

# Update a security group to allow access from your current IP
./manage_access.py update dev/infrautilx-example

# Alternative: Update a specific security group directly
./update_sg.py --sg-id sg-0123456789abcdef0

# Alternative: Update security group from a stack
./update_sg.py --stack dev/infrautilx-example
```

### Commands

#### Manage Access Script

- `list`: List all Pulumi stacks created with InfraUtilX
  - `--project`: Filter stacks by project name
  - `--json`: Output in JSON format

- `check`: Check if your current IP has access to security groups in the stacks
  - `--stack`: Check a specific stack
  - `--project`: Filter stacks by project name
  - `--json`: Output in JSON format

- `update`: Update security group rules to allow access from your current IP
  - Requires a stack name argument

#### Update SG Script

- `--sg-id`: Security group ID to update
- `--stack`: Pulumi stack name to get security group ID from
- `--port`: Port to allow access to (default: 22)
- `--protocol`: Protocol to allow (default: tcp)

### Examples

#### Checking Access Status

```bash
$ ./manage_access.py check

Current IP: 203.0.113.42/32

Access status for 2 stacks:

1. dev/infrautilx-example - ❌ DENIED
   Security Group: sg-0123456789abcdef0
   Authorized IPs for SSH:
     - 198.51.100.17/32

2. dev/another-example - ✅ ALLOWED
   Security Group: sg-0123456789abcdef1
   Authorized IPs for SSH:
     - 203.0.113.42/32 (current)
     - 198.51.100.17/32
```

#### Updating Access

```bash
$ ./manage_access.py update dev/infrautilx-example
Successfully updated security group in stack dev/infrautilx-example to allow access from your current IP.
```

### Troubleshooting

If you encounter errors:

1. **Pulumi not found**: Make sure Pulumi CLI is installed and in your PATH
2. **Authentication errors**: Run `pulumi login` to authenticate with Pulumi
3. **Permission errors**: Make sure your AWS user has permissions to modify security groups
4. **Stack not found**: Check the stack name with `pulumi stack ls --all`
5. **Security group not found**: Make sure your stack exports a 'security_group_id' output

## How It Works

The scripts use the Pulumi CLI and Pulumi Python SDK to:

1. List all Pulumi stacks in your account
2. Extract stack outputs including security group IDs
3. Check security group rules to determine if your current IP has access
4. Create temporary Pulumi programs to update security group rules when needed

This approach maintains the Pulumi abstraction layer while providing a convenient way to manage access to your infrastructure.