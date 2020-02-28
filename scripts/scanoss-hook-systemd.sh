#!/bin/bash
# Replace DEST with your destination folder
/usr/local/bin/scanoss-hook --cfg ${DEST}/scanoss-hook.yaml > /var/log/scanoss-hook.log 2>&1