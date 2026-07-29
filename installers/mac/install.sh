#!/bin/bash

# -----------------------------
# Get current user
# -----------------------------
current_user=$(whoami)
current_group=$(id -gn "$current_user")
owner_spec="$current_user:$current_group"
user_home=$(eval echo "~$current_user")
recorder_dir="$user_home/.Recorder"
launch_agents_folder="$user_home/Library/LaunchAgents"
plist_path="$launch_agents_folder/com.code1.runsh.plist"
runsh_path="/usr/local/bin/runsh"
code1_path="/opt/code1"
echo "[INFO] Installing as user: $current_user"

# -----------------------------
# Ensure LaunchAgents folder exists
# -----------------------------
mkdir -p "$launch_agents_folder"
chown "$owner_spec" "$launch_agents_folder"

# -----------------------------
# Kill old processes safely
# -----------------------------
echo "[INFO] Killing old code1/runsh processes..."
launchctl bootout gui/$(id -u) "$plist_path" 2>/dev/null || true
sudo pkill -f "$code1_path" || true
pkill -f "$runsh_path" 2>/dev/null || true

# -----------------------------
# Delete previous resources
# -----------------------------
echo "[INFO] Removing previous resources..."
rm -rf "$recorder_dir"
sudo rm -f "$runsh_path"
sudo rm -f "$code1_path"
rm -f "$plist_path"

# -----------------------------
# Recreate recorder directory and ensure LaunchAgents exists
# -----------------------------
echo "[INFO] Creating recorder and LaunchAgents folders..."
mkdir -p "$recorder_dir/imgs" "$launch_agents_folder"
chown -R "$owner_spec" "$recorder_dir" "$launch_agents_folder"

# -----------------------------
# Deploy code1
# -----------------------------
sudo mkdir -p /opt
sudo cp code1 "$code1_path"
sudo chmod +x "$code1_path"
sudo chown "$owner_spec" "$code1_path"

# -----------------------------
# Create runsh script
# -----------------------------
cat <<EOF | sudo tee "$runsh_path" > /dev/null
#!/bin/bash

# wait 15 seconds after login
sleep 15

RECORDER_DIR="\$HOME/.Recorder"
mkdir -p "\$RECORDER_DIR/imgs"

while :
do
    $code1_path

    if [ \$? -ne 0 ]; then
        echo "\$(date): code1 exited with error, restarting..." >> "\$RECORDER_DIR/runsh_error.log"
    fi

    sleep 5
done
EOF

sudo chmod +x "$runsh_path"
sudo chown "$owner_spec" "$runsh_path"

# -----------------------------
# Create LaunchAgent plist
# -----------------------------
mkdir -p "$launch_agents_folder"

cat <<EOF > "$plist_path"
<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple Computer//DTD PLIST 1.0//EN"
 "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0">
<dict>
    <key>Label</key>
    <string>com.code1.runsh</string>

    <key>ProgramArguments</key>
    <array>
        <string>$runsh_path</string>
    </array>

    <key>RunAtLoad</key>
    <true/>

    <key>KeepAlive</key>
    <true/>

    <key>StandardOutPath</key>
    <string>$recorder_dir/runsh_output.log</string>

    <key>StandardErrorPath</key>
    <string>$recorder_dir/runsh_error.log</string>

    <key>WorkingDirectory</key>
    <string>$user_home</string>

    <key>EnvironmentVariables</key>
    <dict>
        <key>PATH</key>
        <string>/usr/local/bin:/usr/bin:/bin:/usr/sbin:/sbin</string>
    </dict>
</dict>
</plist>
EOF

chmod 644 "$plist_path"
chown "$owner_spec" "$plist_path"

# -----------------------------
# Ensure ownership
# -----------------------------
chown -R "$owner_spec" "$recorder_dir" "$launch_agents_folder"
sudo chown "$owner_spec" "$runsh_path" "$code1_path"

# -----------------------------
# Load LaunchAgent
# -----------------------------
launchctl bootout gui/$(id -u) "$plist_path" 2>/dev/null || true
launchctl bootstrap gui/$(id -u) "$plist_path"

echo "[INFO] Installation complete."
echo "[INFO] LaunchAgent loaded: com.code1.runsh"
