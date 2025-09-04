# loopstation

python -m venv

source venv/bin/activate

sudo apt-get install portaudio19-dev

pip install pynput pyaudio

pip install keyboard

pip install lgpio

pip install numpy


add service

sudo nano /etc/systemd/system/loopstation.service

# pyhon1: /usr/bin/python3
# python2: /home/pi/loopstation/venv/bin/python

[Unit]
Description=Loopstation
After=sound.target

[Service]
User=pi
Group=pi
ExecStart=/home/pi/loopstation/venv/bin/python /home/pi/loopstation/loopstation.py
WorkingDirectory=/home/pi/loopstation
StandardOutput=journal
StandardError=journal
Restart=always
# Ensure PulseAudio knows where to connect
Environment="XDG_RUNTIME_DIR=/run/user/1000"
Environment="PULSE_SERVER=unix:/run/user/1000/pulse/native"
#User=pi
#Group=pi
#Environment="PULSE_SERVER=unix:/run/user/1000/pulse/native"

[Install]
WantedBy=multi-user.target



reload:
sudo systemctl daemon-reload
sudo systemctl enable loopstation.service
sudo systemctl start loopstation.service

check:
systemctl status loopstation.service
journalctl -u loopstation.service -f
