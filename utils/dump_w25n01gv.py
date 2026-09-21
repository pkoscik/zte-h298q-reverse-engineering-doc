#!/usr/bin/env python3
#
# W25N01GV (128MB SPI NAND) dumper for Raspberry Pi

import spidev
import time
import sys
import argparse
import hashlib

PAGES      = 65536
DATA_BYTES = 2048
OOB_BYTES  = 64
PAGE_BYTES = DATA_BYTES + OOB_BYTES

OP_RESET       = 0xFF
OP_JEDEC_ID    = 0x9F
OP_READ_STATUS = 0x0F
OP_PAGE_READ   = 0x13
OP_READ_CACHE  = 0x03
SR_STATUS_ADDR = 0xC0
BUSY_BIT       = 0x01

EXPECT_MFR = 0xEF
EXPECT_DEV = (0xAA, 0x21)

# pre-built read-cache command + dummy bytes for the full page
_READ_CACHE_CMD = [OP_READ_CACHE, 0x00, 0x00, 0x00] + [0x00] * PAGE_BYTES


def open_spi(speed):
    spi = spidev.SpiDev()
    spi.open(0, 0)
    spi.mode = 3
    spi.max_speed_hz = speed
    try:
        spi.no_cs = False
    except Exception:
        pass
    return spi


def wait_ready(spi, timeout_s=2.0):
    t0 = time.time()
    while True:
        st = spi.xfer2([OP_READ_STATUS, SR_STATUS_ADDR, 0x00])[2]
        if not (st & BUSY_BIT):
            return
        if time.time() - t0 > timeout_s:
            raise TimeoutError("chip stuck busy - check wiring")


def reset_chip(spi):
    spi.xfer([OP_RESET])
    time.sleep(0.001)
    wait_ready(spi)


def read_jedec(spi):
    r = spi.xfer2([OP_JEDEC_ID, 0x00, 0x00, 0x00, 0x00])
    return r[2], (r[3], r[4])


def probe(spi):
    reset_chip(spi)
    mfr, dev = read_jedec(spi)
    print(f"JEDEC ID: mfr=0x{mfr:02X} dev=0x{dev[0]:02X}{dev[1]:02X}")
    if mfr == EXPECT_MFR and dev == EXPECT_DEV:
        print("  -> Winbond W25N01GV detected.")
        return True
    print("  -> Unexpected ID!")
    return False


def read_page(spi, page):
    spi.xfer([OP_PAGE_READ, 0x00, (page >> 8) & 0xFF, page & 0xFF])
    wait_ready(spi)
    out = spi.xfer3(_READ_CACHE_CMD)
    return bytes(out[4:4 + DATA_BYTES])  # drop OOB


def dump(spi, outfile, start=0, count=PAGES):
    reset_chip(spi)
    h = hashlib.sha256()
    end = min(start + count, PAGES)
    t0 = time.time()
    last = t0

    with open(outfile, "wb") as fp:
        for page in range(start, end):
            data = read_page(spi, page)
            fp.write(data)
            h.update(data)

            now = time.time()
            if now - last > 0.5 or page == end - 1:
                done = page - start + 1
                total = end - start
                rate = done / (now - t0) if now > t0 else 0
                eta = (total - done) / rate if rate > 0 else 0
                sys.stdout.write(
                    f"\rPage {page+1}/{end} ({done*100//total}%)"
                    f"    {rate:5.0f} pg/s  ETA {eta:5.0f}s"
                )
                sys.stdout.flush()
                last = now

    print()
    elapsed = time.time() - t0
    nbytes = (end - start) * DATA_BYTES
    digest = h.hexdigest()
    print(f"Done. {nbytes} bytes ({nbytes/1024/1024:.1f} MiB) in {elapsed:.1f}s -> {outfile}")
    print(f"SHA256: {digest}")
    return digest


def main():
    ap = argparse.ArgumentParser(description="Dump W25N01GV SPI NAND via spidev")
    ap.add_argument("--probe", action="store_true", help="JEDEC ID check only")
    ap.add_argument("--verify", action="store_true", help="dump twice and compare")
    ap.add_argument("--speed", type=int, default=16_000_000, help="SPI clock in Hz")
    ap.add_argument("--start", type=int, default=0, help="first page number")
    ap.add_argument("--count", type=int, default=PAGES, help="pages to dump")
    ap.add_argument("--out", default="firmware.bin")
    args = ap.parse_args()

    spi = open_spi(args.speed)
    print(f"SPI clock: {args.speed/1e6:.1f} MHz")

    try:
        if args.probe:
            probe(spi)
            return

        if not probe(spi):
            print("Aborting.")
            return

        d1 = dump(spi, args.out, args.start, args.count)

        if args.verify:
            print()
            vfile = args.out.replace(".bin", "_verify.bin")
            d2 = dump(spi, vfile, args.start, args.count)
            if d1 == d2:
                print("\nVERIFY OK - dumps match.")
            else:
                print("\nVERIFY FAILED - try lowering speed.")
    finally:
        spi.close()


if __name__ == "__main__":
    main()
