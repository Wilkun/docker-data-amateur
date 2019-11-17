#!/bin/bash
# Remember that line endings should be LF
echo "Start config script" && \
echo "Configure sudo" && \
echo 'sdrzymala ALL=(ALL:ALL) ALL' | sudo EDITOR='tee -a' visudo && \
adduser sdrzymala sudo && \
echo "Update ubuntu" && \
export TERM=xter && \
echo "console-setup   console-setup/charmap47 select  UTF-8" > encoding.conf && \
debconf-set-selections encoding.conf && \
rm encoding.conf && \
apt-get update -y && \
#apt-get upgrade -y && \
#apt full-upgrade -y && \
echo "Install basic stuff" && \
apt-get install -y vim && \
apt-get install -y net-tools && \
apt-get install -y python-pip && \
apt-get install -y openssh-server && \
echo "Install Samba" && \
apt-get install -y samba && \
apt-get install -y samba-common && \
apt-get install -y python-glade2 && \
apt-get install -y system-config-samba && \
mv /etc/samba/smb.conf /etc/samba/smb.conf.bak && \
echo "
#============================ Global definition ================================

[global]
workgroup = WORKGROUP
server string = Samba Server %v
netbios name = ubuntu1604
security = user
map to guest = bad user
name resolve order = bcast host
dns proxy = no
bind interfaces only = yes

#============================ Share Definitions ============================== 

[Public]
  path = /samba/public
  writable = yes
  guest ok = yes
  guest only = yes
  read only = no
  create mode = 0777
  directory mode = 0777
  force user = nobody
" >> /etc/samba/smb.conf && \
mkdir -p /samba/public && \
chown -R nobody:nogroup /samba/public && \
chmod -R 0775 /samba/public && \
# known issue, there is a bug....
# sumba is not working
# after repeating the same code manually it works tough...
touch /samba/public/test.txt && \
systemctl restart nmbd && \
echo "Install Docker" && \
apt-get install -y apt-transport-https && \
apt-get install -y ca-certificates && \
apt-get install -y curl && \
apt-get install -y gnupg-agent && \
apt-get install -y software-properties-common && \
curl -fsSL https://download.docker.com/linux/ubuntu/gpg | apt-key add - && \
add-apt-repository "deb [arch=amd64] https://download.docker.com/linux/ubuntu $(lsb_release -cs) stable" && \
apt-get update && \
apt-get install -y docker-ce docker-ce-cli containerd.io && \
pip install docker-compose && \
echo "Finish config script" && \
exit 0