![SCANOSS Webhook logo](webhook.png)

# SCANOSS Webhook - Github Configuration

The SCANOSS webhook is a multiplatform webhook that performs source code scans against the SCANOSS API. Supports integration with GitHub, GitLab and BitBucket APIs.

[SCANOSS](https://www.scanoss.com) provides a source code scanner that can be used to detect Open Source dependencies in your code.

The purpose of this code is to offer a reference implementation that can be expanded to suit the needs of individuals and organisations.

## Installation
For building and intallation see the guide [How to build and deploy](https://github.com/scanoss/webhook/blob/master/docs/How%20to%20build%20and%20deploy.md).

## Create a Personal Access Token

In your github account, Go to your user **Settings > Developer Settings**. Select **Personal access Tokens**, select **Generate new token** button.

Select the following scopes:

- `repo:status`
- `repo_deployment`
- `public_repo`

Click on **Generate token** and save the token generated.

## Configure the webhook

To configure the SCANOSS Webhook in a repository, go to the repository Settings > Webhooks. The click on **Add a Webhook**.

Fill in the Add webhook form:

- Add the webhook URL (or the public ip and port of your server) as the Payload URL
- Select Content Type `application/json`
- Add a secret
- The webhook needs to receive `push` events.
- Make sure that **Active** is checked.

## SCANOSS-hook Configuration file

Next you can see the scanoss-hook.yaml configuration file adjusted for github: 
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
Remember: you need to restart the webhook after change the configuration file. If you are running the service you have to do:
```
service scanoss-hook stop
service scanoss-hook start
```

