import asyncio
import logging

from common.bootstrap import ScriptSetup, bootstrap_instance
from common.infra import launch_instances, setup_security_group
from common.utils import get_default_vpc, wait_instance
from jinja2 import Environment, PackageLoader, select_autoescape

from cluster.secrets import MYSQL_ROOT_PASSWORD

logger = logging.getLogger(__name__)

jinja_env = Environment(
    loader=PackageLoader("templates", ""), autoescape=select_autoescape()
)


async def cluster_setup():
    vpc = get_default_vpc()
    sg = setup_security_group(
        vpc,
        [
            {
                "FromPort": 3306,
                "ToPort": 3306,
                "IpProtocol": "tcp",
                "IpRanges": [{"CidrIp": "0.0.0.0/0"}],
            },
            {
                "FromPort": 0,
                "ToPort": 65535,
                "IpProtocol": "tcp",
                "IpRanges": [{"CidrIp": vpc.cidr_block}],
            },
            {
                "FromPort": 0,
                "ToPort": 65535,
                "IpProtocol": "udp",
                "IpRanges": [{"CidrIp": vpc.cidr_block}],
            },
        ],
    )

    instances = launch_instances(sg, ["t2.micro"] * 4)
    async with asyncio.TaskGroup() as tg:
        for inst in instances:
            tg.create_task(asyncio.to_thread(wait_instance, inst))

    manager = instances[0]
    workers = instances[1:]

    logger.info("Setup mgmd on manager")
    script_tpl = jinja_env.get_template("cluster_mgmd.sh.j2")
    setup = ScriptSetup(script_tpl.render(manager=manager, workers=workers))
    bootstrap_instance(manager, setup)

    logger.info("Setup ndbd on worker instances")
    script_tpl = jinja_env.get_template("cluster_ndbd.sh.j2")
    setup = ScriptSetup(script_tpl.render(manager=manager))
    async with asyncio.TaskGroup() as tg:
        for worker in workers:
            tg.create_task(asyncio.to_thread(bootstrap_instance, worker, setup))

    logger.info("Setup mysql on all instances")
    script_tpl = jinja_env.get_template("cluster_mysql.sh.j2")
    setup = ScriptSetup(
        script_tpl.render(manager=manager, mysql_root_password=MYSQL_ROOT_PASSWORD)
    )
    async with asyncio.TaskGroup() as tg:
        for inst in instances:
            tg.create_task(asyncio.to_thread(bootstrap_instance, inst, setup))

    logger.info("Load sakila on manager")
    script_tpl = jinja_env.get_template("sakila.sh.j2")
    setup = ScriptSetup(script_tpl.render(mysql_root_password=MYSQL_ROOT_PASSWORD))
    bootstrap_instance(manager, setup)

    logger.info(f"Manager: {manager.public_ip_address}")
    logger.info(f"Workers: {[w.public_ip_address for w in workers]}")
