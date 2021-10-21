![SCANOSS Webhook logo](docs/webhook.png)

# SCANOSS Webhook

The SCANOSS webhook is a multiplatform webhook that performs source code scans against the SCANOSS API. Supports integration with GitHub, GitLab and BitBucket APIs.

[SCANOSS](https://www.scanoss.co.uk) provides a source code scanner that can be used to detect Open Source dependencies in your code.

The purpose of this code is to offer a reference implementation that can be expanded to suit the needs of individuals and organisations.

## Installation

Once you have built the python wheel (Check out the Building instructions), you can install SCANOSS webhook using pip: `pip install -U dist/*.whl`

## Configuration

## Integration with Git repositories

The specific instructions to install SCANOSS webhook depend on the particular vendor. SCANOSS webhook requires to be configured to receive pull requests, and be allowed to post commit comments and set the build status.

To test the webhook, once configured, you can perform a commit. If all permissions are right and everything goes smoothly, you should see that the webhook has created a comment in your commit, containing a summary of the scan results.

### Github

#### Create a Personal Access Token

Go to your user **Settings > Developer Settings**. Select **Personal access Tokens**, select **Generate new token** button.

Select the following scopes:

- `repo:status`
- `repo_deployment`
- `public_repo`

Click on **Generate token** and save the token generated.

#### Configure the webhook

To configure the SCANOSS Webhook in a repository, go to the repository Settings > Webhooks. The click on **Add a Webhook**.

Fill in the Add webhook form:

- Add the webhook URL as the Payload URL
- Select Content Type `application/json`
- Add a secret
- The webhook needs to receive `push` events only.
- Make sure that **Active** is checked.

#### Configuration example

```
github:
  api-base: https://api.github.com # Or your local GitHub Enterprise API endpoint
  api-user: your-api-user
  api-key: your-personal-access-token
  secret-token: your-secret-token
scanoss:
  url: https://api-url-for-scanoss.example.com # scanner api, https://osskb.org by default
  token: my-scanoss-token # token for the scanning API. 
  comment_always: 1 # post a comment for each scan, whatever you have a match or not
  sbom_filename: SBOM.json # name of the sbom file sended as assets to the scanning API.

```

### Bitbucket

#### Create an App password

On the webhook user's settings, you can create an App password, with repository write permissions.

#### Configure the webhook

1. From Bitbucket, open the repository where you want to add the webhook.
2. Click the **Settings** link on the left side.
3. From the links on the Settings page, click the **Webhooks** link.
4. Click the **Add webhook** button to create a webhook for the repository. The Add new webhook page appears. Fill in the name, and URL, and make sure that the webhook can receive pull requests.

You can check the extended instructions on the [Bitbucket webhooks documentation](https://confluence.atlassian.com/bitbucket/manage-webhooks-735643732.html)

#### Configuration example

```config-bb.yaml
bitbucket:
  api-base: https://bitbucket.org/ # This can also be your local bitbucket deployment URL.
  api-key: your-bb-app-password
  api-user: your-bb-user-name
scanoss:
  url: https://api-url-for-scanoss.example.com
  token: my-scanoss-token
```

### GitLab

#### Generate an Access Token

In GitLab, on the webhook user's settings, select **Access Tokens**. Fill in a name and expiry date, and select **api** scope. Then **Create personal access token**. Take note of the token generated.

#### Configure the webhook

In GitLab, go to the repository where you want to install the webhook. Then select **settings**, then **Webhook**. Fill in the form with the URL of the webhook, add a secret token, and check **Push events**.

#### Configuration example

```
gitlab:
  api-base: https://gitlab.com/api/v4 # This can also be your local GitLab API endpoint
  api-key: your-gitlab-access-token
  secret-token: your-secret-token
scanoss:
  url: https://api-url-for-scanoss.example.com
  token: my-scanoss-token
```

## Contributing

Please see our [Contributing Guide](CONTRIBUTING.md) and our [Code of Conduct](CODE_OF_CONDUCT.md).

## Building

Python 3 is required. It uses setuptools to build a PIP wheel.

- Install dependencies: `make init && make init-dev`

- Generate a new wheel: `make dist`. The binaries will be located under `dist`.
