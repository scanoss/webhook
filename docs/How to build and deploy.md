![SCANOSS Webhook logo](webhook.png)

# SCANOSS Webhook

The SCANOSS webhook is a multiplatform webhook that performs source code scans against the SCANOSS API. Supports integration with GitHub, GitLab and BitBucket APIs.

## Building

Python 3 is required. It uses setuptools to build a PIP wheel.

- Install dependencies: `make init && make init-dev`

- Generate a new wheel: `make dist`. The binaries will be located under `dist`.

## Installation
### Local Installation

If you have built the webhook locally, you have to call pip3 to install the whl file:
```
pip3 install -U dist/scanoss_webhook_integration-1.0.0-py3-none-any.whl
```
#### Execution
Just run in a terminal:
```
/usr/local/bin/scanoss-hook --cfg ~/scanoss-hook.yaml --handler github
```
Where "scanoss-hook.yaml" is the configuration file for the selected handler, github in this case.
Then, follow the corresponding guide to configure the webhook for your GIT repository.

## Useful scripts

### Service configuration
At scripts/scanoss-hook-systemd you have an example about how to create a daemon for the service.
```
#!/bin/bash
# Replace {DEST} with your destination folder
/usr/local/bin/scanoss-hook --cfg {DEST}/scanoss-hook.yaml --handler github
```
Also you have scripts/scanoss-hook.service, to define the service:
```
# Systemd script for scanoss-hook
# Replace {DEST} with your destination folder
[Unit]
Description=SCANOSS webhook integration service
After=network.target
StartLimitIntervalSec=0

[Service]
Type=simple
Restart=always
RestartSec=1
User=root
ExecStart=/bin/bash {DEST}/scanoss-hook-systemd.sh

[Install]
WantedBy=multi-user.target
```
You have to adjust the configuration file folder and the desired handler.
Then, copy the necessary files as follow (replace {DEST} for the user folder, for example "/home/user/")
```
cp test/scanoss-hook.yaml {DEST}
cp scripts/scanoss-hook-systemd.sh {DEST}
cp scripts/scanoss-hook.service /etc/systemd/system
```
Now you are ready to start the service.
```
service scanoss-hook start
```
You can check the status of the service with the command:
```
systemctl status scanoss-hook
```
And you can see the log file with:
```
cat /log/scanoss-hook.log
```
### Remote Installation
If you want to install the webhook in a remote server, you can use the server install script (requires ssh):
```
sh scripts/server_install.sh server_name
```
This will build, install and start the service on the remote server. You need to config the service and daemon scripts first, as it was explained in the previous section. The scanoss-hook.yaml should be present in the folder {DEST} in the server. You can copy it with scp:
```
scp test/scanoss-hook.yaml {SERVER}:{DEST}
```









