"""
Command line interface for deployer
"""
import argparse

from deploy_actions import (
    deploy,
    deploy_support,
    deploy_grafana_dashboards,
    use_cluster_credentials,
)
from config_validation import (
    validate_cluster_config,
    validate_support_config,
    validate_hub_config,
)


def main():
    argparser = argparse.ArgumentParser(
        description="""A command line tool to perform various functions related
        to deploying and maintaining a JupyterHub running on kubernetes
        infrastructure
        """
    )
    subparsers = argparser.add_subparsers(
        required=True, dest="action", help="Available subcommands"
    )

    # === Arguments and options shared across subcommands go here ===#
    # NOTE: If we do not add a base_parser here with the add_help=False
    #       option, then we see a "conflicting option strings" error when
    #       running `python deployer --help`
    base_parser = argparse.ArgumentParser(add_help=False)
    base_parser.add_argument(
        "cluster_name",
        type=str,
        help="The name of the cluster to perform actions on",
    )

    # === Add new subcommands in this section ===#
    # Deploy subcommand
    deploy_parser = subparsers.add_parser(
        "deploy",
        parents=[base_parser],
        help="Install/upgrade the helm charts of JupyterHubs on a cluster",
    )
    deploy_parser.add_argument(
        "hub_name",
        nargs="?",
        help="The hub, or list of hubs, to install/upgrade the helm chart for",
    )
    deploy_parser.add_argument(
        "--skip-hub-health-test", action="store_true", help="Bypass the hub health test"
    )
    deploy_parser.add_argument(
        "--config-path",
        help="File to read secret deployment configuration from",
        # This filepath is relative to the PROJECT ROOT
        default="shared/deployer/enc-auth-providers-credentials.secret.yaml",
    )

    # Validate subcommand
    validate_parser = subparsers.add_parser(
        "validate",
        parents=[base_parser],
        help="Validate the cluster.yaml configuration itself, as well as the provided non-encrypted helm chart values files for each hub or the specified hub.",
    )
    validate_parser.add_argument(
        "hub_name",
        nargs="?",
        help="The hub, or list of hubs, to validate provided non-encrypted helm chart values for.",
    )

    # deploy-support subcommand
    deploy_support_parser = subparsers.add_parser(
        "deploy-support",
        parents=[base_parser],
        help="Install/upgrade the support helm release on a given cluster",
    )

    # deploy-grafana-dashboards subcommand
    deploy_grafana_dashboards_parser = subparsers.add_parser(
        "deploy-grafana-dashboards",
        parents=[base_parser],
        help="Deploy grafana dashboards to a cluster for monitoring JupyterHubs. deploy-support must be run first!",
    )

    # use-cluster-credentials subcommand
    use_cluster_credentials_parser = subparsers.add_parser(
        "use-cluster-credentials",
        parents=[base_parser],
        help="Modify the current kubeconfig with the deployer's access credentials for the named cluster",
    )
    # === End section ===#

    args = argparser.parse_args()

    if args.action == "deploy":
        deploy(
            args.cluster_name,
            args.hub_name,
            args.skip_hub_health_test,
            args.config_path,
        )
    elif args.action == "validate":
        validate_cluster_config(args.cluster_name)
        validate_support_config(args.cluster_name)
        validate_hub_config(args.cluster_name, args.hub_name)
    elif args.action == "deploy-support":
        deploy_support(args.cluster_name)
    elif args.action == "deploy-grafana-dashboards":
        deploy_grafana_dashboards(args.cluster_name)
    elif args.action == "use-cluster-credentials":
        use_cluster_credentials(args.cluster_name)
