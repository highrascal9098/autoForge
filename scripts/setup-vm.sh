#!/usr/bin/env bash
# Run ONCE on the Oracle VM as root/sudo, BEFORE docker compose.
# 1GB RAM cannot hold n8n + Chromium without swap — this creates 4GB.
set -euo pipefail
if ! swapon --show | grep -q '^/swapfile'; then
  fallocate -l 4G /swapfile || dd if=/dev/zero of=/swapfile bs=1M count=4096
  chmod 600 /swapfile
  mkswap /swapfile
  swapon /swapfile
  grep -q '^/swapfile' /etc/fstab || echo '/swapfile none swap sw 0 0' >> /etc/fstab
fi
sysctl -w vm.swappiness=10
grep -q 'vm.swappiness' /etc/sysctl.conf || echo 'vm.swappiness=10' >> /etc/sysctl.conf

# UFW: SSH only. n8n/dashboard are never public.
ufw allow OpenSSH >/dev/null 2>&1 || true
ufw --force enable >/dev/null 2>&1 || true

free -h
echo "VM ready. Now: cp .env.example .env, fill it, put storage_state.json in data/linkedin/, then ./scripts/bootstrap.sh"
