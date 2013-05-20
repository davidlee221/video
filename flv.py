# flv.py
# 2013/05/18-
# @fand

import sys
import copy
import random
import binascii


with open(sys.argv[1], "rb") as f:
    binary = f.read()

i = 13

codec = 0
first = True
while i < len(binary):
    if not (binary[i] in ["\x08", "\x09", "\x12"]):
        i += 4
        continue
    
    l = i + 11 + (ord(binary[i+1]) * 0x10000 +
                  ord(binary[i+2]) * 0x100 +
                  ord(binary[i+3]))

    # damage keyframes
    if binary[i] == "\x09" and ord(binary[i+11]) & 0xf0 == 0x10:
        if first:
            first = False
            continue

        codec = ord(binary[i+11]) & 0x0f
        s = ""
        for j in range(i+13, l):
            if random.random() < 0.2:
                s += chr(random.randint(60, 230))
            else:
                s += binary[j]
        binary = binary[:i+13] + s + binary[l:]

    # damage audio
    elif binary[i] == "\x08" and random.random() < 0.3:
        s = ""
        for j in range(i+15, l):
            if random.random() < 0.1:
                s += chr(random.randint(30, 230))
            else:
                s += binary[j]
        binary = binary[:i+15] + s + binary[l:]
    
    i = l+4
    

with open("/vmshare/out.flv", "wb") as f:
    f.write(binary)
    



