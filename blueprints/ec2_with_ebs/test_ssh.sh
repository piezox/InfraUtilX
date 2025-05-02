#!/bin/bash

# SSH Connectivity Test Script for InfraUtilX EC2 with EBS Blueprint
# This script tests SSH connectivity to the deployed EC2 instance

set -e

# Process command line arguments
TIMEOUT=5
VERBOSE=false
MAX_ATTEMPTS=3

show_help() {
  echo "InfraUtilX - SSH Connectivity Test"
  echo ""
  echo "Usage: ./test_ssh.sh [options]"
  echo ""
  echo "Options:"
  echo "  --timeout N     SSH connection timeout in seconds (default: 5)"
  echo "  --attempts N    Maximum number of connection attempts (default: 3)"
  echo "  --verbose       Show verbose output"
  echo "  --help          Show this help message"
  echo ""
  exit 0
}

while [[ "$#" -gt 0 ]]; do
  case $1 in
    --timeout) TIMEOUT="$2"; shift 2 ;;
    --attempts) MAX_ATTEMPTS="$2"; shift 2 ;;
    --verbose) VERBOSE=true; shift ;;
    --help) show_help ;;
    *) echo "Unknown parameter: $1"; exit 1 ;;
  esac
done

# Go to the blueprint directory
THIS_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$THIS_DIR"

# Check if Pulumi is installed
command -v pulumi >/dev/null 2>&1 || { echo "Pulumi is required but not installed. Aborting."; exit 1; }

# Get instance information from Pulumi stack
echo "Getting instance information from Pulumi stack..."
PUBLIC_IP=$(pulumi stack output public_ip)
KEY_NAME=$(pulumi stack output key_name)
KEY_PATH=$(pulumi stack output key_path)

if [ -z "$PUBLIC_IP" ]; then
  echo "Error: Could not get public IP from Pulumi stack."
  echo "Make sure the stack is deployed and has a 'public_ip' output."
  exit 1
fi

if [ -z "$KEY_PATH" ]; then
  echo "Error: Could not get SSH key path from Pulumi stack."
  echo "Make sure the stack is deployed and has a 'key_path' output."
  exit 1
fi

echo "Instance public IP: $PUBLIC_IP"
echo "SSH key path: $KEY_PATH"

# Test basic connectivity with ping
echo "Testing basic connectivity with ping..."
if ping -c 3 -W 5 "$PUBLIC_IP" > /dev/null 2>&1; then
  echo "✅ Ping successful - instance is reachable"
else
  echo "❌ Ping failed - instance is not responding to ICMP"
  echo "This could be due to a firewall blocking ICMP or the instance is not running."
  echo "Continuing with SSH test anyway..."
fi

# Test SSH connectivity
echo "Testing SSH connectivity..."
SSH_OPTS="-o StrictHostKeyChecking=no -o UserKnownHostsFile=/dev/null -o ConnectTimeout=$TIMEOUT -o BatchMode=yes"

if [ "$VERBOSE" = true ]; then
  SSH_OPTS="$SSH_OPTS -v"
fi

success=false
for ((i=1; i<=MAX_ATTEMPTS; i++)); do
  echo "Attempt $i of $MAX_ATTEMPTS..."
  
  if ssh $SSH_OPTS -i "$KEY_PATH" ubuntu@"$PUBLIC_IP" "echo 'SSH connection successful'"; then
    echo "✅ SSH connection successful!"
    success=true
    break
  else
    echo "❌ SSH connection failed on attempt $i"
    if [ "$i" -lt "$MAX_ATTEMPTS" ]; then
      echo "Waiting 5 seconds before next attempt..."
      sleep 5
    fi
  fi
done

if [ "$success" = false ]; then
  echo ""
  echo "===== SSH CONNECTION TROUBLESHOOTING ====="
  echo ""
  echo "SSH connection failed after $MAX_ATTEMPTS attempts. Here are some troubleshooting steps:"
  echo ""
  echo "1. Verify Security Group Configuration:"
  echo "   - Check that port 22 is open in the security group"
  echo "   - Verify your current IP address is allowed in the security group"
  echo "   - Current security group ID: $(pulumi stack output security_group_id)"
  echo ""
  echo "2. Check Network Configuration:"
  echo "   - Verify the subnet has a route to the internet gateway"
  echo "   - Check that the instance has a public IP address"
  echo "   - Subnet ID: $(pulumi stack output subnet_id)"
  echo ""
  echo "3. Verify Instance State:"
  echo "   - Check that the instance is running"
  echo "   - Instance ID: $(pulumi stack output instance_id)"
  echo ""
  echo "4. Check SSH Key:"
  echo "   - Verify the SSH key exists at $KEY_PATH"
  echo "   - Check permissions: chmod 400 $KEY_PATH"
  echo ""
  echo "5. Check Instance Logs:"
  echo "   - Connect to the AWS Console and check the instance system log"
  echo "   - Look for any SSH service errors"
  echo ""
  echo "6. Try Manual SSH Connection with Verbose Output:"
  echo "   ssh -v -i \"$KEY_PATH\" ubuntu@$PUBLIC_IP"
  echo ""
  echo "7. Try connecting to the instance using the AWS Systems Manager Session Manager"
  echo ""
  echo "8. If all else fails, try redeploying with a different AMI or instance type"
  echo ""
  exit 1
else
  echo ""
  echo "===== ADDITIONAL INSTANCE INFORMATION ====="
  echo ""
  echo "Checking instance system information..."
  
  # Get system information
  ssh $SSH_OPTS -i "$KEY_PATH" ubuntu@"$PUBLIC_IP" "
    echo '- Hostname: \$(hostname)'
    echo '- Uptime: \$(uptime)'
    echo '- SSH Service Status: \$(systemctl status ssh | grep Active)'
    echo '- Kernel: \$(uname -r)'
    echo '- CPU Info: \$(grep 'model name' /proc/cpuinfo | head -1)'
    echo '- Memory: \$(free -h | grep Mem)'
    echo '- Disk Space: \$(df -h | grep -E \"^/dev|Filesystem\")'
    echo '- EBS Mount: \$(df -h | grep /data)'
    echo '- Network Interfaces: \$(ip -br addr)'
    echo '- Default Route: \$(ip route | grep default)'
    echo '- Startup Log: \$(tail -n 10 /var/log/infrautilx-startup.log)'
  "
  
  echo ""
  echo "✅ All tests completed successfully!"
  echo ""
  echo "You can connect to the instance with:"
  echo "ssh -i \"$KEY_PATH\" ubuntu@$PUBLIC_IP"
  echo ""
  echo "You can also access the web server at:"
  echo "http://$PUBLIC_IP/"
  echo ""
fi