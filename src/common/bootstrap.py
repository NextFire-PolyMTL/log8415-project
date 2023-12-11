import io
import logging
from dataclasses import dataclass
from typing import TYPE_CHECKING, Callable

import backoff
from paramiko import AutoAddPolicy, RSAKey, SSHClient, ssh_exception

from common.config import AWS_KEYPAIR_PEM, SSH_USERNAME
from common.utils import SSHExecError, ssh_exec

if TYPE_CHECKING:
    from mypy_boto3_ec2.service_resource import Instance

logger = logging.getLogger(__name__)


@backoff.on_exception(
    backoff.constant, (ssh_exception.NoValidConnectionsError, TimeoutError)
)
def bootstrap_instance(
    instance: "Instance", setup: Callable[["Instance", SSHClient], None]
):
    logger.info(f"Bootstrapping {instance=}")
    ssh_key = RSAKey.from_private_key_file(AWS_KEYPAIR_PEM.as_posix())
    with SSHClient() as ssh_client:
        ssh_client.set_missing_host_key_policy(AutoAddPolicy())
        ssh_client.connect(
            hostname=instance.public_ip_address,
            username=SSH_USERNAME,
            pkey=ssh_key,
        )
        setup(instance, ssh_client)


@dataclass
class ScriptSetup:
    script: str

    @backoff.on_exception(backoff.constant, SSHExecError)
    def __call__(self, instance: "Instance", ssh_client: SSHClient):
        with io.BytesIO() as f:
            f.write(self.script.encode())
            f.seek(0)
            with ssh_client.open_sftp() as sftp:
                sftp.putfo(f, "setup.sh")
        ssh_exec(ssh_client, "chmod +x setup.sh && sudo ./setup.sh")
