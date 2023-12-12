import asyncio
import logging

from common.infra import launch_instances, setup_security_group
from common.provision import ScriptSetup, provision_instance
from common.utils import get_default_vpc, wait_instance
from jinja2 import Environment, PackageLoader, select_autoescape

from standalone.secrets import MYSQL_ROOT_PASSWORD

logger = logging.getLogger(__name__)

jinja_env = Environment(
    loader=PackageLoader("templates", ""), autoescape=select_autoescape()
)


async def standalone_setup():
    vpc = get_default_vpc()
    sg = setup_security_group(
        vpc,
        [
            {
                "FromPort": 3306,
                "ToPort": 3306,
                "IpProtocol": "tcp",
                "IpRanges": [{"CidrIp": "0.0.0.0/0"}],
            }
        ],
    )

    instances = launch_instances([sg], ["t2.micro"])
    inst = instances[0]
    await asyncio.to_thread(wait_instance, inst)

    script_tpl = jinja_env.get_template("standalone.sh.j2")
    setup = ScriptSetup(script_tpl.render())
    provision_instance(inst, setup)

    script_tpl = jinja_env.get_template("mysql_root_setup.sh.j2")
    setup = ScriptSetup(script_tpl.render(mysql_root_password=MYSQL_ROOT_PASSWORD))
    provision_instance(inst, setup)

    script_tpl = jinja_env.get_template("sakila.sh.j2")
    setup = ScriptSetup(script_tpl.render(mysql_root_password=MYSQL_ROOT_PASSWORD))
    provision_instance(inst, setup)

    logger.info(f"Public IP: {inst.public_ip_address}")

    return inst, sg
