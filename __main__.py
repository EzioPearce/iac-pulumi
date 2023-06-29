"""Pulumi-Python Infra as Code"""

import pulumi
#from pulumi_aws import s3
import pulumi_aws as awsx
from pulumi_aws import ec2, lb, autoscaling

# Create an AWS provider
provider = awsx.Provider("aws", region="ap-south-1")

# Create a vpc
vpc = awsx.ec2.Vpc("vpc-name",
    cidr_block="10.0.0.0/16",
    instance_tenancy="default",
    tags={
        "Name": "vpc-name",
    })

subnet1 = ec2.Subnet("subnet1",
    vpc_id=vpc.id,
    cidr_block="10.0.1.0/24",
    availability_zone="ap-south-1a",
    tags={"Name": "d-subnet-1"})

# Create the second subnet in the VPC
subnet2 = ec2.Subnet("subnet2",
    vpc_id=vpc.id,
    cidr_block="10.0.2.0/24",
    availability_zone="ap-south-1b",
    tags={"Name": "d-subnet-2"})

igw = ec2.InternetGateway("igw",
    vpc_id=vpc.id)

ec2.DefaultRouteTable("MainRouteTable",
    default_route_table_id=vpc.default_route_table_id,
    routes=[
        ec2.DefaultRouteTableRouteArgs(
            cidr_block="0.0.0.0/0",
            gateway_id=igw.id,
        ),
    ]
)
ec2.RouteTable("routeTable",
    vpc_id=vpc.id,
    routes=[{
        "cidr_block": "0.0.0.0/0",
        "gateway_id": igw.id,
    }],
    tags={"Name": "public"})

#pulumi.export("vpcId", vpc.vpc_id)
pulumi.export("subnet_id1", subnet1.id)
pulumi.export("subnet_id2", subnet2.id)

# Create security group for EC2 instances
security_group = ec2.SecurityGroup("sg-name",
    vpc_id=vpc.id,
    ingress=[
        ec2.SecurityGroupIngressArgs(
            protocol="tcp",
            from_port=22,
            to_port=22,
            cidr_blocks=["0.0.0.0/0"],
        ),
        ec2.SecurityGroupIngressArgs(
            protocol="tcp",
            from_port=80,
            to_port=80,
            cidr_blocks=["0.0.0.0/0"],
        ),
        ec2.SecurityGroupIngressArgs(
            protocol="tcp",
            from_port=443,
            to_port=443,
            cidr_blocks=["0.0.0.0/0"],
        ),
        ec2.SecurityGroupIngressArgs(
            protocol="tcp",
            from_port=9000,
            to_port=9000,
            cidr_blocks=["0.0.0.0/0"],
        )
    ],
    egress=[
        ec2.SecurityGroupIngressArgs(
            protocol="-1",
            from_port=0,
            to_port=0,
            cidr_blocks=["0.0.0.0/0"],
        )
    ]
)

instance1 = ec2.Instance("instance1",
    instance_type="t3a.micro",
    ami="ami-057752b3f1d6c4d6c",  # Specify the appropriate AMI ID: Check out the AMIs on ec2 console while selecting the OS
    subnet_id=subnet1.id,
    associate_public_ip_address=True,
    key_name="ssh-key-name",
    security_groups=[security_group.id],
    tags={"Name": "instance2"})

instance2 = ec2.Instance("instance2",
    instance_type="t3a.micro", #Because AMD is cheaper
    ami="ami-057752b3f1d6c4d6c",  # Specify the appropriate AMI ID. Check out the AMIs on ec2 console while selecting the OS
    subnet_id=subnet2.id,
    associate_public_ip_address=True,
    key_name="ssh-key-name",
    security_groups=[security_group.id],
    tags={"Name": "instance2"})
# Create a target group
target_group = lb.TargetGroup("tg-name",
    port=9000,
    protocol="HTTP",
    target_type="instance",
    vpc_id=vpc.id)

# Register the instances with the target group
lb.TargetGroupAttachment("attachment1",
    target_group_arn=target_group.arn,
    target_id=instance1.id)

lb.TargetGroupAttachment("attachment2",
    target_group_arn=target_group.arn,
    target_id=instance2.id)

# Create application load balancer
load_balancer = lb.LoadBalancer("myLoadBalancer",
    subnets=[subnet1.id, subnet2.id],
    security_groups=[security_group.id],
    load_balancer_type="application")

# Create listener and attach target group
lb.Listener("myListener",
    load_balancer_arn=load_balancer.arn,
    port=80,
    protocol="HTTP",
    default_actions=[{
        "type": "forward",
        "target_group_arn": target_group.arn,
    }])

# Export the load balancer DNS name
pulumi.export("loadBalancerDnsName", load_balancer.dns_name)

# Create an ecr repo
repository = awsx.ecr.Repository("ecr-repo-name", image_scanning_configuration={
    "scanOnPush": True
})
pulumi.export("repository_url", repository.repository_url)