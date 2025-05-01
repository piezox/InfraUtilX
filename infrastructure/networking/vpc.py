import pulumi
import pulumi_aws as aws
from typing import List, Dict, Optional

def create_vpc(
    name: str,
    cidr_block: str,
    enable_dns_hostnames: bool = True,
    enable_dns_support: bool = True,
    tags: Optional[Dict[str, str]] = None,
) -> tuple[aws.ec2.Vpc, aws.ec2.RouteTable]:
    """
    Create a VPC with the specified configuration.
    
    Args:
        name: Name of the VPC
        cidr_block: CIDR block for the VPC
        enable_dns_hostnames: Whether to enable DNS hostnames
        enable_dns_support: Whether to enable DNS support
        tags: Optional dictionary of tags
    
    Returns:
        tuple[aws.ec2.Vpc, aws.ec2.RouteTable]: The created VPC and public route table
    """
    vpc = aws.ec2.Vpc(
        name,
        cidr_block=cidr_block,
        enable_dns_hostnames=enable_dns_hostnames,
        enable_dns_support=enable_dns_support,
        tags=tags,
    )

    # Create an Internet Gateway
    igw = aws.ec2.InternetGateway(
        f"{name}-igw",
        vpc_id=vpc.id,
        tags=tags,
    )

    # Create a public route table
    public_rt = aws.ec2.RouteTable(
        f"{name}-public-rt",
        vpc_id=vpc.id,
        routes=[
            aws.ec2.RouteTableRouteArgs(
                cidr_block="0.0.0.0/0",
                gateway_id=igw.id,
            ),
        ],
        tags=tags,
    )

    return vpc, public_rt

def create_subnet(
    name: str,
    vpc_id: str,
    cidr_block: str,
    availability_zone: str,
    map_public_ip_on_launch: bool = True,
    tags: Optional[Dict[str, str]] = None,
    public_route_table_id: Optional[str] = None,
) -> aws.ec2.Subnet:
    """
    Create a subnet in the specified VPC.
    
    Args:
        name: Name of the subnet
        vpc_id: ID of the VPC
        cidr_block: CIDR block for the subnet
        availability_zone: Availability zone for the subnet
        map_public_ip_on_launch: Whether to map public IP on launch
        tags: Optional dictionary of tags
        public_route_table_id: Optional ID of the public route table to associate the subnet with
    
    Returns:
        aws.ec2.Subnet: The created subnet
    """
    subnet = aws.ec2.Subnet(
        name,
        vpc_id=vpc_id,
        cidr_block=cidr_block,
        availability_zone=availability_zone,
        map_public_ip_on_launch=map_public_ip_on_launch,
        tags=tags,
    )
    
    # Associate the subnet with the public route table if provided
    if public_route_table_id:
        aws.ec2.RouteTableAssociation(
            f"{name}-rt-association",
            subnet_id=subnet.id,
            route_table_id=public_route_table_id,
        )

    return subnet

def get_availability_zones() -> List[str]:
    """
    Get a list of available availability zones in the current region.
    
    Returns:
        List[str]: List of availability zone names
    """
    zones = aws.get_availability_zones()
    return zones.names 