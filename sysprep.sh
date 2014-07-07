#!/usr/bin/expect -f
set timeout -1
set argv1 [lindex $argv 0]
set passthrough [lindex $argv 1]

spawn virsh console $argv1
expect "Escape character is ^]"
send \003
expect ":~# "

# update hostname
send "echo '$argv1' > /etc/hostname; "
send "sed -i'.bak' -e's/ubuntu-14.04\\s*ubuntu-14/$argv1/' /etc/hosts; "
send "\r"
expect ":~# "

if {$passthrough == "true"} {
    # configure kernel for 9p filesystems on bootup
    send "echo '9p\n9pnet\n9pnet_virtio' >> /etc/initramfs-tools/modules; "
    send "update-initramfs -u; "
    send "\r"
    expect ":~# "

    # add passthrough filesystem mount
    send "mkdir /mnt/shared /mnt/shared-local /mnt/shared-host; "
    send "echo 'shared /mnt/shared-host/ 9p ro,trans=virtio,version=9p2000.L' >> /etc/fstab; "
    send "echo 'overlayfs /mnt/shared overlayfs lowerdir=/mnt/shared-host,upperdir=/mnt/shared-local 0 0' >> /etc/fstab; "
    send "\r"
    expect ":~# "
}

send "apt-get -y install avahi-daemon openssh-server\r"
expect ":~# "
send "ssh-keygen -l -f /etc/ssh/ssh_host_ecdsa_key.pub\r"
expect ":~# "
send "rm /etc/init/roottyS0.conf; reboot\r"
expect ":~# "
close
