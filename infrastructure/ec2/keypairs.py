import pulumi
import pulumi_aws as aws
from typing import Optional, Dict, Tuple
import os
import stat
import tempfile
import subprocess

def ensure_keypair(
    name: str,
    save_path: Optional[str] = None,
    tags: Optional[Dict[str, str]] = None,
    force_overwrite: bool = False
) -> Tuple[pulumi.Output[str], str]:
    """
    Ensures that a key pair exists with the given name. 
    If the key pair doesn't exist, it creates it.
    This automatically handles the region through Pulumi configuration.
    
    Args:
        name: Name of the key pair
        save_path: Path to save the generated private key. 
                  If None, defaults to ~/.ssh/{name}.pem
        tags: Optional tags to apply to the key pair
        force_overwrite: Whether to overwrite an existing key file
                  
    Returns:
        Tuple[pulumi.Output[str], str]: The key name and the path to the private key file
    """
    # Default save path if not specified
    if not save_path:
        home_dir = os.path.expanduser("~")
        ssh_dir = os.path.join(home_dir, ".ssh")
        if not os.path.exists(ssh_dir):
            os.makedirs(ssh_dir)
        save_path = os.path.join(ssh_dir, f"{name}.pem")
    
    # Check if the key file exists
    if os.path.exists(save_path):
        if not force_overwrite:
            print(f"Key file {save_path} already exists. Using existing key file.")
            # Create the key pair in AWS - reusing the existing key file
            try:
                keypair = aws.ec2.get_key_pair(key_name=name)
                print(f"Key pair '{name}' already exists in AWS. Using existing key pair.")
                return pulumi.Output.from_input(name), save_path
            except Exception:
                # Get the public key from the existing private key
                tmp_pub_key = tempfile.mktemp()
                try:
                    subprocess.run(
                        ["ssh-keygen", "-y", "-f", save_path],
                        stdout=open(tmp_pub_key, "w"),
                        check=True
                    )
                    with open(tmp_pub_key, "r") as f:
                        public_key_content = f.read().strip()
                    
                    # Create the key pair in AWS with the existing public key
                    keypair = aws.ec2.KeyPair(
                        name,
                        key_name=name,
                        public_key=public_key_content,
                        tags=tags or {},
                    )
                    os.unlink(tmp_pub_key)
                    return keypair.key_name, save_path
                except Exception as e:
                    print(f"Error extracting public key from {save_path}: {e}")
                    # Fall through to create a new key pair
            
    # First, generate a key pair locally
    tmp_key_dir = tempfile.mkdtemp()
    tmp_key_file = os.path.join(tmp_key_dir, "temp_key")
    tmp_key_pub_file = f"{tmp_key_file}.pub"
    
    subprocess.run(["ssh-keygen", "-t", "rsa", "-b", "2048", "-N", "", "-f", tmp_key_file], check=True)
    
    # Read the public key
    with open(tmp_key_pub_file, "r") as f:
        public_key_content = f.read().strip()
    
    # Read the private key
    with open(tmp_key_file, "r") as f:
        private_key_content = f.read()
    
    # If the save_path file exists, we need to make it writable
    if os.path.exists(save_path):
        os.chmod(save_path, stat.S_IRUSR | stat.S_IWUSR)
    
    # Write the private key to the save path
    with open(save_path, "w") as f:
        f.write(private_key_content)
    
    # Set correct permissions
    os.chmod(save_path, stat.S_IRUSR | stat.S_IWUSR)
    
    # Clean up the temporary files
    os.unlink(tmp_key_file)
    os.unlink(tmp_key_pub_file)
    os.rmdir(tmp_key_dir)
    
    # Create the key pair in AWS
    keypair = aws.ec2.KeyPair(
        name,
        key_name=name,
        public_key=public_key_content,
        tags=tags or {},
    )
    
    print(f"Created key pair '{name}' and saved private key to '{save_path}'")
    
    return keypair.key_name, save_path

def get_keypair(
    name: str,
) -> aws.ec2.GetKeyPairResult:
    """
    Get an existing key pair by name.
    
    Args:
        name: Name of the key pair to get
        
    Returns:
        aws.ec2.GetKeyPairResult: The key pair resource if it exists
    """
    # Look up the existing key pair
    try:
        return aws.ec2.get_key_pair(key_name=name)
    except Exception:
        # Key doesn't exist
        return None 