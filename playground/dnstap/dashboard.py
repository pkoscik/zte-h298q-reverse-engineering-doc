#!/usr/bin/env python3
import sys, json, time, threading, subprocess
from pathlib import Path
from collections import deque, OrderedDict
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

PAGE = (Path(__file__).parent / "index.html").read_text()
PORT = 8088
MAX_EVENTS = 200
STATE_LOCK = threading.Lock()
DEVICES = OrderedDict()

FIELDS = ["frame.time_epoch", "eth.src", "ip.src", "dns.qry.name", "tls.handshake.extensions_server_name",
          "dhcp.option.hostname", "eth.src.oui_resolved", "ip.dst", "udp.dstport", "tcp.dstport"]


def device_for(mac, ip):
    key = mac or ip or "?"
    d = DEVICES.get(key)
    if d is None:
        d = {"mac": mac, "ip": ip, "hostname": None, "vendor": None,
             "first": time.time(), "last": time.time(),
             "events": deque(maxlen=MAX_EVENTS)}
        DEVICES[key] = d
    if ip:
        d["ip"] = ip
    return d


def feed_line(line):
    parts = line.rstrip("\n").split("\t")
    parts += [""] * (10 - len(parts))
    t_epoch, mac, ip, dns, sni, hostname, vendor, dst, uport, tport = parts[:10]
    if not (mac or ip):
        return None
    try:
        t = float(t_epoch) if t_epoch else time.time()
    except ValueError:
        t = time.time()
    with STATE_LOCK:
        d = device_for(mac.lower(), ip)
        d["last"] = t
        if hostname and not d["hostname"]:
            d["hostname"] = hostname
        if vendor and not d["vendor"]:
            d["vendor"] = vendor
        domain = (sni or dns).strip().rstrip(".")
        if domain:
            kind = "sni" if sni else "dns"
            d["events"].append({"t": t, "kind": kind, "domain": domain,
                                "dst": dst, "port": tport or uport})
            return kind
    return None


def tshark(nic):
    cmd = ["tshark", "-l", "-n", "-i", nic, "-T", "fields"]
    for f in FIELDS:
        cmd += ["-e", f]
    for line in subprocess.Popen(cmd, stdout=subprocess.PIPE, text=True).stdout:
        if line.strip():
            feed_line(line)


def snapshot():
    with STATE_LOCK:
        out = []
        for d in DEVICES.values():
            out.append({
                "name": d["hostname"] or d["vendor"] or d["ip"] or d["mac"],
                "mac": d["mac"], "ip": d["ip"], "vendor": d["vendor"],
                "first": d["first"], "last": d["last"],
                "events": list(d["events"]),
            })
    out.sort(key=lambda x: x["last"], reverse=True)
    return out




class Handler(BaseHTTPRequestHandler):
    def log_message(self, *a):
        pass

    def _send(self, body, ctype):
        b = body.encode() if isinstance(body, str) else body
        self.send_response(200)
        self.send_header("Content-Type", ctype)
        self.send_header("Content-Length", str(len(b)))
        self.end_headers()
        self.wfile.write(b)

    def do_GET(self):
        if self.path.startswith("/data"):
            self._send(json.dumps(snapshot()), "application/json")
        else:
            self._send(PAGE, "text/html; charset=utf-8")


def main():
    if len(sys.argv) != 2:
        sys.exit(f"usage: {sys.argv[0]} <nic>")
    nic = sys.argv[1]
    threading.Thread(target=tshark, args=(nic,), daemon=True).start()
    srv = ThreadingHTTPServer(("0.0.0.0", PORT), Handler)
    print(f"dashboard: http://localhost:{PORT}  (source: {nic})", file=sys.stderr)
    srv.serve_forever()


if __name__ == "__main__":
    main()
