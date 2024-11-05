# Install apt packages
sudo apt update
sudo apt install wget python3 python3-pip python3-requests xvfb parallel coreutils zip unzip snapd

# Download Chrome
wget https://dl.google.com/linux/direct/google-chrome-stable_current_amd64.deb
sudo dpkg -i google-chrome-stable_current_amd64.deb
sudo apt -f install
rm google-chrome-stable_current_amd64.deb

# Download and setup Docker
sudo snap install docker
sudo groupadd docker
sudo usermod -aG docker $USER
newgrp docker