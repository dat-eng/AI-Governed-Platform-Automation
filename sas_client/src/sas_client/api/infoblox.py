import json
from typing import Final, Optional

from ..config.infoblox_config import build_infoblox_base_config, build_infoblox_user_config
from ..utils.logger import get_logger
from ..utils.utils import build_overrides, validate_inputs_with_config
from .common.api_client import APIClient, APIClientConfig


class InfobloxApi:
    """
    A client for interacting with Infoblox's WAPI endpoints.

    Provides methods to create, query, and delete host and network records
    through the Infoblox REST API.
    """

    PATH_INFOBLOX: Final[str] = "/wapi/v2.10.1"
    PATH_INFOBLOX_NETWORK_REFERENCE: Final[str] = (
        f"{PATH_INFOBLOX}/{{endpoint}}?network={{network_cidr}}"
    )
    PATH_INFOBLOX_HOST_REFERENCE: Final[str] = f"{PATH_INFOBLOX}/record:host?name={{name}}"
    PATH_INFOBLOX_NEXT_AVAILABLE_IP: Final[str] = (
        f"{PATH_INFOBLOX}/{{network_ref}}?_function=next_available_ip"
    )
    PATH_INFOBLOX_HOST_RECORD: Final[str] = f"{PATH_INFOBLOX}/record:host"

    def __init__(self):
        """
        Initialize the Infoblox API client.

        Args:
            config (dict): Dictionary containing 'base_url', 'username', and 'password' keys.
        """
        self.logger = get_logger(__name__)
        self.config = build_infoblox_base_config()
        self.client = APIClient(APIClientConfig.from_dict(self.config))

    def create_host_record(self, fqdn: str, mac: str, ip_v4: str, ip_v6: str) -> str:
        """
        Create a host record in Infoblox.

        Args:
            fqdn (str): Fully Qualified Domain Name of the host.
            mac (str): MAC address of the host.
            ip_v4 (str): IPv4 address.
            ip_v6 (str): IPv6 address.

        Returns:
            str: Response containing the host record reference
        """
        payload = {
            "name": fqdn,
            "ipv4addrs": [{"ipv4addr": ip_v4, "mac": mac}],
            "ipv6addrs": [{"ipv6addr": ip_v6, "duid": mac}],
        }
        return self.client.post(endpoint=self.PATH_INFOBLOX_HOST_RECORD, json=payload)

    def get_network_reference(self, network_cidr: str, ip_version: str = "v4") -> Optional[str]:
        """
        Get the network reference ID for a given CIDR.

        Args:
            network_cidr (str): Network in CIDR notation.
            ip_version (str): 'v4' or 'v6'. Defaults to 'v4'.

        Returns:
            Optional[str]: Network reference string if found, else None.
        """
        endpoint = "network" if ip_version == "v4" else "ipv6network"
        url = self.PATH_INFOBLOX_NETWORK_REFERENCE.format(
            endpoint=endpoint, network_cidr=network_cidr
        )
        networks = self.client.get(endpoint=url)
        self.logger.debug(f"networks: {networks}")
        return networks[0]["_ref"] if networks else None

    def get_host_reference(self, fqdn: str) -> Optional[str]:
        """
        Get the reference ID for a host by its FQDN.

        Args:
            fqdn (str): Fully Qualified Domain Name.

        Returns:
            Optional[str]: Host reference if found, else None.
        """
        url = self.PATH_INFOBLOX_HOST_REFERENCE.format(name=fqdn)
        response = self.client.get(endpoint=url)
        return response[0]["_ref"] if response else None

    def get_reference(
        self, endpoint: str, filter_key: str, filter_value: str
    ) -> tuple[Optional[str], Optional[dict]]:
        """
        Generic method to get object reference by filtering a resource.

        Args:
            endpoint (str): WAPI endpoint (e.g., 'record:host').
            filter_key (str): Query parameter key.
            filter_value (str): Query parameter value.

        Returns:
            tuple: (reference string or None, full record dict or None)
        """
        url = f"{self.PATH_INFOBLOX}/{endpoint}?{filter_key}={filter_value}"
        response = self.client.get(endpoint=url)
        return (response[0]["_ref"], response[0]) if response else (None, None)

    def get_next_available_ip(
        self, ip_version: str, network_cidr: Optional[str] = None, user_config: dict = None
    ) -> str:
        """
        Get the next available IP from a given network reference.

        Args:
            network_cidr (str): Network reference identifier.

        Returns:
            str: Next available IP address.
        """
        if ip_version not in ("v4", "v6"):
            self.logger.info(
                "IP Version argument is required: get_next_available_ip(ip_version, config or overrides dict)"
            )
            return "Missing required argument"

        overrides = {}
        if network_cidr is not None:
            key = "network_cidr" if ip_version == "v4" else "network_cidr_v6"
            overrides = {key: network_cidr}

        self.config = build_infoblox_user_config(
            self.config, user_config=user_config, overrides=overrides
        )

        # Validate keys & required input
        network_cidr_arg = "network_cidr" if ip_version == "v4" else "network_cidr_v6"
        validation = validate_inputs_with_config(
            args={network_cidr_arg: self.config.get("network_cidr")},
            config=self.config,
            required_mappings={
                network_cidr_arg: [network_cidr_arg],
            },
        )

        if validation["status"] == "error":
            self.logger.error(f"Missing Keys: {validation}")
            return validation

        network_cidr = (
            self.config["network_cidr"] if ip_version == "v4" else self.config["network_cidr_v6"]
        )

        network_ref = self.get_network_reference(network_cidr, ip_version)

        self.logger.info(f"🚀 Getting next available IP for {ip_version}")
        url = self.PATH_INFOBLOX_NEXT_AVAILABLE_IP.format(network_ref=network_ref)
        response = self.client.post(endpoint=url, data={"num": 1})
        self.logger.info(f"Next available ip for {ip_version} is {response['ips'][0]}")
        return response["ips"][0]

    def get_host_record(self, fqdn: str, add_return_fields: Optional[str] = None) -> dict:
        """
        Retrieve a host record from Infoblox.

        Args:
            fqdn (str): Fully Qualified Domain Name.
            add_return_fields (Optional[str]): Comma-separated fields to include in response.

        Returns:
            dict: Host record response object.
        """
        return_fields = "ipv4addrs,ipv6addrs,name"
        if add_return_fields:
            return_fields += "," + add_return_fields

        params = {"name": fqdn, "_return_fields": return_fields, "_return_as_object": "1"}

        return self.client.get(endpoint=self.PATH_INFOBLOX_HOST_RECORD, params=params)

    def host_record_exists(self, fqdn: Optional[str] = None, user_config: dict = None) -> bool:
        """
        Check if a host record exists in Infoblox.

        Args:
            fqdn (str): Fully Qualified Domain Name. If not provided, defaults to config.

        Returns:
            bool: True if host record exists, False otherwise.
        """
        overrides = build_overrides(fqdn=fqdn)

        self.config = build_infoblox_user_config(
            self.config, user_config=user_config, overrides=overrides
        )
        self.logger.debug(f"Resolved job config: {json.dumps(self.config, indent=2)}")

        # Validate keys
        validation = validate_inputs_with_config(
            args={"fqdn": self.config.get("fqdn")},
            config=self.config,
            required_mappings={
                "fqdn": ["fqdn"],
            },
        )

        if validation["status"] == "error":
            self.logger.error(f"Missing Keys: {validation}")
            return validation

        self.logger.info(f"🚀 Verifying Host Record exists for fqdn: {self.config.get('fqdn')}")

        url = f"{self.PATH_INFOBLOX_HOST_RECORD}?name={self.config.get('fqdn')}"
        response = self.client.get(endpoint=url)
        self.logger.info(f"fqdn {self.config.get('fqdn')} exists: {bool(response)}")
        return bool(response)

    def delete_record(self, reference: str) -> dict:
        """
        Delete a record from Infoblox using its reference.

        Args:
            reference (str): The object reference returned by Infoblox.

        Returns:
            dict: Response from the delete operation.
        """
        url = f"{self.PATH_INFOBLOX}/{reference}"
        return self.client.delete(endpoint=url)
