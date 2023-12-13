import json
import logging
from importlib.resources import files
from typing import TYPE_CHECKING, Sequence

from cluster.secrets import MYSQL_ROOT_PASSWORD
from cluster.setup import make_cluster
from common.infra import launch_instances, setup_security_group
from common.provision import ScriptSetup, provision_instance
from common.utils import get_default_vpc, wait_instance
from jinja2 import Environment, PackageLoader, select_autoescape

import patterns.apps

if TYPE_CHECKING:
    from mypy_boto3_ec2.service_resource import Instance, SecurityGroup, Vpc

logger = logging.getLogger(__name__)

jinja_env = Environment(
    loader=PackageLoader("templates", ""), autoescape=select_autoescape()
)
apps_res = files(patterns.apps)


async def patterns_setup():
    vpc = get_default_vpc()
    manager, workers, internal_sg = await make_cluster(vpc)
    proxy, proxy_sg = await make_proxy(vpc, manager, workers, internal_sg)
    (gatekeeper, gatekeeper_sg), (trusted_host, _) = await make_gatekeeper(
        vpc, proxy, proxy_sg
    )
    # Allow any host to access gatekeeper
    gatekeeper_sg.authorize_ingress(
        CidrIp="0.0.0.0/0", FromPort=3000, ToPort=3000, IpProtocol="tcp"
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

    script_tpl = jinja_env.get_template("pattern_deploy.sh.j2")
    main_ts = (apps_res / "proxy.ts").read_text()
    config = dict(
        manager=manager.private_ip_address,
        workers=[w.private_ip_address for w in workers],
        username="root",
        password=MYSQL_ROOT_PASSWORD,
        db="sakila",
    )
    config_json = json.dumps(config)
    setup = ScriptSetup(script_tpl.render(main_ts=main_ts, config_json=config_json))
    provision_instance(manager, setup)

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
        FromPort=9000,
        ToPort=9000,
        IpProtocol="tcp",
    )

    script_tpl = jinja_env.get_template("pattern_deploy.sh.j2")
    main_ts = (apps_res / "trusted.ts").read_text()
    config = dict(proxy=f"http://{proxy.private_ip_address}:9000")
    config_json = json.dumps(config)
    setup = ScriptSetup(script_tpl.render(main_ts=main_ts, config_json=config_json))
    provision_instance(trusted_host, setup)

    logger.info("Setting up gatekeeper")
    gatekeeper_sg = setup_security_group(vpc)
    instances = launch_instances([gatekeeper_sg], ["t2.large"])
    gatekeeper = instances[0]
    wait_instance(gatekeeper)

    # Allow gatekeeper to access trusted host
    trusted_host_sg.authorize_ingress(
        CidrIp=gatekeeper.private_ip_address + "/32",
        FromPort=8000,
        ToPort=8000,
        IpProtocol="tcp",
    )

    script_tpl = jinja_env.get_template("pattern_deploy.sh.j2")
    main_ts = (apps_res / "gatekeeper.ts").read_text()
    config = dict(trusted=f"http://{trusted_host.private_ip_address}:8000")
    config_json = json.dumps(config)
    setup = ScriptSetup(script_tpl.render(main_ts=main_ts, config_json=config_json))
    provision_instance(gatekeeper, setup)

    return (gatekeeper, gatekeeper_sg), (trusted_host, trusted_host_sg)
