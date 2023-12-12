import logging
from typing import TYPE_CHECKING, Sequence

from cluster.setup import make_cluster
from common.infra import launch_instances, setup_security_group
from common.utils import get_default_vpc, wait_instance
from jinja2 import Environment, PackageLoader, select_autoescape

if TYPE_CHECKING:
    from mypy_boto3_ec2.service_resource import Instance, SecurityGroup, Vpc

logger = logging.getLogger(__name__)

jinja_env = Environment(
    loader=PackageLoader("templates", ""), autoescape=select_autoescape()
)


async def patterns_setup():
    vpc = get_default_vpc()
    manager, workers, internal_sg = await make_cluster(vpc)
    proxy, proxy_sg = await make_proxy(vpc, manager, workers, internal_sg)
    (gatekeeper, gatekeeper_sg), (trusted_host, _) = await make_gatekeeper(
        vpc, proxy, proxy_sg
    )
    # Allow any host to access gatekeeper
    gatekeeper_sg.authorize_ingress(
        CidrIp="0.0.0.0/0", FromPort=3306, ToPort=3306, IpProtocol="tcp"
    )

    logger.info("Setup complete")
    logger.info(f"{manager.public_ip_address=}")
    for worker in workers:
        logger.info(f"{worker.public_ip_address=}")
    logger.info(f"{proxy.public_ip_address=}")
    logger.info(f"{trusted_host.public_ip_address=}")
    logger.info(f"{gatekeeper.public_ip_address=}")


async def make_proxy(
    vpc: "Vpc",
    manager: "Instance",
    workers: Sequence["Instance"],
    internal_sg: "SecurityGroup",
):
    logger.info("Setting up proxy")
    sg = setup_security_group(vpc)
    instances = launch_instances([sg], ["t2.large"])
    proxy = instances[0]
    wait_instance(proxy)

    # Allow proxy to access cluster mysqld
    internal_sg.authorize_ingress(
        CidrIp=proxy.private_ip_address + "/32",
        FromPort=3306,
        ToPort=3306,
        IpProtocol="tcp",
    )

    return proxy, sg


async def make_gatekeeper(vpc: "Vpc", proxy: "Instance", proxy_sg: "SecurityGroup"):
    logger.info("Setting up trusted host")
    trusted_host_sg = setup_security_group(vpc)
    instances = launch_instances([trusted_host_sg], ["t2.large"])
    trusted_host = instances[0]
    wait_instance(trusted_host)

    # Allow trusted host to access proxy
    proxy_sg.authorize_ingress(
        CidrIp=trusted_host.private_ip_address + "/32",
        FromPort=3306,
        ToPort=3306,
        IpProtocol="tcp",
    )

    logger.info("Setting up gatekeeper")
    gatekeeper_sg = setup_security_group(vpc)
    instances = launch_instances([gatekeeper_sg], ["t2.large"])
    gatekeeper = instances[0]
    wait_instance(gatekeeper)

    # Allow gatekeeper to access trusted host
    trusted_host_sg.authorize_ingress(
        CidrIp=gatekeeper.private_ip_address + "/32",
        FromPort=3306,
        ToPort=3306,
        IpProtocol="tcp",
    )

    return (gatekeeper, gatekeeper_sg), (trusted_host, trusted_host_sg)
