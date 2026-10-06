## Setup (on router)

Keep your monitoring device on LAN1 (eth0), the port everything mirrors to.

```sh
mirror add wlan0   eth0   # 2.4 GHz wifi
mirror add wlan5g0 eth0   # 5 GHz wifi
mirror add eth1    eth0   # LAN2
mirror add eth2    eth0   # LAN3
mirror add eth3    eth0   # LAN4
# mirror show   watch succ[]/packs() climb; mirror del <src> to stop
```

## Run

Needs `tshark`.

```sh
sudo python3 dashboard.py <iface>
# http://localhost:8088
```
