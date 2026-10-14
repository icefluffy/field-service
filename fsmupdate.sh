#!/bin/bash
set -euo pipefail

# Exit 10 means new files were staged and a restart is required.
status=0
python3 /mnt/sethDeploy.py --prepare || status=$?

case "$status" in
    0)
        exit 0
        ;;
    10)
        echo "Restarting odoo18 using your existing PID 1 workflow..."
        echo ""
        echo "Reconnect in Portainer, by clicking Disconnect button at top of page"
        echo "Then connect again. (you have already been disconnected by the restart...)"
        echo ""
        echo "After reconnection, run: python3 /mnt/sethDeploy.py or sethDeploy.py"
        sync
        kill -TERM 1
        ;;
    *)
        echo "Preparation failed. Container will not be restarted."
        exit "$status"
        ;;
esac
