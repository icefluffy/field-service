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
        echo "Reconnect in Portainer, then run: python3 /mnt/sethDeploy.py"
        sync
        kill -TERM 1
        ;;
    *)
        echo "Preparation failed. Container will not be restarted."
        exit "$status"
        ;;
esac
