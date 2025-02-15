# Manage authentication

## Auth0

[auth0](https://auth0.com) provides authentication for the majority of 2i2c hubs. It can
be configured with many different [connections](https://auth0.com/docs/identityproviders)
that users can authenticate with - such as Google, GitHub, etc.

So we want to manage authentication by:

1. Explicitly listing the type of connection we want for this hub, via
   `auth0.connection`. Currently common ones are `google-oauth2` for Google &
   `github` for GitHub. *Users* of the hub will use this method to log in to
   the hub.

   You can set the auth0 connector for a hub with:

   ```yaml
   auth0:
      connection: google-oauth2
   ```

   Theoretically, every provider in [this list](https://auth0.com/docs/connections/identity-providers-social)
   is supported. However, we've currently only tested this with Google
   (`google-oauth2`) and GitHub (`github`)

2. Explicitly list *admin users* for a given hub. These admin users will be the
   only ones allowed to log in to begin with. They can use the JupyterHub
   admin interface (available from their hub control panel) to explicitly allow
   more users into the hub. This way, we don't need to be involved in explicitly
   allowing users into hubs.

   In the admin interface, admin users can add users via a username appropriate
   for the auth connector used. For GitHub, it's the username. For Google Auth,
   it's the email address.

   You can set the admin interfaces for a hub like this:

   ```yaml
   jupyterhub:
     auth:
       allowed_users:
           # WARNING: THESE USER LISTS MUST MATCH (for now)
           - user1@gmail.com
           - user2@gmail.com
       admin_users:
           # WARNING: THESE USER LISTS MUST MATCH (for now)
           - user1@gmail.com
           - user2@gmail.com
   ```

```{admonition} Switching auth
Switching authentication providers (e.g. from GitHub to Google) for a pre-existing hub will simply create new usernames. Any pre-existing users will no longer be able to access their accounts (although administrators will be able to do so). If you have pre-existing users and want to switch the hub authentication, rename the users to the new auth pattern (e.g. convert github handles to emails).
```

## Native JupyterHub OAuthenticator for GitHub Orgs and Teams

```{note}
This setup is currently only supported for communities that **require** authentication via a GitHub organisation or team.

We may update this policy in the future.
```

For communities that require authenticating users against [a GitHub organisation or team](https://docs.github.com/en/organizations), we instead use the [native JupyterHub OAuthenticator](https://github.com/jupyterhub/oauthenticator).
Presently, this involves a few more manual steps than the `auth0` setup described above.

1. **Create a GitHub OAuth App.**
   This can be achieved by following [GitHub's documentation](https://docs.github.com/en/developers/apps/building-oauth-apps/creating-an-oauth-app).
   - Create [a new app](https://github.com/organizations/2i2c-org/settings/applications/new) inside the
     `2i2c-org`.
   - When naming the application, please follow the convention `<cluster_name>-<hub_name>` for consistency, e.g. `2i2c-staging` is the OAuth app for the staging hub running on the 2i2c cluster.
   - The Homepage URL should match that in the `domain` field of the appropriate `cluster.yaml` file in the `infrastructure` repo.
   - The authorisation callback URL is the homepage url appended with `/hub/oauth_callback`. For example, `staging.pilot.2i2c.cloud/hub/oauth_callback`.
   - Once you have created the OAuth app, make a new of the client ID, generate a client secret and then hold on to these values for a future step

2. **Create or update the appropriate secret config file under `config/clusters/<cluster_name>/<hub_name>.secret.values.yaml`.**
   You should add the following config to this file, pasting in the client ID and secret you generated in step 1.

    ```yaml
    jupyterhub:
      hub:
        config:
          GitHubOAuthenticator:
            client_id: CLIENT_ID
            client_secret: CLIENT_SECRET
    ```

    ````{note}
    Add the `basehub` key above the `jupyterhub` key for `daskhub` deployments.
    For example:

    ```yaml
    basehub:
      jupyterhub:
        ...
    ```
    ````

    ```{note}
    Make sure this is encrypted with `sops` before committing it to the repository!

    `sops --output config/clusters/<cluster_name>/enc-<hub_name>.secret.values.yaml --encrypt config/clusters/<cluster_name>/<hub_name>.secret.values.yaml`
    ```

3. **Set the hub to _not_ configure Auth0 in the `config/clusters/<cluster_name>/cluster.yaml` file.**
   To ensure the deployer does not provision and configure an OAuth app from Auth0, the following config should be added to the appropriate hub in the cluster's `cluster.yaml` file.

   ```yaml
   hubs:
     - name: <hub_name>
       auth0:
         enabled: false
   ```

4. **If not already present, add the secret hub config file to the list of helm chart values file in `config/clusters<cluster_name>/cluster.yaml`.**
   If you created the `enc-<hub_name>.secret.values.yaml` file in step 2, add it the the `cluster.yaml` file like so:

   ```yaml
   ...
   hubs:
     - name: <hub_name>
       ...
       helm_chart_values_files:
         - <hub_name>.values.yaml
         - enc-<hub_name>.secret.values.yaml
     ...
   ```

5. **Edit the non-secret config under `config/clusters/<cluster_name>/<hub_name>.values.yaml`.**
   You should make sure the matching hub config takes one of the following forms.

   ```{warning}
   When using this method of authentication, make sure to remove the `allowed_users` key from the config.
   This is because this key will block any user not listed under it **even if** they are valid members of the the organisation or team you are authenticating against.

   You should keep the `admin_users` key, however.
   ```

   To authenticate against a GitHub organisation:

    ```yaml
    jupyterhub:
      hub:
        config:
          JupyterHub:
            authenticator_class: github
          GitHubOAuthenticator:
            oauth_callback_url: https://{{ HUB_DOMAIN }}/hub/oauth_callback
            allowed_organizations:
              - 2i2c-org
              - ORG_NAME
            scope:
              - read:user
    ```

   To authenticate against a GitHub Team:

    ```yaml
    jupyterhub:
      hub:
        config:
          JupyterHub:
            authenticator_class: github
          GitHubOAuthenticator:
            oauth_callback_url: https://{{ HUB_DOMAIN }}/hub/oauth_callback
            allowed_organizations:
              - 2i2c-org:tech-team
              - ORG_NAME:TEAM_NAME
            scope:
              - read:org
    ```

6. Run the deployer as normal to apply the config.

## CILogon

[CILogon](https://www.cilogon.org) is a service provider that allows users to login against various identity providers, including campus identity providers. 2i2c manages CILogon through [auth0](https://auth0.com), similar to Google and GitHub authentication.

```{seealso}
See the [CILogon documentation on `Auth0`](https://www.cilogon.org/auth0) for more configuration information.
```

### Key terms

Some key terms about CILogon authentication worth mentioning:

Identity Provider
: The authentication service available through the CILogon connection.

  When a user logs in via CILogon, they are first presented with a list of various institutions and organizations that they may choose from (e.g. `UC Berkeley` or `Australia National University`).

  The available identity providers are members of [InCommon](https://www.incommon.org/federation/), a federation of universities and other organizations that provide single sign-on access to various resources.

  Example:

  ```{figure} ../../images/cilogon-ipd-list.png
  A list of Identity Providers the user may select from.
  ```

User account
: Within an institution, each user is expected to have their own user account (e.g. `myname@berkeley.edu`). This is the account that is used to give somebody an ID on their JupyterHub. This is entered on an Identity Provider's login screen. For example:

  ```{figure} ../../images/cilogon-berkley-login-page.png
  The Berkeley authentication screen.
  ```

  ```{note}
  The JupyterHub usernames will be the **email address** that users provide when authenticating with an institutional identity provider. It will not be the CILogon `user_id`! This is because the `USERNAME_KEY` used for the CILogon login is the email address.
  ```

### Steps to enable CILogon authentication

1. List CILogon as the type of connection we want for a hub, via `auth0.connection`:

   ```yaml
   auth0:
      connection: CILogon
   ```

2. Add **admin users** to the hub by explicitly listing their email addresses. Add **allowed users** for the hub by providing a regex pattern that will match to an institutional email address. (see example below)

  ```{note}
  Don't forget to allow login to the test user (`deployment-service-check`), otherwise the hub health check performed during deployment will fail.
  ```

### Example config for CILogon

The CILogon connection works by providing users the option to login into a hub using any CILogon Identity Provider of their choice, as long as the email address of the user or the entire organization (e.g. `*@berkeley.edu`) has been provided access into the hub.

The following configuration example shows off how to configure hub admins and allowed users:

1. **Hub admins** are these explicit emails:
   - one `@campus.edu` user
   - one `@gmail.com` user
   - the 2i2c staff (identified through their 2i2c email address)

2. **Allowed users** are matched against a pattern, with a few specific addresses added in as well
   - all `@2i2c.org` email adresses
   - all `@campus.edu` email addresses
   - `user2@gmail.com`
   - the test username, `deployment-service-check`

```yaml
jupyterhub:
  custom:
    2i2c:
      add_staff_user_ids_to_admin_users: true
      add_staff_user_ids_of_type: "google"
  hub:
    config:
      Authenticator:
        admin_users:
          - user1@campus.edu
          - user2@gmail.com
        username_pattern: '^(.+@2i2c\.org|.+@campus\.edu|user2@gmail\.com|deployment-service-check)$'
```

```{note}
All the users listed under `admin_users` need to match the `username_pattern` expression otherwise they won't be allowed to login!
```

### Switch Identity Providers or user accounts

By default, logging in with a particular user account will persist your credentials in future sessions.
This means that you'll automatically re-use the same institutional and user account when you access the hub's home page.

#### Switch Identity Providers

1. **Logout of the Hub** using the logout button or by going to `https://{hub-name}/hub/logout`.
2. **Clear browser cookies** (optional). If the user asked CILogon to re-use the same Identity Provider connection when they logged in, they'll need to [clear browser cookies](https://www.lifewire.com/how-to-delete-cookies-2617981) for https://cilogon.org.

   ```{figure} ../../images/cilogon-remember-this-selection.png
   The dialog box that allows you to re-use the same Identity Provider.
   ```

   Firefox example:
   ```{figure} ../../images/cilogon-clear-cookies.png
   An example of clearing cookies with Firefox.
   ```

3. The next time the user goes to the hub's landing page, they'll be asked to re-authenticate and will be presented with the list of available Identity Providers after choosing the CILogon connection.
4. They can now choose **another Identity Provider** via CILogon.

```{note}
If the user choses the same Identity Provider, then they will be automatically logged in with the same user account they've used before. To change the user account, see [](auth:cilogon:switch-user-accounts).
```

(auth:cilogon:switch-user-accounts)=
#### Switch user account

1. Logout of the Hub using the logout button or by going to `https://{hub-name}/hub/logout`.
2. Logout of CILogon by going to the [CILogon logout page](https://cilogon.org/logout).
3. The next time the user goes to the hub's landing page, they'll be asked to re-authenticate and will be presented with the list of available Identity Providers after choosing the CILogon connection.
4. Choose the **same Identity Provider** to login.
5. The user can now choose **another user account** to login with.

#### 403 - Unauthorized errors

If you see a 403 error page, this means that the account you were using to login hasn't been allowed by the hub administrator.

```{figure} ../../images/403-forbidden.png
```

If you think this is an error, and the account should have been allowed, then contact the hub adminstrator/s.

If you used the wrong user account, you can log in using another account by following the steps in [](auth:cilogon:switch-user-accounts).
