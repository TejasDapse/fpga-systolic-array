#!/usr/bin/env bash
# One-time setup for the Ubuntu build/test machine (Ubuntu 22.04 LTS, x86-64).
# Installs simulation tools, USB-Blaster + UART permissions, the Python venv,
# then runs the simulation regression. Quartus itself is installed manually
# (see docs/UBUNTU_HANDOFF.md, step 2).
#
#   ./tools/setup_ubuntu.sh
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT"

echo "== 1/5 apt packages =="
sudo apt update
sudo apt install -y git iverilog gtkwave python3-venv python3-pip \
    libxft2 libxext6 libxtst6 libxi6
# Quartus needs these older libs; they exist on 22.04 but not on 24.04.
sudo apt install -y libncurses5 libtinfo5 \
    || echo "WARN: libncurses5/libtinfo5 not found (Ubuntu 24.04?). See docs/UBUNTU_HANDOFF.md."

echo "== 2/5 USB-Blaster udev rule =="
RULE=/etc/udev/rules.d/51-usbblaster.rules
sudo tee "$RULE" >/dev/null <<'EOF'
# Intel/Altera USB-Blaster (DE10-Lite on-board) and USB-Blaster II
SUBSYSTEM=="usb", ATTR{idVendor}=="09fb", ATTR{idProduct}=="6001", MODE="0666"
SUBSYSTEM=="usb", ATTR{idVendor}=="09fb", ATTR{idProduct}=="6010", MODE="0666"
SUBSYSTEM=="usb", ATTR{idVendor}=="09fb", ATTR{idProduct}=="6810", MODE="0666"
EOF
sudo udevadm control --reload-rules
sudo udevadm trigger

echo "== 3/5 serial port access (USB-UART adapter) =="
if id -nG "$USER" | grep -qw dialout; then
    echo "already in dialout group"
else
    sudo usermod -aG dialout "$USER"
    echo "Added $USER to dialout -> LOG OUT AND BACK IN before using /dev/ttyUSB0"
fi

echo "== 4/5 Python venv =="
[ -d .venv ] || python3 -m venv .venv
.venv/bin/pip install -q --upgrade pip
.venv/bin/pip install -q -r requirements.txt

echo "== 5/5 simulation regression =="
iverilog -V 2>&1 | head -1
(cd tb && ../.venv/bin/pytest -q)

echo
if command -v quartus_sh >/dev/null; then
    echo "Quartus found: $(quartus_sh --version | grep -m1 Version)"
else
    echo "Quartus NOT in PATH yet -> install it (docs/UBUNTU_HANDOFF.md step 2)."
fi
echo "Setup done."
