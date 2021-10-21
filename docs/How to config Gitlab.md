![SCANOSS Webhook logo](docs/webhook.png)

# SCANOSS Webhook - Gitlab Configuration

The SCANOSS webhook is a multiplatform webhook that performs source code scans against the SCANOSS API. Supports integration with GitHub, GitLab and BitBucket APIs.

[SCANOSS](https://www.scanoss.com) provides a source code scanner that can be used to detect Open Source dependencies in your code.

The purpose of this code is to offer a reference implementation that can be expanded to suit the needs of individuals and organisations.

## Installation
For building and intallation see the guide [How to build and deploy](https://github.com/scanoss/webhook/blob/master/docs/How%20to%20build%20and%20deploy.md).

## Generate an Access Token

In GitLab, on the webhook user's settings, select **Access Tokens**. Fill in a name and expiry date, and select **api** scope. Then **Create personal access token**. Take note of the token generated.

## Configure the webhook

In GitLab, go to the repository where you want to install the webhook. Then select **settings**, then **Webhook**. Fill in the form with the URL of the webhook, add a secret token, and check **Push events**.

### Configuration example
```
gitlab:
  api-base: https://gitlab.com/api/v4 # This can also be your local GitLab API endpoint
  api-key: your-gitlab-access-token
  secret-token: your-secret-token
scanoss:
  url: https://api-url-for-scanoss.example.com
  token: my-scanoss-token
```

