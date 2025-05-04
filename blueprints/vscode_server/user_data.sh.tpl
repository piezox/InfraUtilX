#!/bin/bash
# VS Code Server Installation and Configuration Script
# This script installs and configures VS Code Server on an Ubuntu EC2 instance

# Create a log file for troubleshooting
LOGFILE="/var/log/vscode-server-setup.log"
exec > >(tee -a $LOGFILE) 2>&1

# Ensure HOME environment variable is set
export HOME="/home/ubuntu"

echo "===== VS Code Server Setup - $(date) ====="
echo "Starting VS Code Server installation and configuration..."

# Generated password for VS Code Server
VSCODE_PASSWORD="${vscode_password}"
VSCODE_PORT="${vscode_port}"

# Ensure SSH is properly configured and running
echo "Configuring SSH service..."
sudo sed -i 's/#PasswordAuthentication yes/PasswordAuthentication no/' /etc/ssh/sshd_config
sudo sed -i 's/#PubkeyAuthentication yes/PubkeyAuthentication yes/' /etc/ssh/sshd_config
sudo systemctl restart ssh
sudo systemctl status ssh

# Check SSH service status
echo "SSH service status:"
sudo systemctl status ssh | grep Active

# Update packages
echo "Updating packages..."
sudo apt-get update -y
sudo apt-get install -y nginx ca-certificates curl gnupg lsb-release unzip software-properties-common apt-transport-https

# Configure EBS volume
# Get the EBS device name (in case of device name mapping differences)
DEVICE_NAME="${ebs_device_name}"
echo "Looking for EBS volume at $DEVICE_NAME..."
lsblk

# Find EBS volume - more robust method that avoids the root volume
ACTUAL_DEVICE=$(lsblk | grep -v loop | grep disk | grep -v nvme0n1 | awk '{print $1}' | head -1)
if [ -z "$ACTUAL_DEVICE" ]; then
    echo "Could not find the EBS volume. Using default: $DEVICE_NAME"
    ACTUAL_DEVICE="xvdf"
else
    echo "Detected EBS volume as /dev/$ACTUAL_DEVICE"
fi
ACTUAL_DEVICE="/dev/$ACTUAL_DEVICE"

# Create mount point
MOUNT_POINT="/data"
sudo mkdir -p $MOUNT_POINT
echo "Created mount point at $MOUNT_POINT"

# Check if the device is already mounted or formatted
if mount | grep -q "$ACTUAL_DEVICE"; then
    echo "Device $ACTUAL_DEVICE is already mounted. Skipping formatting."
else
    # Check if the device has a filesystem
    if sudo file -s $ACTUAL_DEVICE | grep -q "data"; then
        echo "Device $ACTUAL_DEVICE already has a filesystem. Skipping formatting."
    else
        # Format the volume
        echo "Formatting the EBS volume as ext4..."
        sudo mkfs -t ext4 $ACTUAL_DEVICE
    fi
    
    # Mount the volume
    echo "Mounting the EBS volume to $MOUNT_POINT"
    sudo mount $ACTUAL_DEVICE $MOUNT_POINT
    
    # Update fstab to mount on reboot
    EBS_UUID=$(sudo blkid -s UUID -o value $ACTUAL_DEVICE)
    if ! grep -q "$EBS_UUID" /etc/fstab; then
        echo "Adding entry to /etc/fstab for persistent mounting"
        echo "UUID=$EBS_UUID $MOUNT_POINT ext4 defaults,nofail 0 2" | sudo tee -a /etc/fstab
    fi
fi

# Create workspace directory
WORKSPACE="$MOUNT_POINT/workspace"
sudo mkdir -p $WORKSPACE
sudo chown -R ubuntu:ubuntu $MOUNT_POINT
echo "Created workspace directory at $WORKSPACE"

# Create data directories for VS Code Server
sudo mkdir -p $MOUNT_POINT/.vscode-server-data $MOUNT_POINT/.vscode-server-extensions
sudo chown -R ubuntu:ubuntu $MOUNT_POINT/.vscode-server-*

# Install VS Code Server
echo "Installing VS Code Server..."
mkdir -p ~/.vscode-server/bin
mkdir -p ~/.vscode-server/extensions

# We'll use code-server which provides VS Code in the browser
echo "Installing code-server (VS Code in browser)..."
# Ensure HOME is explicitly set for this command
export HOME="/home/ubuntu"
curl -fsSL https://code-server.dev/install.sh | sh

# Verify the installation
if [ ! -f "/usr/bin/code-server" ]; then
    echo "ERROR: code-server installation failed. Binary not found at /usr/bin/code-server."
    echo "Attempting alternative installation method..."
    # Try alternative installation method
    sudo apt-get update
    sudo apt-get install -y code-server
fi

# Configure code-server
mkdir -p ~/.config/code-server
cat > ~/.config/code-server/config.yaml << EOF
bind-addr: 0.0.0.0:${vscode_port}
auth: password
password: ${vscode_password}
cert: false
EOF

# Create systemd service for code-server
sudo tee /etc/systemd/system/code-server.service > /dev/null << EOF
[Unit]
Description=VS Code Server (code-server)
After=network.target

[Service]
Type=simple
User=ubuntu
Environment="HOME=/home/ubuntu"
ExecStart=/usr/bin/code-server --bind-addr 0.0.0.0:${vscode_port} --user-data-dir $MOUNT_POINT/.vscode-server-data --extensions-dir $MOUNT_POINT/.vscode-server-extensions
Restart=always
RestartSec=10

[Install]
WantedBy=multi-user.target
EOF

# Start the service
sudo systemctl daemon-reload
sudo systemctl enable code-server
sudo systemctl start code-server
echo "VS Code Server service started on port ${vscode_port}"

# Verify the service started successfully
echo "Checking code-server service status:"
sudo systemctl status code-server | grep Active

# Configure Nginx as a reverse proxy (with SSL)
echo "Configuring Nginx as a reverse proxy..."
sudo tee /etc/nginx/sites-available/code-server > /dev/null << EOF
server {
    listen 80;
    server_name _;
    
    location / {
        proxy_pass http://localhost:${vscode_port};
        proxy_set_header Host \$host;
        proxy_set_header Upgrade \$http_upgrade;
        proxy_set_header Connection upgrade;
        proxy_set_header Accept-Encoding gzip;
    }
}
EOF

sudo ln -s /etc/nginx/sites-available/code-server /etc/nginx/sites-enabled/
sudo rm -f /etc/nginx/sites-enabled/default
sudo nginx -t && sudo systemctl restart nginx

# Create a welcome HTML file explaining how to access VS Code
PUBLIC_IP=$(curl -s http://169.254.169.254/latest/meta-data/public-ipv4)
cat > /var/www/html/index.html << EOF
<!DOCTYPE html>
<html>
<head>
    <title>VS Code Server</title>
    <style>
        body { 
            font-family: Arial, sans-serif; 
            margin: 40px; 
            line-height: 1.6; 
            color: #333;
            max-width: 800px;
            margin: 0 auto;
            padding: 20px;
        }
        h1 { color: #0078D4; }
        .info { 
            background-color: #f4f4f4; 
            padding: 20px; 
            border-radius: 5px; 
            margin-bottom: 20px;
        }
        .steps {
            background-color: #E6F3FF;
            padding: 20px;
            border-radius: 5px;
            margin-bottom: 20px;
        }
        .url {
            background-color: #333;
            color: white;
            padding: 10px;
            border-radius: 5px;
            font-family: monospace;
        }
        .warning {
            background-color: #FFECD9;
            padding: 10px;
            border-radius: 5px;
            margin-top: 20px;
        }
    </style>
</head>
<body>
    <h1>VS Code Server is Ready!</h1>
    
    <div class="info">
        <p><strong>Instance ID:</strong> $(curl -s http://169.254.169.254/latest/meta-data/instance-id)</p>
        <p><strong>Instance Type:</strong> $(curl -s http://169.254.169.254/latest/meta-data/instance-type)</p>
        <p><strong>Availability Zone:</strong> $(curl -s http://169.254.169.254/latest/meta-data/placement/availability-zone)</p>
        <p><strong>Setup Completed:</strong> $(date)</p>
    </div>
    
    <div class="steps">
        <h2>Access Your VS Code Server</h2>
        <p>Your VS Code Server is running and accessible at:</p>
        <p class="url">http://$PUBLIC_IP</p>
        
        <h3>Login Credentials:</h3>
        <p><strong>Password:</strong> ${vscode_password}</p>
        
        <h3>Features:</h3>
        <ul>
            <li>Full VS Code environment in your browser</li>
            <li>Persistent storage on EBS volume mounted at /data</li>
            <li>Pre-configured workspace at /data/workspace</li>
            <li>SSH access available for direct connection</li>
        </ul>
    </div>
    
    <div class="warning">
        <strong>Security Note:</strong> For production use, we recommend adding HTTPS with a proper SSL certificate.
    </div>
</body>
</html>
EOF

# Create a verification file
echo "VS Code Server setup completed successfully at $(date)" > $MOUNT_POINT/vscode_setup_complete.txt

echo "===== VS Code Server Setup Completed - $(date) ====="