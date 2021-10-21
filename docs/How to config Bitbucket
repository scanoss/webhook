![SCANOSS Webhook logo](docs/webhook.png)

# SCANOSS Webhook - Bitbucket Configuration

The SCANOSS webhook is a multiplatform webhook that performs source code scans against the SCANOSS API. Supports integration with GitHub, GitLab and BitBucket APIs.

[SCANOSS](https://www.scanoss.com) provides a source code scanner that can be used to detect Open Source dependencies in your code.

The purpose of this code is to offer a reference implementation that can be expanded to suit the needs of individuals and organisations.

## Installation
For building and intallation see the guide [How to build and deploy](https://github.com/scanoss/webhook/blob/master/docs/How%20to%20build%20and%20deploy.md).

#### Create an App password

On the webhook user's settings (in your Bitbucket account), you can create an App password, with repository write permissions.

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

