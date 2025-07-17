# Install apt packages
sudo apt update
sudo apt install parallel coreutils zip unzip snapd

# Download and setup Docker
sudo snap install docker
sudo groupadd docker
sudo usermod -aG docker $USER
newgrp docker