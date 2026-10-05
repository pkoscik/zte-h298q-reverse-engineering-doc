## Serve
```sh
python3 -m http.server 8080 --bind 0.0.0.0
```

## Run
```sh
cd /var
wget -O /var/blink.sh http://<HOST_IP>:8080/blink.sh
sh /var/blink.sh
```
