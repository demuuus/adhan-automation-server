![Python](https://img.shields.io/badge/Python-3.9%2B-blue)
![Platform](https://img.shields.io/badge/Platform-Linux-green)
![License](https://img.shields.io/badge/License-MIT-yellow)
![Status](https://img.shields.io/badge/Status-Stable-brightgreen)

# 🕌 Adhan Automation Server
A lightweight Linux-based Adhan automation system that:
- Fetches daily prayer times via API
- Plays Adhan automatically at each prayer time
- Plays a reminder 2 minutes before each prayer
- Works offline using cached prayer times
- Runs as a systemd service for 24/7 reliability

Designed to run on:
- Old laptops
- Raspberry Pi
- Linux home servers

## ⚙️ Features
- Automatic daily prayer time fetch (Aladhan API)
- Offline fallback using cached data
- 2-minute pre-Adhan reminder
- Systemd auto-start support
- Automatic daily refresh at 00:01
- Crash recovery (Restart=always)
- SSH CLI mode to check prayer times

## 📁 Project Structure
```
adhan/
│
├── adhan.py
├── config.json
├── requirements.txt
├── logs/
│  └── cache.json
│
└── audio/
    ├── Adzan Mekkah.mp3
    └── reminder.mp3
```

## 🔧 Installation Guide (Linux)
### 1. Clone Repository
```
git clone https://github.com/YOUR_USERNAME/adhan-automation-server.git
cd adhan-automation-server
```

### 2. Create Virtual Environment
```
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
```

### 3. Install Dependencies
```
sudo apt update
sudo apt install python3 python3-venv mpg123 alsa-utils
```

### 4. Configure Location
Edit:
***```config.json```***

Example JSON:
```
{
    "city": "New Delhi",
    "country": "India",
    "method": 2
}
```

### 5. Run the Bot
```
python3 adhan.py
```

## 🔄 Run as Systemd Service
Create:
```
/etc/systemd/system/adhan.service
```
Example:
```
[Unit]
Description=Adhan Player Service
After=network.target sound.target

[Service]
Type=simple
User=YOUR_USERNAME
WorkingDirectory=/home/YOUR_USERNAME/adhan-automation-server
ExecStart=/home/YOUR_USERNAME/adhan-automation-server/venv/bin/python /home/YOUR_USERNAME/adhan-automation-server/adhan.py
Restart=always
RestartSec=5

[Install]
WantedBy=multi-user.target
```
Then:
```
sudo systemctl daemon-reload
sudo systemctl enable adhan
sudo systemctl start adhan
```

## 🔍 CLI Commands
### Show Live Prayer Time (API)
```
python adhan.py --show
```
### Show Cached Prayer Time
```
python adhan.py --cached
```

## 🔊 Audio Notes
- Uses ***```mpg123```*** for playback
- Ensure correct output device:
  ***```alsamixer```***

