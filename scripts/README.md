# InfraUtilX Scripts

This directory contains utility scripts for managing infrastructure resources.

## Script Overview

### AWS Access Management

- **manage_access.py**: Manages access to your deployed infrastructure when your IP changes
  ```bash
  ./scripts/manage_access.py list    # List all stacks
  ./scripts/manage_access.py check   # Check if your IP has access
  ./scripts/manage_access.py update  # Update security group with your IP
  ```

### AWS Profile Management

- **manage_profiles.py**: Manages AWS profiles and credentials
  ```bash
  ./scripts/manage_profiles.py list          # List all profiles
  ./scripts/manage_profiles.py current       # Show current profile
  ./scripts/manage_profiles.py switch PROFILE # Switch to profile
  ./scripts/manage_profiles.py validate      # Validate credentials
  ./scripts/manage_profiles.py refresh-sso PROFILE  # Refresh SSO creds
  ```

## AWS Profile Management Details

The `manage_profiles.py` utility helps you manage your AWS profiles and credentials using Pulumi's AWS provider system. It provides several commands for working with AWS profiles.

### Commands

#### List Profiles

List all available AWS profiles configured on your system:

```bash
./scripts/manage_profiles.py list
```

This will show all profiles from your AWS config and credentials files, indicating the active profile, regions, and whether profiles use SSO.

#### Check Current Profile

Show the currently active AWS profile:

```bash
./scripts/manage_profiles.py current
```

#### Switch Profile

Switch to a different AWS profile:

```bash
./scripts/manage_profiles.py switch profile_name
```

Note that this only affects the Python script's process. To use the profile in your shell, run the exported command or set `AWS_PROFILE` in your shell.

#### Validate Profile Credentials

Validate that AWS credentials for a profile are valid:

```bash
./scripts/manage_profiles.py validate --profile profile_name
```

If no profile is specified, it validates the current profile.

#### Refresh SSO Credentials

For SSO profiles, refresh the SSO credentials:

```bash
./scripts/manage_profiles.py refresh-sso profile_name
```

This initiates the AWS SSO login process for the specified profile.

#### Shell Helper Functions

Display helper functions to add to your shell configuration:

```bash
./scripts/manage_profiles.py shell-helpers
```

Add these functions to your `~/.bashrc` or `~/.zshrc` to make working with profiles easier.

### Shell Integration

To make the profile management utilities more convenient, add the shell helper function to your `.bashrc` or `.zshrc`:

```bash
# Get the shell helper
./scripts/manage_profiles.py shell-helpers >> ~/.zshrc

# Then source your shell config
source ~/.zshrc  # or ~/.bashrc
```

This adds a unified `awsp` command that lets you manage AWS profiles with a Git-like command structure:

```bash
# Show help information
awsp help                 # or simply awsp

# List all profiles
awsp ls                   # or awsp list

# Show current profile
awsp current

# Switch to a profile
awsp switch profile_name  # or awsp use profile_name

# Validate profile credentials
awsp validate [profile_name]

# Refresh SSO credentials
awsp sso profile_name
```

**Features:**
- Single command with logical subcommands
- Tab completion for both commands and profile names
- Proper handling of shell environment variables
- Unified help system
- Intuitive command structure similar to Git and Docker CLI

**Examples:**

```bash
# List profiles and see which one is active
awsp ls

# List all profiles with their AWS account IDs
awsp ls -a

# Switch between profiles
awsp switch dev
awsp use prod

# Refresh SSO credentials
awsp sso admin-sso
```

All commands have tab completion support, making it easy to work with multiple profiles.

## Adding New Scripts

When adding new scripts to this directory, please follow these guidelines:

1. Use Python for consistency with other scripts
2. Include a descriptive header and help text
3. Update this README with details about your script
4. Follow the existing patterns for command-line arguments

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