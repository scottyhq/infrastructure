(new-hub)=
# Add a new hub

This section describes steps around adding hubs to the 2i2c JupyterHub federation.

## Infrastructure that is needed for a hub

There are three kinds of infrastructure needed to add a new hub. In most cases, they are configured via configuration in the `infrastructure/` repository.

- **A Kubernetes cluster**.
  Deploying a Kubernetes cluster is specific to the cloud provider. For hubs that do not need to use their own cloud credits, or otherwise are fine running on a cloud project that is not owned by their institution, we can deploy hubs on an already-running Kubernetes Cluster.
  For hubs that require their own cluster, we'll need to set it up on our own.
  To do so, see [](new-cluster).
- **Support infrastructure**.
  This is a collection of services that run on a Kubernetes Cluster and help us in running and monitoring things.
  There is one set of services running per **cluster**, not per hub.
  This includes things like Grafana, NFS server provisioners, etc.
- **JupyterHubs**.
  When a cluster is up and running, we may then deploy JupyterHubs on top of it using the JupyterHub Helm Chart.
  Configuration that is specific to each JupyterHub is stored in the [`config/clusters`](https://github.com/2i2c-org/infrastructure/tree/HEAD/config/clusters) folder.
  A GitHub Action workflow then deploys and updates the hubs on a cluster using this configuration.
  There are some cases where you must manually deploy or modify a hub.
  See [](operate:manual-deploy) for more details.

## Overview of hub configuration

Many of our hubs are automatically deployed and updated using GitHub Action workflows and configuration that is defined in [`infrastructure/config/clusters`](https://github.com/2i2c-org/infrastructure/tree/HEAD/config/clusters).

These are a collection of folders (one per cluster) that contain a collection of YAML files (one per hub deployed to that cluster, plus a cluster-wide file) that define the configuration for all of our hubs.
To learn which subset of clusters are *automatically* deployed via GitHub Actions, inspect the `matrix.cluster_name` list in [the `deploy-hubs.yaml` workflow file](https://github.com/2i2c-org/infrastructure/blob/f2ffc8ef51427d5f824747917bfd51533daf3045/.github/workflows/deploy-hubs.yaml#L17-L31).

The process of automatically updating and adding hubs is almost the same for all of the hubs deployed on these clusters.

(new-hub:deploy)=
## To add a new hub

To deploy a new hub, follow these steps:

1. [Ask the Community Representative to fill in this issue template](https://github.com/2i2c-org/infrastructure/issues/new?assignees=&labels=type%3A+hub&template=2_new-hub.yml&title=New+Hub%3A+%3CHub+name%3E).
   This will create a "New Hub" issue and ask the representative questions that are important for understanding how to set up their hub.
   Once that issue is created, move to the next step.
2. Decide whether you'll deploy on a pre-existing Kubernetes cluster, or if you'll need to create a new one.
   See [](cluster:when-to-deploy) for information to help you decide.
3. Determine the **hub helm chart** that is needed.
   Hub helm charts are pre-configured deployments for certain kinds of JupyterHubs.
   There are a few base charts to choose from.
   For more information about our hub helm charts and how to choose, see [](hub-helm-charts).
4. Add a configuration entry for your new hub by creating a new `<hub_name>.values.yaml` file under the appropriate cluster folder, and referencing this file in a new entry under the `hubs` key in the cluster's `cluster.yaml` file.
   Each `*.values.yaml` file is a Zero to JupyterHub configuration, and you can customize whatever you like.
   The easiest way to add new configuration is to look at the entries for similar hubs under the same cluster folder, copy / paste one of them, and make modifications as needed for this specific hub.
   For example, see the hubs configuration in [the 2i2c Google Cloud cluster configuration directory](https://github.com/2i2c-org/infrastructure/tree/HEAD/config/clusters/2i2c).

   :::{seealso}
   See [](/topic/config.md) for more information about hub helm chart configuration.
   :::
5. Create a Pull Request with the new hub entry, and get a team member to review it.
6. Once you merge the pull request, the GitHub Action workflow will detect that a new entry has been added to the configuration file.
   It will then deploy a new JupyterHub with the configuration you've specified onto the corresponding cluster.
7. Monitor the action to make sure that it completes.
   If something goes wrong and the workflow does not finish, try [deploying locally](operate:manual-deploy) to access the logs to help understand what is going on.
   It may be necessary to make new changes to the hub's configuration via a Pull Request, or to *revert* the old Pull Request if you cannot determine how to resolve the problem.

   ```{note}
   In order to protect sensitive tokens, our CI/CD pipeline will not print testing output to its logs.
   You will need to run the deployer locally to inspect these logs.
   ```
8. Log in to the hub and ensure that the hub works as expected from a user's perspective.
9. Send a link to the hub's Community Representative(s) so they can confirm that it works from their perspective as well.

:::{note}
There are some minor additional steps if you need to [deploy a new hub in a AWS cluster](new-hub:aws).
:::

## Automated vs. manual deploys

Some of our infrastructure automatically deploys and updates hubs via GitHub Actions workflows, while others require manual deploys.
This is changing over time as we automate more things, and is dependent on the cloud provider.

General details about our CI/CD machinery lives at [](/reference/ci-cd.md)

## Deploying hubs manually

Some of our infrastructure still requires manual deploys.
There are also situations where you may want to deploy infrastructure manually.
Or situation where some specific steps still need some manual intervention.

The following sections cover how to deploy in these situations:

* [General manual deployment process](operate:manual-deploy)
* Some [AWS specific manual steps](new-hub:aws) needed to deploy a new hub for first time

:::{warning}
Manual deploys should be avoided when possible.
They increase the likelihood of confusion, bottlenecks of information, inconsistent
states and discrepancies between what is already deployed vs. the codebase, among other
things.
:::

## Cloud-specific deployment steps

See the sections below for information about setting up a new hub on specific commercial clouds.

```{toctree}
aws
```
