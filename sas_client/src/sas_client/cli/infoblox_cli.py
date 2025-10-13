from functools import lru_cache

from ..api.infoblox import InfobloxApi
from ..utils.logger import get_logger

logger = get_logger(__name__)


@lru_cache(maxsize=1)
def get_infoblox_instance():
    return InfobloxApi()


def infoblox_host_record_exists(args, config):
    infoblox = get_infoblox_instance()
    result = infoblox.host_record_exists(args.fqdn, user_config=config)
    logger.info(f"Result: {result}")


def infoblox_get_next_ipv4(args, config):
    infoblox = get_infoblox_instance()
    result = infoblox.get_next_available_ip("v4", args.network_cidr, user_config=config)
    logger.info(f"Result: {result}")


def infoblox_get_next_ipv6(args, config):
    infoblox = get_infoblox_instance()
    result = infoblox.get_next_available_ip("v6", args.network_cidr_v6, user_config=config)
    logger.info(f"Result: {result}")
