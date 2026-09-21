#!/usr/bin/env python3
#
# Usage:
#   ./rootfs_ramcarve.py --probe 0x80020000
#   ./rootfs_ramcarve.py --scan --uncached

import argparse, re, sys, time

PROMPT  = b'bldr>'
HEXLINE = re.compile(rb'^([0-9a-fA-F]{8})\s+([0-9a-fA-F .]+?)\s*\|')

MARKERS = {
    b'hsqs':    'squashfs le superblock',
    b'sqsh':    'squashfs be superblock',
    b'\x7fELF': 'ELF binary',
    b'BusyBox': 'busybox banner',
    b'/bin/sh': 'shell path',
}


def open_port(port, baud):
    import serial
    return serial.Serial(port, baud, timeout=0.4)


def cmd(ser, line, settle=0.15):
    ser.reset_input_buffer()
    ser.write(line.encode() + b'\r')
    time.sleep(settle)
    buf = b''
    idle = 0
    while idle < 8:
        chunk = ser.read(4096)
        if chunk:
            buf += chunk; idle = 0
            if PROMPT in buf: break
        else:
            idle += 1
    return buf


def parse_dump(out):
    data = bytearray()
    for line in out.splitlines():
        m = HEXLINE.match(line.strip())
        if not m:
            continue
        for t in m.group(2).replace(b'.', b' ').split():
            if len(t) == 2 and re.fullmatch(rb'[0-9a-fA-F]{2}', t):
                data += bytes.fromhex(t.decode())
    return bytes(data)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('-v', '--verbose', action='store_true')
    ap.add_argument('--port', default='/dev/ttyACM0')
    ap.add_argument('--baud', type=int, default=115200)
    ap.add_argument('--probe', type=lambda x: int(x, 16))
    ap.add_argument('--scan', action='store_true')
    ap.add_argument('--uncached', action='store_true')
    ap.add_argument('--start', type=lambda x: int(x, 16), default=0x80020000)
    ap.add_argument('--end',   type=lambda x: int(x, 16), default=0x90000000)
    ap.add_argument('--stride', type=lambda x: int(x, 16), default=0x10000)
    a = ap.parse_args()
    ser = open_port(a.port, a.baud)

    if a.probe is not None:
        raw = cmd(ser, f"dump {a.probe:x} 40")
        print(raw.decode('latin1'))
        print("parsed %d bytes: %s" % (len(parse_dump(raw)), parse_dump(raw).hex()))
        return

    if a.scan:
        probe = 0x200
        seen = {}
        span = max(1, a.end - a.start)
        for base in range(a.start, a.end, a.stride):
            addr = base + (0x20000000 if a.uncached else 0)
            data = parse_dump(cmd(ser, f"dump {addr:x} {probe:x}", settle=0.03))
            for mk, desc in MARKERS.items():
                if mk in data:
                    off = data.find(mk)
                    print(f"[HIT] 0x{base+off:08x}  {mk!r:22} {desc}")
                    seen.setdefault(mk, []).append(base + off)
            pct = 100 * (base - a.start) / span
            preview = data[:16].hex(' ') if data else '<no data>'
            if a.verbose:
                print(f"[{pct:5.1f}%] 0x{base:08x}: {data[:probe].hex(' ')}")
            else:
                sys.stderr.write(f"\r[{pct:5.1f}%] 0x{base:08x}  {preview}   ")
                sys.stderr.flush()
        sys.stderr.write("\n=== summary ===\n")
        if not seen:
            print("nothing found :(")
        for mk, addrs in seen.items():
            print(f"  {mk!r:22} x{len(addrs):<4} first@0x{addrs[0]:08x}  {MARKERS[mk]}")
        return

    ap.print_help()


if __name__ == '__main__':
    main()
