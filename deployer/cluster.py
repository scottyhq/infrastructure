import os
import json
import subprocess
import tempfile

from pathlib import Path
from contextlib import contextmanager

from hub import Hub
from utils import print_colour
from file_acquisition import get_decrypted_file


class Cluster:
    """
    A single k8s cluster we can deploy to
    """

    def __init__(self, spec, config_path):
        self.spec = spec
        self.config_path = config_path
        self.hubs = [Hub(self, hub_spec) for hub_spec in self.spec["hubs"]]
        self.support = self.spec.get("support", {})

    @contextmanager
    def auth(self):
        if self.spec["provider"] == "gcp":
            yield from self.auth_gcp()
        elif self.spec["provider"] == "aws":
            yield from self.auth_aws()
        elif self.spec["provider"] == "azure":
            yield from self.auth_azure()
        elif self.spec["provider"] == "kubeconfig":
            yield from self.auth_kubeconfig()
        else:
            raise ValueError(f'Provider {self.spec["provider"]} not supported')

    def ensure_docker_credhelpers(self):
        """
        Setup credHelper for current hub's image registry.

        Most image registries (like ECR, GCP Artifact registry, etc) use
        a docker credHelper (https://docs.docker.com/engine/reference/commandline/login/#credential-helpers)
        to authenticate, rather than a username & password. This requires an
        entry per registry in ~/.docker/config.json.

        This method ensures the appropriate credential helper is present
        """
        image_name = self.spec["image_repo"]
        registry = image_name.split("/")[0]

        helper = None
        # pkg.dev is used by Google Cloud Artifact registry
        if registry.endswith("pkg.dev"):
            helper = "gcloud"

        if helper is not None:
            dockercfg_path = os.path.expanduser("~/.docker/config.json")
            try:
                with open(dockercfg_path) as f:
                    config = json.load(f)
            except FileNotFoundError:
                config = {}

            helpers = config.get("credHelpers", {})
            if helpers.get(registry) != helper:
                helpers[registry] = helper
                config["credHelpers"] = helpers
                with open(dockercfg_path, "w") as f:
                    json.dump(config, f, indent=4)

    def deploy_support(self):
        cert_manager_url = "https://charts.jetstack.io"
        cert_manager_version = "v1.3.1"

        print_colour("Adding cert-manager chart repo...")
        subprocess.check_call(
            [
                "helm",
                "repo",
                "add",
                "jetstack",
                cert_manager_url,
            ]
        )

        print_colour("Updating cert-manager chart repo...")
        subprocess.check_call(
            [
                "helm",
                "repo",
                "update",
            ]
        )

        print_colour("Provisioning cert-manager...")
        subprocess.check_call(
            [
                "helm",
                "upgrade",
                "--install",
                "--create-namespace",
                "--namespace=cert-manager",
                "cert-manager",
                "jetstack/cert-manager",
                f"--version={cert_manager_version}",
                "--set=installCRDs=true",
            ]
        )
        print_colour("Done!")

        print_colour("Provisioning support charts...")

        support_dir = (Path(__file__).parent.parent).joinpath("helm-charts", "support")
        subprocess.check_call(["helm", "dep", "up", support_dir])

        support_secrets_file = support_dir.joinpath("enc-support.secret.yaml")
        # TODO: Update this with statement to handle any number of context managers
        #       containing decrypted support values files. Not critical right now as
        #       no individual cluster has specific support secrets, but it's possible
        #       to support that if we want to in the future.
        with get_decrypted_file(support_secrets_file) as secret_file:
            cmd = [
                "helm",
                "upgrade",
                "--install",
                "--create-namespace",
                "--namespace=support",
                "--wait",
                "support",
                str(support_dir),
                f"--values={secret_file}",
            ]

            for values_file in self.support["helm_chart_values_files"]:
                cmd.append(f"--values={self.config_path.joinpath(values_file)}")

            print_colour(f"Running {' '.join([str(c) for c in cmd])}")
            subprocess.check_call(cmd)

        print_colour("Done!")

    def auth_kubeconfig(self):
        """
        Context manager for authenticating with just a kubeconfig file

        For the duration of the contextmanager, we:
        1. Decrypt the file specified in kubeconfig.file with sops
        2. Set `KUBECONFIG` env var to our decrypted file path, so applications
           we call (primarily helm) will use that as config
        """
        config = self.spec["kubeconfig"]
        config_path = self.config_path.joinpath(config["file"])

        with get_decrypted_file(config_path) as decrypted_key_path:
            # FIXME: Unset this after our yield
            os.environ["KUBECONFIG"] = decrypted_key_path
            yield

    def auth_aws(self):
        """
        Reads `aws` nested config and temporarily sets environment variables
        like `KUBECONFIG`, `AWS_ACCESS_KEY_ID`, and `AWS_SECRET_ACCESS_KEY`
        before trying to authenticate with the `aws eks update-kubeconfig` or
        the `kops export kubecfg --admin` commands.

        Finally get those environment variables to the original values to prevent
        side-effects on existing local configuration.
        """
        config = self.spec["aws"]
        key_path = self.config_path.joinpath(config["key"])
        cluster_type = config["clusterType"]
        cluster_name = config["clusterName"]
        region = config["region"]

        if cluster_type == "kops":
            state_store = config["stateStore"]

        with tempfile.NamedTemporaryFile() as kubeconfig:
            orig_kubeconfig = os.environ.get("KUBECONFIG", None)
            orig_access_key_id = os.environ.get("AWS_ACCESS_KEY_ID", None)
            orig_secret_access_key = os.environ.get("AWS_SECRET_ACCESS_KEY", None)
            try:
                with get_decrypted_file(key_path) as decrypted_key_path:

                    decrypted_key_abspath = os.path.abspath(decrypted_key_path)
                    if not os.path.isfile(decrypted_key_abspath):
                        raise FileNotFoundError("The decrypted key file does not exist")
                    with open(decrypted_key_abspath) as f:
                        creds = json.load(f)

                    os.environ["AWS_ACCESS_KEY_ID"] = creds["AccessKey"]["AccessKeyId"]
                    os.environ["AWS_SECRET_ACCESS_KEY"] = creds["AccessKey"][
                        "SecretAccessKey"
                    ]

                os.environ["KUBECONFIG"] = kubeconfig.name

                if cluster_type == "kops":
                    subprocess.check_call(
                        [
                            "kops",
                            "export",
                            "kubecfg",
                            "--admin",
                            f"--name={cluster_name}",
                            f"--state={state_store}",
                        ]
                    )
                else:
                    subprocess.check_call(
                        [
                            "aws",
                            "eks",
                            "update-kubeconfig",
                            f"--name={cluster_name}",
                            f"--region={region}",
                        ]
                    )

                yield
            finally:
                if orig_kubeconfig is not None:
                    os.environ["KUBECONFIG"] = orig_kubeconfig
                if orig_access_key_id is not None:
                    os.environ["AWS_ACCESS_KEY_ID"] = orig_access_key_id
                if orig_kubeconfig is not None:
                    os.environ["AWS_SECRET_ACCESS_KEY"] = orig_secret_access_key

    def auth_azure(self):
        """
        Read `azure` nested config, login to Azure with a Service Principal,
        activate the appropriate subscription, then authenticate against the
        cluster using `az aks get-credentials`.
        """
        config = self.spect["azure"]
        key_path = self.config_path.joinpath(config["key"])
        cluster = config["cluster"]
        resource_group = config["resource_group"]

        with tempfile.NamedTemporaryFile() as kubeconfig:
            orig_kubeconfig = os.environ.get("KUBECONFIG", None)

            try:
                os.environ["KUBECONFIG"] = kubeconfig.name

                with get_decrypted_file(key_path) as decrypted_key_path:

                    decrypted_key_abspath = os.path.abspath(decrypted_key_path)
                    if not os.path.isfile(decrypted_key_abspath):
                        raise FileNotFoundError("The decrypted key file does not exist")

                    with open(decrypted_key_path) as f:
                        service_principal = json.load(f)

                # Login to Azure
                subprocess.check_call(
                    [
                        "az",
                        "login",
                        "--service-principal",
                        f"--username={service_principal['service_principal_id']}",
                        f"--password={service_principal['service_principal_password']}",
                        f"--tenant={service_principal['tenant_id']}",
                    ]
                )

                # Set the Azure subscription
                subprocess.check_call(
                    [
                        "az",
                        "account",
                        "set",
                        f"--subscription={service_principal['subscription_id']}",
                    ]
                )

                # Get cluster creds
                subprocess.check_call(
                    [
                        "az",
                        "aks",
                        "get-credentials",
                        f"--name={cluster}",
                        f"--resource-group={resource_group}",
                    ]
                )

                yield
            finally:
                if orig_kubeconfig is not None:
                    os.environ["KUBECONFIG"] = orig_kubeconfig

    def auth_gcp(self):
        config = self.spec["gcp"]
        key_path = self.config_path.joinpath(config["key"])
        project = config["project"]
        # If cluster is regional, it'll have a `region` key set.
        # Else, it'll just have a `zone` key set. Let's respect either.
        location = config.get("zone", config.get("region"))
        cluster = config["cluster"]
        with tempfile.NamedTemporaryFile() as kubeconfig:
            orig_kubeconfig = os.environ.get("KUBECONFIG")
            try:
                os.environ["KUBECONFIG"] = kubeconfig.name
                with get_decrypted_file(key_path) as decrypted_key_path:
                    subprocess.check_call(
                        [
                            "gcloud",
                            "auth",
                            "activate-service-account",
                            f"--key-file={os.path.abspath(decrypted_key_path)}",
                        ]
                    )

                subprocess.check_call(
                    [
                        "gcloud",
                        "container",
                        "clusters",
                        # --zone works with regions too
                        f"--zone={location}",
                        f"--project={project}",
                        "get-credentials",
                        cluster,
                    ]
                )

                yield
            finally:
                if orig_kubeconfig is not None:
                    os.environ["KUBECONFIG"] = orig_kubeconfig
