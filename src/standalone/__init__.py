import asyncio
import logging

from common.bootstrap import ScriptSetup, bootstrap_instance
from common.infra import launch_instances, setup_security_group
from common.utils import wait_instance
from jinja2 import Environment, PackageLoader, select_autoescape

from standalone.secrets import MYSQL_APP_PASSWORD, MYSQL_APP_USER

logger = logging.getLogger(__name__)

jinja_env = Environment(
    loader=PackageLoader(__package__), autoescape=select_autoescape()
)


async def standalone_setup():
    sg = setup_security_group(
        [
            {
                "FromPort": 3306,
                "ToPort": 3306,
                "IpProtocol": "tcp",
                "IpRanges": [{"CidrIp": "0.0.0.0/0"}],
            }
        ]
    )

    instances = launch_instances(sg, ["t2.micro"])
    inst = instances[0]
    await asyncio.to_thread(wait_instance, inst)

    script_tpl = jinja_env.get_template("setup.sh.j2")
    setup = ScriptSetup(
        script_tpl.render(
            mysql_app_user=MYSQL_APP_USER, mysql_app_password=MYSQL_APP_PASSWORD
        )
    )
    bootstrap_instance(inst, setup)

    logger.info(f"Public IP: {inst.public_ip_address}")
