#!/bin/bash

# Step 1: Install dependencies
apt update && apt install -y sudo gcc g++ binutils cmake make \
    automake autoconf libelf-dev bc git \
    flex bison libncurses-dev libssl-dev debootstrap qemu-system-x86 wget curl

# Step 2: Create fuzz user
useradd -ms /bin/bash fuzz
echo "fuzz:fuzz" | chpasswd
usermod -aG sudo fuzz
echo 'fuzz ALL=(ALL) NOPASSWD:ALL' >> /etc/sudoers

# Step 3: Copy diff and warmup.go to /home/fuzz
cp 9750182a9a67f35e95cb1e077a3b69a4a9b54083_0110.diff /home/fuzz/
cp warmup_10_flag0107.go /home/fuzz/
cp ci-qemu-upstream-corpus.db /home/fuzz/
cp syzbot_config /home/fuzz/config
cp create-image.sh /home/fuzz/create-image.sh
cp -r scripts /home/fuzz/
chown fuzz:fuzz /home/fuzz/*.diff /home/fuzz/*.go /home/fuzz/*.db /home/fuzz/config /home/fuzz/create-image.sh 
chown -R fuzz:fuzz /home/fuzz/scripts

# Step 4: Write installation script as fuzz user
cat << 'EOF' > /tmp/setup_as_fuzz.sh
#!/bin/bash

set -e

# === Install Go ===
cd /home/fuzz
wget https://dl.google.com/go/go1.22.1.linux-amd64.tar.gz
tar -C /home/fuzz -xf go1.22.1.linux-amd64.tar.gz
export GOROOT=/home/fuzz/go
export PATH=$GOROOT/bin:$PATH

echo "export GOROOT=/home/fuzz/go" >> ~/.bashrc
echo "export PATH=\$GOROOT/bin:\$PATH" >> ~/.bashrc
source ~/.bashrc
rm /home/fuzz/go1.22.1.linux-amd64.tar.gz

# === Clone sources and create folder structure ===
mkdir -p /home/fuzz/code /home/fuzz/kernel /home/fuzz/Image/imag1
cd /home/fuzz/kernel
git clone https://github.com/torvalds/linux
cd linux
git checkout v6.12-rc6

# === Compile kernel ===
mkdir /home/fuzz/kernel/linux-out
cp /home/fuzz/config /home/fuzz/kernel/linux-out/.config
yes "" | make oldconfig O=/home/fuzz/kernel/linux-out
make -j$(nproc) O=/home/fuzz/kernel/linux-out 2>&1 | tee /home/fuzz/kernel/linux/makeout.txt

# === Create rootfs image ===
cd /home/fuzz/Image/imag1
cp /home/fuzz/create-image.sh ./create-image.sh
chmod +x create-image.sh
./create-image.sh

# === Clone and build sysyphuzz ===
cd /home/fuzz/code
git clone https://github.com/google/syzkaller sysyphuzz
cd sysyphuzz
git checkout 9750182a9a67f35e95cb1e077a3b69a4a9b54083

# === Apply patch and replace warmup.go ===
git apply /home/fuzz/9750182a9a67f35e95cb1e077a3b69a4a9b54083_0110.diff
cp /home/fuzz/warmup_10_flag0107.go /home/fuzz/code/sysyphuzz/pkg/fuzzer/warmup.go

make

# === Setup workdir and corpus ===
# workdir for syzkaller
mkdir /home/fuzz/code/sysyphuzz/workdir_syzk
# workdir for sysyphuzz
mkdir /home/fuzz/code/sysyphuzz/workdir_sysy
# Use syzbot corpus
cp /home/fuzz/ci-qemu-upstream-corpus.db /home/fuzz/code/sysyphuzz/workdir_syzk/corpus.db
cp /home/fuzz/ci-qemu-upstream-corpus.db /home/fuzz/code/sysyphuzz/workdir_sysy/corpus.db

# === Create sysyphuzz config ===
cat << CFG > /home/fuzz/code/sysyphuzz/sysyphuzz.cfg
{
    "target": "linux/amd64",
    "http": "127.0.0.1:56743",
    "workdir": "/home/fuzz/code/sysyphuzz/workdir_sysy",
    "kernel_src": "/home/fuzz/kernel/linux",
    "kernel_obj": "/home/fuzz/kernel/linux-out",
    "raw_cover": true,
    "warm_up": true,
    "boost_only": false,
    "cover_bb_num" : "sysyphuzz_bb",
    "reproduce": false,
    "image": "/home/fuzz/Image/imag1/bullseye.img",
    "sshkey": "/home/fuzz/Image/imag1/bullseye.id_rsa",
    "syzkaller": "/home/fuzz/code/sysyphuzz",
    "procs": 4,
    "type": "qemu",
    "vm": {
        "count": 8,
        "cpu": 2,
        "mem": 4096,
        "kernel": "/home/fuzz/kernel/linux-out/arch/x86/boot/bzImage"
    }
}
CFG

# === Create syzkaller config ===
cat << CFG > /home/fuzz/code/sysyphuzz/syzkaller.cfg
{
    "target": "linux/amd64",
    "http": "127.0.0.1:56743",
    "workdir": "/home/fuzz/code/sysyphuzz/workdir_syzk",
    "kernel_src": "/home/fuzz/kernel/linux",
    "kernel_obj": "/home/fuzz/kernel/linux-out",
    "raw_cover": true,
    "warm_up": false,
    "boost_only": false,
    "cover_bb_num" : "syzkaller_bb",
    "reproduce": false,
    "image": "/home/fuzz/Image/imag1/bullseye.img",
    "sshkey": "/home/fuzz/Image/imag1/bullseye.id_rsa",
    "syzkaller": "/home/fuzz/code/sysyphuzz",
    "procs": 4,
    "type": "qemu",
    "vm": {
        "count": 8,
        "cpu": 2,
        "mem": 4096,
        "kernel": "/home/fuzz/kernel/linux-out/arch/x86/boot/bzImage"
    }
}
CFG

echo "✅ Sysyphuzz environment setup complete."
echo "Run Sysyphuzz using: cd /home/fuzz/code/sysyphuzz && sudo bin/syz-manager -config sysyphuzz.cfg 2>&1| tee ./workdir_sysy/"$(date +"%Y_%m_%d").log""
echo "Run Syzkaller using: cd /home/fuzz/code/sysyphuzz && sudo bin/syz-manager -config syzkaller.cfg 2>&1| tee ./workdir_syzk/"$(date +"%Y_%m_%d").log""
echo "! Do not run both at the same time unless your memory is larger than 100G and disk space is larger than 200G"
echo "🔹 Please relogin or run 'source ~/.bashrc' if Go is not available after reboot."
EOF

chmod +x /tmp/setup_as_fuzz.sh

# Step 5: Execute the script as fuzz user
su - fuzz -c "/tmp/setup_as_fuzz.sh"


