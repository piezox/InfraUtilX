import pulumi
import pulumi_aws as aws
from typing import List, Dict, Optional, Union, Any

class IngressRule:
    def __init__(
        self,
        protocol: str,
        from_port: int,
        to_port: int,
        cidr_blocks: Optional[List[str]] = None,
        security_groups: Optional[List[str]] = None,
        description: Optional[str] = None
    ):
        self.protocol = protocol
        self.from_port = from_port
        self.to_port = to_port
        self.cidr_blocks = cidr_blocks or []
        self.security_groups = security_groups or []
        self.description = description

def create_security_group(
    name: str,
    vpc_id: str,
    description: str,
    ingress_rules: List[Union[Dict[str, Any], IngressRule]],
    egress_rules: Optional[List[Dict[str, Any]]] = None,
    tags: Optional[Dict[str, str]] = None,
) -> aws.ec2.SecurityGroup:
    """
    Create a security group with the specified rules.
    
    Args:
        name: Name of the security group
        vpc_id: ID of the VPC
        description: Description of the security group
        ingress_rules: List of ingress rules
        egress_rules: Optional list of egress rules
        tags: Optional dictionary of tags
    
    Returns:
        aws.ec2.SecurityGroup: The created security group
    """
    # Create the security group
    sg = aws.ec2.SecurityGroup(
        name,
        vpc_id=vpc_id,
        description=description,
        tags=tags,
    )

    # Add ingress rules
    for rule in ingress_rules:
        if isinstance(rule, IngressRule):
            aws.ec2.SecurityGroupRule(
                f"{name}-ingress-{rule.protocol}-{rule.from_port}",
                security_group_id=sg.id,
                type="ingress",
                protocol=rule.protocol,
                from_port=rule.from_port,
                to_port=rule.to_port,
                cidr_blocks=rule.cidr_blocks,
                description=rule.description,
            )
        else:
            aws.ec2.SecurityGroupRule(
                f"{name}-ingress-{rule['protocol']}-{rule['from_port']}",
                security_group_id=sg.id,
                type="ingress",
                protocol=rule["protocol"],
                from_port=rule["from_port"],
                to_port=rule["to_port"],
                cidr_blocks=rule.get("cidr_blocks", []),
                description=rule.get("description"),
            )

    # Add egress rules (default: allow all outbound traffic)
    if egress_rules is None:
        egress_rules = [{
            "protocol": "-1",
            "from_port": 0,
            "to_port": 0,
            "cidr_blocks": ["0.0.0.0/0"],
        }]

    for rule in egress_rules:
        aws.ec2.SecurityGroupRule(
            f"{name}-egress-{rule['protocol']}-{rule['from_port']}",
            security_group_id=sg.id,
            type="egress",
            protocol=rule["protocol"],
            from_port=rule["from_port"],
            to_port=rule["to_port"],
            cidr_blocks=rule.get("cidr_blocks", []),
            description=rule.get("description"),
        )

    return sg 