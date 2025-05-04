#!/usr/bin/env python3
"""
AWS Profile Manager CLI

A command-line utility for managing AWS profiles with Pulumi integration.
This tool helps you list, validate, and switch between AWS profiles.
"""

import argparse
import os
import sys
import textwrap
from pathlib import Path

# Add the parent directory to sys.path to import from infrastructure
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from infrastructure.aws_profiles import (
    list_profiles, 
    get_current_profile, 
    switch_profile, 
    validate_profile,
    refresh_sso_credentials,
    ProfileInfo
)

def format_profile_list(profiles):
    """Format profiles for display."""
    if not profiles:
        return "No AWS profiles found."
    
    output = []
    for p in profiles:
        marker = "→ " if p.is_active else "  "
        output.append(f"{marker}{p}")
    
    return "\n".join(output)

def handle_list(args):
    """Handle the list command."""
    profiles = list_profiles(fetch_all_account_ids=args.all_accounts)
    print("AWS Profiles:")
    print(format_profile_list(profiles))
    
    # Print the current profile
    current = get_current_profile()
    if current:
        print(f"\nActive profile: {current}")
    else:
        print("\nNo profile explicitly set (using default)")

def handle_current(args):
    """Handle the current command."""
    current = get_current_profile()
    if current:
        print(f"Current AWS profile: {current}")
    else:
        print("No AWS profile explicitly set (using default)")

def handle_switch(args):
    """Handle the switch command."""
    profile_name = args.profile
    if switch_profile(profile_name):
        print(f"Switched to profile: {profile_name}")
        print(f"\nTo use this profile in your shell, run:")
        print(f"  export AWS_PROFILE={profile_name}")
    else:
        print(f"Error: Profile '{profile_name}' not found")
        sys.exit(1)

def handle_validate(args):
    """Handle the validate command."""
    profile_name = args.profile
    success, message = validate_profile(profile_name)
    
    if success:
        print(f"✅ {message}")
    else:
        print(f"❌ {message}")
        sys.exit(1)

def handle_refresh_sso(args):
    """Handle the refresh-sso command."""
    profile_name = args.profile
    success, message = refresh_sso_credentials(profile_name)
    
    if success:
        print(f"✅ {message}")
    else:
        print(f"❌ {message}")
        sys.exit(1)

def handle_shell_helpers(args):
    """Display shell helper functions."""
    helpers = textwrap.dedent("""
    # AWS Profile Management Helper Function
    # Add this to your ~/.bashrc or ~/.zshrc
    
    # Unified AWS profile management command
    awsp() {
        # Show help if requested
        if [ "$1" = "--help" ] || [ "$1" = "-h" ] || [ "$1" = "help" ] || [ "$#" -eq 0 ]; then
            echo "AWS Profile Manager - Manage your AWS profiles"
            echo ""
            echo "Usage: awsp <command> [options]"
            echo ""
            echo "Commands:"
            echo "  ls, list            List all AWS profiles"
            echo "    -a, --all         Show account IDs for all profiles (can be slow)"
            echo "  current             Show current profile"
            echo "  switch <profile>    Switch to specified profile"
            echo "  use <profile>       Alias for switch"
            echo "  validate [profile]  Validate profile credentials"
            echo "  sso <profile>       Refresh SSO credentials for profile"
            echo "  help                Show this help message"
            echo ""
            echo "Examples:"
            echo "  awsp ls             # List all profiles"
            echo "  awsp ls -a          # List all profiles with account IDs"
            echo "  awsp switch dev     # Switch to dev profile"
            echo "  awsp use prod       # Switch to prod profile"
            echo "  awsp sso admin      # Refresh SSO credentials for admin profile"
            return
        fi
        
        # Process commands
        case "$1" in
            ls|list)
                # Check for -a or --all flag
                if [ "$2" = "-a" ] || [ "$2" = "--all" ]; then
                    python3 PATH_TO_SCRIPT/manage_profiles.py list --all-accounts
                else
                    python3 PATH_TO_SCRIPT/manage_profiles.py list
                fi
                ;;
                
            current)
                python3 PATH_TO_SCRIPT/manage_profiles.py current
                ;;
                
            switch|use)
                if [ -z "$2" ]; then
                    echo "Error: Profile name required"
                    echo "Usage: awsp switch <profile_name>"
                    return 1
                fi
                
                # Execute the switch command
                python3 PATH_TO_SCRIPT/manage_profiles.py switch "$2" > /tmp/awsp_result
                if [ $? -ne 0 ]; then
                    cat /tmp/awsp_result
                    rm -f /tmp/awsp_result
                    return 1
                fi
                
                # Extract and execute the export command
                export AWS_PROFILE="$2"
                echo "AWS Profile set to: $AWS_PROFILE"
                rm -f /tmp/awsp_result
                ;;
                
            validate)
                if [ -z "$2" ]; then
                    python3 PATH_TO_SCRIPT/manage_profiles.py validate
                else
                    python3 PATH_TO_SCRIPT/manage_profiles.py validate --profile "$2"
                fi
                ;;
                
            sso)
                if [ -z "$2" ]; then
                    echo "Error: Profile name required"
                    echo "Usage: awsp sso <profile_name>"
                    return 1
                fi
                
                python3 PATH_TO_SCRIPT/manage_profiles.py refresh-sso "$2"
                ;;
                
            *)
                echo "Error: Unknown command '$1'"
                echo "Run 'awsp help' for usage information"
                return 1
                ;;
        esac
    }
    
    # Get shell completion
    _awsp_completion() {
        local cur prev
        cur="${COMP_WORDS[COMP_CWORD]}"
        prev="${COMP_WORDS[COMP_CWORD-1]}"
        
        # Complete subcommands
        if [ "$COMP_CWORD" -eq 1 ]; then
            COMPREPLY=( $(compgen -W "ls list current switch use validate sso help" -- "$cur") )
            return 0
        fi
        
        # Complete flags for ls command
        if [ "$prev" = "ls" ] || [ "$prev" = "list" ]; then
            COMPREPLY=( $(compgen -W "-a --all" -- "$cur") )
            return 0
        fi
        
        # Complete profile names for commands that need profiles
        if [[ "$prev" = "switch" || "$prev" = "use" || "$prev" = "validate" || "$prev" = "sso" ]]; then
            COMPREPLY=( $(compgen -W "$(grep '\\[.*\\]' ~/.aws/config 2>/dev/null | sed -e 's/\\[profile \\(.*\\)]/\\1/' -e 's/\\[\\(default\\)]/\\1/')" -- "$cur") )
            return 0
        fi
    }
    complete -F _awsp_completion awsp
    """)
    
    # Replace PATH_TO_SCRIPT with the actual path
    script_path = Path(__file__).resolve().parent
    helpers = helpers.replace("PATH_TO_SCRIPT", str(script_path))
    
    print(helpers)

def main():
    parser = argparse.ArgumentParser(
        description="AWS Profile Manager - Manage your AWS profiles with Pulumi integration"
    )
    subparsers = parser.add_subparsers(dest="command", help="Command to run")
    
    # List command
    list_parser = subparsers.add_parser("list", help="List all AWS profiles")
    list_parser.add_argument("--all-accounts", "-a", action="store_true", 
                        help="Fetch account IDs for all profiles (can be slow)")
    list_parser.set_defaults(func=handle_list)
    
    # Current command
    current_parser = subparsers.add_parser("current", help="Show current AWS profile")
    current_parser.set_defaults(func=handle_current)
    
    # Switch command
    switch_parser = subparsers.add_parser("switch", help="Switch to a different AWS profile")
    switch_parser.add_argument("profile", help="Profile name to switch to")
    switch_parser.set_defaults(func=handle_switch)
    
    # Validate command
    validate_parser = subparsers.add_parser("validate", help="Validate AWS credentials for a profile")
    validate_parser.add_argument("--profile", help="Profile to validate (uses current if not specified)")
    validate_parser.set_defaults(func=handle_validate)
    
    # Refresh SSO command
    sso_parser = subparsers.add_parser("refresh-sso", help="Refresh SSO credentials for a profile")
    sso_parser.add_argument("profile", help="SSO profile to refresh")
    sso_parser.set_defaults(func=handle_refresh_sso)
    
    # Shell helpers command
    helpers_parser = subparsers.add_parser("shell-helpers", help="Display shell helper functions")
    helpers_parser.set_defaults(func=handle_shell_helpers)
    
    args = parser.parse_args()
    
    if not args.command:
        parser.print_help()
        sys.exit(0)
    
    args.func(args)

if __name__ == "__main__":
    main() 