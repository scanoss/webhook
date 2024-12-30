<img src="docs/webhook.png" alt="SCANOSS Webhook logo" width="150" height="150" />

# SCANOSS Webhook

The SCANOSS webhook is a multiplatform webhook that performs source code scans against the SCANOSS API. Supports integration with GitHub, GitLab and BitBucket APIs.

[SCANOSS](https://www.scanoss.com) provides a source code scanner that can be used to detect Open Source dependencies in your code.

The purpose of this code is to offer a reference implementation that can be expanded to suit the needs of individuals and organisations.

## Installation

For building and intallation see the guide [How to build and deploy](/docs/How%20to%20build%20and%20deploy.md).

## Integration with Git repositories

The specific instructions to install SCANOSS webhook depend on the particular vendor. SCANOSS webhook requires to be configured to receive pull requests, and be allowed to post commit comments and set the build status.

To test the webhook, once configured, you can perform a commit. If all permissions are right and everything goes smoothly, you should see that the webhook has created a comment in your commit, containing a summary of the scan results.

### Github
See the guide [How to config Github](/docs/How%20to%20config%20Github.md).
### Bitbucket
See the guide [How to config Bitbucket](/docs/How%20to%20config%20Bitbucket.md).
### GitLab
See the guide [How to config Gitlab](/docs/How%20to%20config%20Gitlab.md).

## Contributing

Please see our [Contributing Guide](CONTRIBUTING.md) and our [Code of Conduct](CODE_OF_CONDUCT.md).
