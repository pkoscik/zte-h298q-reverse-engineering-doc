## Build
```sh
./build.sh
```

## Serve
```sh
cd dist && python3 -m http.server 8099 --bind 0.0.0.0
```

## Run
```sh
cd /var && mkdir -p www
cp /bin/sh /var/httpd
wget -O /var/httpd            http://<HOST_IP>:8099/httpd
wget -O /var/www/index.html   http://<HOST_IP>:8099/index.html
killall httpd
/var/httpd 8080 /var/www &
# cspd restarts stock httpd on :80 immedietaly after killing it, hijack the port routing instead
iptables -t nat -A PREROUTING -p tcp --dport 80 -j REDIRECT --to-port 8080
```
