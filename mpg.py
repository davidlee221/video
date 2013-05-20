# mpg.py
# 2013/05/15-
# @fand

import sys
import os.path
import struct
import copy
import random
import binascii
import tempfile

import time
import gc

##########################
# global elements
##########################
CODE = {
    "PACK" : "\x00\x00\x01\xBA",
    "SEQ"  : "\x00\x00\x01\xB3",
    "FRAME": "\x00\x00\x01\x00"
    }

PCT = ["O", "I", "P", "B", "D", "O", "O", "O"]

BUFFER_SIZE = 512 * 1024 * 1024

def getTime():
    new = time.time()
    while True:
        old = new
        new = time.time()
        yield new - old

class MPG:

    def __init__(self, src):
        t = getTime()
        self.src = open(src, "rb")
        self.video = tempfile.TemporaryFile()
        self.audio = tempfile.TemporaryFile()        
        print "opened file : %f sec" % t.next()

        self.binary = self.src.read()
        self.src_size = len(self.binary)

        self.pack = self.bin2pack(self.binary)
        print "pack : %f sec" % t.next()

        self.packet = self.bin2packet(self.binary)
        print "packet : %f sec" % t.next()
        
        self.offset_video = self.getStream(self.video, "v")
        print "video stream : %f sec" % t.next()
        
        self.offset_audio = self.getStream(self.audio, "a")
        print "audio stream : %f sec" % t.next()

        print "source size: %d" % os.path.getsize(src)
        print "source size: %d" % len(self.binary)

#        self.seq = self.bin2seq(self.video)
#        print "seq : %f sec" % t.next()
#        self.frame = self.seq2frame()
        print "inited : %f sec" % t.next()


    def __del__(self):
        self.src.close()
        self.video.close()
        self.audio.close()                    
        
        
    def bin2pack(self, src):

        packs = []
        last_pack = len(src)

        while True:
            i = src[:last_pack].rfind(CODE["PACK"])
            if i == -1:
                break
            else:
                z = long(binascii.b2a_hex(src[i+4:i+14]), 16)

                # MPEG 1
                if (z & 0xF1000100018000010000) == 0x21000100018000010000:
                    packs.append((i, i+12, last_pack))
                    
                # MPEG 2
                elif (z & 0xC4000400040100000300) == 0x44000400040100000300:
                    packs.append((i, i+14, last_pack))

                last_pack = i

        packs.reverse()
        return packs


    def bin2packet(self, src):
        packet = []
        
        for p in self.pack:
            ppp = []

            buf = src[p[1]:p[2]]
            
            last_packet = last_i = p[2]
            
            while True:
                i = buf[:last_i].rfind("\x00\x00\x01")
                if i == -1:
                    break
                if not(0xBC <= ord(buf[i+3]) <= 0xFF):
                    last_i = i
                    continue
                
                z = long(binascii.b2a_hex(src[i+3]), 16)

                # video packet
#                if (z & 0xF0) == 0xE0:
                if 0xE0 <= z < 0xF0:
                    ppp.append((p[1]+i, p[1]+i+4, p[1]+last_packet, "v"))

                # audio packet
                elif 0xC0 <= z < 0xE0:
                    ppp.append((p[1]+i, p[1]+i+4, p[1]+last_packet, "a"))

                # others
                else:
                    ppp.append((p[1]+i, p[1]+i+4, p[1]+last_packet, "o"))
                    
                last_packet = last_i = i
                
            packet += reversed(ppp)
        return packet


    def getStream(self, dst, query):
        
        offset = []
        
        for p in filter(lambda x: x[3] == query, self.packet):

            len_p = ord(self.binary[p[1]]) * 256 + ord(self.binary[p[1]+1])
            
#            i = p[1] + 2    # pass "packet length" area
            i = 2    # pass "packet length" area            
            
            while True:
                flag = ord(self.binary[i])
                if flag == 0xFF:    # Stuffing bytes(11)
                    i += 1
                    continue
                elif flag & 0xC0 == 0x40:    # MPEG1 STD(01)
                    i += 2
                    continue

                elif flag & 0xC0 == 0x80:    # MPEG2 PES(10)
                    i += 3
                    break
                
                # PTS or DTS(00)
                elif flag & 0xF0 == 0x00:
                    i += 1
                    break
                elif flag & 0xF0 == 0x20:
                    i += 5
                    break
                elif flag & 0xF0 == 0x30:
                    i += 10
                    break
                else:
                    print "strange packet! %0x" % flag
                    break

            l = p[1] + i
            r = p[1] + 2 + len_p
            dst.write(self.binary[l : r])
            offset.append((l, r, r-l))    # (start, end, length)
            
        return offset


    def bin2seq(self, _src):

        seqs = []
        _src.seek(0)
        src = _src.read()
        
        last_seq = len(src)
        
        while True:
            i = src[:last_seq].rfind(CODE["SEQ"])
            if i == -1:
                break
            else:    
                seqs.append((i + 4, last_seq))
                last_seq = i
                
        self.video_header = src[:last_seq]
        seqs.reverse()
        return seqs

    

    # def bin2seq(self, src):

    #     seqs = []
    #     last_seq = self.src_size
    #     buf_size = BUFFER_SIZE
    #     offset = last_seq - buf_size
    #     final = False

    #     if offset <= 0:
    #         buf_size += offset
    #         offset = 0
    #         final = True
        
    #     count = 0
    #     while True:
    #         src.seek(offset)
    #         buf = src.read(buf_size)
    #         i = buf.rfind(CODE["SEQ"])
    #         if i == -1:
    #             if final:
    #                 break
    #             else:
    #                 offset -= buf_size
    #         else:    
    #             seqs.append((offset + i + 4, last_seq))
                
    #             last_seq = offset + i
    #             offset = last_seq - buf_size
            
    #         if offset <= 0:
    #             buf_size += offset
    #             offset = 0
    #             final = True

    #     src.seek(0)
    #     self.video_header = src.read(last_seq)
    #     seqs.reverse()
    #     return seqs

    
    def output(self, dst):
        
        offsets = (map(lambda x:x+("v",0), self.offset_video) +
                   map(lambda x:x+("a",0), self.offset_audio))
        offsets.sort()

        print offsets[:5]

        f_out = open(dst, "wb")
        last = 0

        self.video.seek(0)
        self.audio.seek(0)
        
        for o in offsets:
            f_out.write(self.binary[last:o[0]])
            if o[3] == 'v':
                s = self.video.read(o[2])
                f_out.write(s)
            else:
                s = self.audio.read(o[2])
                f_out.write(s)
            last = o[1]
        f_out.write(self.binary[last:])
        f_out.close()

    
    
    def frame(self, *_type):
        query = _type
        if len(query) == 0:
            query = ["I", "P", "B", "D", "O"]
        l = []
        for s in self.seq:
            for f in s.frame:
                if f.type in query:
                    l.append(f)
        return l

    
    def remove(self, f):
        for s in self.seq:
            if f in s.frame and len(s) > 1:
                i = s.frame.index(f)
                s.frame[i] = s.frame[i-1] if i>1 else s.frame[i+1]
                break

    def swap(self, old, new):
        for s in self.seq:
            if old in s.frame:
                i = s.frame.index(old)
                s.frame.insert(i, copy.copy(new))
                s.frame.remove(old)
                break
            
    def slide(self):
        first = True
        replace = True
        last = self.seq[0].frame[0]
        for s in self.seq:
            ff = []
            for f in s.frame:
                if f.type == "I":
                    if first:
                        first = False
                        ff.append(f)
                    replace = True
                elif f.type in ["P", "B"]:
                    if replace:
                        last = f
                        replace = False
                    ff.append(last)
                else:
                    ff.append(f)
            s.frame = copy.copy(ff)
            

        
    
class MPG_Frame:


    def __init__(self, binary):
        self.binary = binary
        i = (ord(binary[0]) & 0b00111000) >> 3
        self.type = MPG_Frame.PCT[i]

    def output(self, dst):
        dst.write(CODE["FRAME"] + self.binary)
            
    def randomize(self):
        b = ""
        for i in self.binary:
            b += chr(random.randint(20,255))

#        s = self.binary.partition("\x00\x00\x01\x01")
#        b = s[0] + s[1]
#        ss = s[2]
#        for c in ss:
#            b += chr((~(ord(c))) & 0xFF)
#            b += chr(random.randint(20,255))
        self.binary = b

        

        
if __name__=="__main__":
    if len(sys.argv) != 2:
        print "Usage : python glitch.py [input]"
        exit()

    g = MPG(sys.argv[1])

#    for f in g.frame("I"):
#        f.randomize()

    g.output("/vmshare/gli.mpg")




