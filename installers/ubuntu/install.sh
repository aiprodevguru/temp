#!/bin/bash

# Stop running process
pkill /opt/code1
pkill /usr/local/bin/run.sh
rm -rf /opt/code1
rm -rf /usr/local/bin/run.sh

rm -rf /var/.Recorder
mkdir /var/.Recorder

apt-get install -y ffmpeg imagemagick wmctrl xdotool

# Check if the file exists
if [ -f "/etc/gdm3/custom.conf" ]; then
    # Append "Wayland=false" to the end of the file
    echo "WaylandEnable=false" | sudo tee -a /etc/gdm3/custom.conf > /dev/null
    echo "Wayland option added to /etc/gdm3/custom.conf"
else
    echo "Error: /etc/gdm3/custom.conf not found."
fi

# Create run.sh file
cat <<EOT > run.sh
#!/bin/bash

while :
do
    echo "Starting recorder command..."

    /opt/code1

    # Check the exit status of recorder
    if [ \$? -eq 0 ]; then
        echo "recorder command exited successfully."
    else
        echo "recorder command exited with an error. Restarting..."
    fi

    sleep 5  # Wait for 5 seconds before restarting
done
EOT

# Make the file executable
chmod +x run.sh

# Create service file
cat <<EOT > run.service
[Unit]
Description=Recorder Service
After=network.target

[Service]
Type=simple
ExecStart=/usr/local/bin/run.sh
Environment="DISPLAY=$DISPLAY"
Environment="XAUTHORITY=$XAUTHORITY"
Environment="HOME=$HOME"

[Install]
WantedBy=multi-user.target
EOT

mv run.sh /usr/local/bin/
mv run.service /etc/systemd/system/
mv code1 /opt/

sudo systemctl daemon-reload
sudo systemctl enable run.service
sudo systemctl restart run.service
