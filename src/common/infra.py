import logging
from typing import TYPE_CHECKING, Sequence

from common.config import (
    AWS_KEYPAIR_NAME,
    AWS_RES_NAME,
    IMAGE_ID,
)
from common.utils import ec2_cli, ec2_res

if TYPE_CHECKING:
    from mypy_boto3_ec2.literals import InstanceTypeType
    from mypy_boto3_ec2.service_resource import Instance, SecurityGroup, Vpc
    from mypy_boto3_ec2.type_defs import IpPermissionTypeDef

logger = logging.getLogger(__name__)


def setup_security_group(vpc: "Vpc", permissions: Sequence["IpPermissionTypeDef"] = ()):
    logger.info("Setting up security group")
    sg = ec2_res.create_security_group(
        GroupName=AWS_RES_NAME,
        Description=AWS_RES_NAME,
        VpcId=vpc.id,
    )
    sg.authorize_ingress(
        IpPermissions=[
            {
                "FromPort": 22,
                "ToPort": 22,
                "IpProtocol": "tcp",
                "IpRanges": [{"CidrIp": "0.0.0.0/0"}],
            },
            *permissions,
        ],
    )
    return sg


def launch_instances(sg: "SecurityGroup", instance_types: list["InstanceTypeType"]):
    logger.info("Launching instances")
    avail_zones = [
        zone["ZoneName"]
        for zone in ec2_cli.describe_availability_zones()["AvailabilityZones"]
        if "ZoneName" in zone
    ]
    instances: list[Instance] = []
    for i, itype in enumerate(instance_types):
        zone = avail_zones[i % len(avail_zones)]
        instances += ec2_res.create_instances(
            KeyName=AWS_KEYPAIR_NAME,
            SecurityGroupIds=[sg.id],
            InstanceType=itype,
            ImageId=IMAGE_ID,
            MaxCount=1,
            MinCount=1,
            BlockDeviceMappings=[
                {
                    "DeviceName": "/dev/sda1",
                    "Ebs": {
                        "DeleteOnTermination": True,
                        "VolumeSize": 15,
                        "VolumeType": "gp2",
                    },
                }
            ],
            Placement={"AvailabilityZone": zone},
            TagSpecifications=[
                {
                    "ResourceType": "instance",
                    "Tags": [
                        {
                            "Key": "Name",
                            "Value": AWS_RES_NAME,
                        },
                    ],
                }
            ],
        )
    return instances
