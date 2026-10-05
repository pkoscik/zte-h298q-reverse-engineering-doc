# DOOM on the H298Q

## Build
```sh
./build.sh
```

## Serve
```sh
cd dist && python3 -m http.server 8080 --bind 0.0.0.0
```

## Run
No `chmod` on-device, so get the `exec` bit from `/bin/sh`, then `wget -O` over it:
```sh
cd /var
cp /bin/sh /var/doom
wget -O /var/doom      http://<HOST_IP>:8080/doom
wget -O /var/doom1.wad http://<HOST_IP>:8080/doom1.wad
/var/doom -iwad /var/doom1.wad -scaling 2
```
