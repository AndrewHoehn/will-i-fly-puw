#!/bin/bash

# deploy_db.sh
# Automates the "Atomic Swap" of the local history.db to Fly.io

APP_NAME="kpuw-tracker"
LOCAL_DB="backend/history.db"
REMOTE_TEMP="/data/history_new.db"
REMOTE_FINAL="/data/history.db"

# Check if local DB exists
if [ ! -f "$LOCAL_DB" ]; then
    echo "Error: Local database not found at $LOCAL_DB"
    exit 1
fi

echo "Deploying $LOCAL_DB to $APP_NAME..."

# 1. Upload to temp file
echo "1. Uploading to temporary location..."
fly sftp put "$LOCAL_DB" "$REMOTE_TEMP" -a "$APP_NAME"

if [ $? -ne 0 ]; then
    echo "Upload failed!"
    exit 1
fi

# 2. Atomic Swap
echo "2. Swapping database files..."
fly ssh console -C "mv $REMOTE_TEMP $REMOTE_FINAL" -a "$APP_NAME"

if [ $? -ne 0 ]; then
    echo "Swap failed!"
    exit 1
fi

# 3. Restart App
echo "3. Restarting application..."
fly apps restart "$APP_NAME"

echo "✅ Database deployed successfully!"
