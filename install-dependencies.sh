# Install apt packages
sudo apt update
sudo apt install python3-pip xvfb parallel coreutils zip unzip snapd

# Install Python dependencies
pip install -r analyze-topics-api/requirements.txt

# Download Chrome
wget https://dl.google.com/linux/direct/google-chrome-stable_current_amd64.deb
sudo dpkg -i google-chrome-stable_current_amd64.deb
sudo apt -f install

# Download and setup Docker
sudo snap install docker
sudo groupadd docker
sudo usermod -aG docker $USER
newgrp docker