import argparse
import getpass
from functools import lru_cache

from ..api.ansible import AnsibleApi
from ..api.github import GitHubApi
from ..api.nutanix import NutanixApi
from ..api.terraform import TerraformApi
from ..config.config_mixer import _list_from_arg
from ..utils import utils
from ..utils.logger import get_logger
from .infoblox_cli import (
    infoblox_get_next_ipv4,
    infoblox_get_next_ipv6,
    infoblox_host_record_exists,
)

logger = get_logger(__name__)


@lru_cache(maxsize=1)
def get_ansible_instance():
    return AnsibleApi()


def ansible_run_job(args, config):
    ansible = get_ansible_instance()
    ansible.run_job(args.job_template_name, args.job_data, user_config=config)


@lru_cache(maxsize=1)
def get_github_instance():
    return GitHubApi()


def github_get_project_data(args, config):
    github = get_github_instance()
    github.get_project_data(
        args.owner, args.repo, args.project_name, args.os_type, user_config=config
    )


def infoblox_parsers(subparsers):
    host_exists_parser = subparsers.add_parser(
        "infoblox.host_record_exists", help="Verify Hostname exists"
    )
    host_exists_parser.add_argument(
        "-c", "--config_path", required=False, help="Path to config YAML"
    )
    # Optional direct args (Override config if both present)
    host_exists_parser.add_argument("-f", "--fqdn", required=False, help="FQDN")
    host_exists_parser.set_defaults(func=infoblox_host_record_exists)

    get_next_ipv4_parser = subparsers.add_parser(
        "infoblox.get_next_available_ipv4", help="Verify Hostname exists"
    )
    get_next_ipv4_parser.add_argument(
        "-c", "--config_path", required=False, help="Path to config YAML"
    )
    # Optional direct args (Override config if both present)
    get_next_ipv4_parser.add_argument(
        "-n", "--network_cidr", required=False, help="V4 Network CIDR"
    )
    get_next_ipv4_parser.set_defaults(func=infoblox_get_next_ipv4)

    get_next_ipv6_parser = subparsers.add_parser(
        "infoblox.get_next_available_ipv6", help="Verify Hostname exists"
    )
    get_next_ipv6_parser.add_argument(
        "-c", "--config_path", required=False, help="Path to config YAML"
    )
    # Optional direct args (Override config if both present)
    get_next_ipv6_parser.add_argument(
        "-n", "----network_cidr_v6", required=False, help="V6 Network CIDR"
    )
    get_next_ipv6_parser.set_defaults(func=infoblox_get_next_ipv6)


def nexus_handler(args, config):
    config["password"] = getpass.getpass("Enter your password:")
    nutanix = NexusApi(config)
    criteria = utils.to_key_value(config["criteria"])
    resp = nutanix.get_package_info(config["tag"], criteria)
    print(resp)


@lru_cache(maxsize=1)
def get_nutanix_instance():
    return NutanixApi()


def nutanix_launch_app(args, config):
    nutanix = get_nutanix_instance()
    nutanix.launch_app(
        args.project, args.owner_email, args.owner_seid, args.server_data, user_config=config
    )


@lru_cache(maxsize=1)
def get_terraform_instance():
    return TerraformApi()


def terraform_onboard(args, config):
    members_list = _list_from_arg(args.members)
    terraform = get_terraform_instance()
    terraform.launch_onboard(
        args.organization, args.team_name, args.project_name, members_list, user_config=config
    )


def main():
    parser = argparse.ArgumentParser(
        description="Unified Multi-tool CLI entry point for launching automation jobs"
    )
    subparsers = parser.add_subparsers(dest="command", required=True)

    ansible_parser = subparsers.add_parser("ansible.run_job", help="Run Ansible job")
    ansible_parser.add_argument("-c", "--config_path", required=False, help="Path to config YAML")
    # Optional direct args (Override config if both present)
    ansible_parser.add_argument(
        "-t", "--job_template_name", required=False, help="Ansible Job Template Name"
    )
    ansible_parser.add_argument("-d", "--job_data", required=False, help="Job Data")
    ansible_parser.set_defaults(func=ansible_run_job)

    github_parser = subparsers.add_parser("github.get_project_data", help="Get project data")
    github_parser.add_argument("-c", "--config_path", required=False, help="Path to config YAML")
    # Optional direct args (Override config if both present)
    github_parser.add_argument("-o", "--owner", required=False, help="GitHub Repository Owner")
    github_parser.add_argument("-r", "--repo", required=False, help="GitHub Repository")
    github_parser.add_argument("-p", "--project_name", required=False, help="Project Name")
    github_parser.add_argument("-os", "--os_type", required=False, help="OS Type")
    github_parser.set_defaults(func=github_get_project_data)

    infoblox_parsers(subparsers)

    nutanix_parser = subparsers.add_parser("nutanix.launch_app", help="Launch Nutanix blueprint")
    nutanix_parser.add_argument("-c", "--config_path", required=False, help="Path to config YAML")
    # Optional direct args (Override config if both present)
    nutanix_parser.add_argument("-p", "--project", required=False, help="Project Name")
    nutanix_parser.add_argument("-oe", "--owner_email", required=False, help="Owner Email")
    nutanix_parser.add_argument("-os", "--owner_seid", required=False, help="Owner SEID")
    nutanix_parser.add_argument("-d", "--server_data", required=False, help="Server Data")
    nutanix_parser.set_defaults(func=nutanix_launch_app)

    terraform_parser = subparsers.add_parser("terraform.onboard", help="Onboard Terraform")
    terraform_parser.add_argument("-c", "--config_path", required=False, help="Path to config YAML")
    # Optional direct args (Override config if both present)
    terraform_parser.add_argument(
        "-o", "--organization", required=False, help="TFE Organization Name"
    )
    terraform_parser.add_argument(
        "-p", "--project_name", required=False, help="Project name to use"
    )
    terraform_parser.add_argument(
        "-t", "--team_name", required=False, help="Team name to ensure access"
    )
    terraform_parser.add_argument(
        "-m", "--members", required=False, help="Team members (comma separated)"
    )
    terraform_parser.set_defaults(func=terraform_onboard)

    args = parser.parse_args()
    config = utils.load_config(args.config_path) if getattr(args, "config_path", None) else {}
    args.func(args, config)


if __name__ == "__main__":
    main()
