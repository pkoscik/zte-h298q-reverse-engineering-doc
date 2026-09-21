#!/usr/bin/env python3

import sys
from Crypto.Cipher import AES

KEY = b'H298Q068e7bbb599'
ROOTFS_OFFSET = 0x1540000
ROOTFS_SIZE   = 0xA2DD90

infile = sys.argv[1] if len(sys.argv) > 1 else 'firmware-dump1.bin'
blob = open(infile, 'rb').read()[ROOTFS_OFFSET:ROOTFS_OFFSET + ROOTFS_SIZE]

aligned = len(blob) // 16 * 16
dec = AES.new(KEY, AES.MODE_ECB).decrypt(blob[:aligned])

outfile = 'rootfs.decrypted.bin'
open(outfile, 'wb').write(dec)
print(f"{dec[:4]}  ->  {outfile}")
