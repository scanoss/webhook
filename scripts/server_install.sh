
#!/bin/bash
# server_install.sh
# Simple script to push and restart scanoss-hook in remote server
# Make sure that you set ${DEST} to your destination folder.
# To access logs: journalctl -u scanoss-hook


SERVER=${1:-dev}

make dist

# Install Python wheel in remote server
WHEEL=$(ls dist/*.whl| awk -F'/' '{print $2}')
echo "Pushing wheel: ${WHEEL}"
scp dist/$WHEEL $SERVER:/root
ssh $SERVER "pip3 install -U ${WHEEL}"
# Systemd service configuration
scp scripts/scanoss-hook-systemd.sh $SERVER:${DEST}
scp scripts/scanoss-hook.service $SERVER:/etc/systemd/system
#ssh $SERVER "systemctl stop scanoss-hook && systemctl daemon-reload && systemctl start scanoss-hook"
