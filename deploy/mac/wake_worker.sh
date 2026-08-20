#!/usr/bin/env bash
# Send a Wake-on-LAN magic packet from THIS Mac to another machine on the LAN.
#
# This is the relay that makes remote waking possible: the app cannot reach the
# sleeping PC, but it can queue a job on the Mac, which is on the same network
# and can broadcast to it. Usage: wake_worker.sh <MAC> [broadcast-ip]
set -uo pipefail
MAC="${1:-}"
BCAST="${2:-255.255.255.255}"
[ -z "$MAC" ] && { echo "usage: wake_worker.sh <MAC> [broadcast]"; exit 1; }

CLEAN=$(echo "$MAC" | tr 'A-F' 'a-f' | tr -d ':-')
[ ${#CLEAN} -ne 12 ] && { echo "that is not a MAC address: $MAC"; exit 1; }

python3 - "$CLEAN" "$BCAST" <<'PY'
import socket, sys, binascii
mac, bcast = sys.argv[1], sys.argv[2]
# A magic packet is 6 x 0xFF followed by the target MAC repeated 16 times.
pkt = b'\xff' * 6 + binascii.unhexlify(mac) * 16
s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
s.setsockopt(socket.SOL_SOCKET, socket.SO_BROADCAST, 1)
for port in (9, 7):
    s.sendto(pkt, (bcast, port))
print(f"magic packet sent to {mac} via {bcast} on ports 9 and 7")
PY

echo "The packet is fire-and-forget - nothing acknowledges it."
echo "If the box does not appear in the app within about 2 minutes, then either"
echo "wake-on-LAN is off in its BIOS, Fast Startup is still on, or the PSU has"
echo "no standby power (mains actually out). Nothing on the network can fix that."
