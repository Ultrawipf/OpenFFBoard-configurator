import sys,struct,zlib,os
import argparse

address = 0x8000000
DEFAULT_DEVICE="0x0483:0xdf11"

# (Start,length) to skip eeprom emulation sectors
flash_sectors_f4 = [
(0x8000000,0x4000),(0x800C000,-1) # multiple sectors combined. -1 size for rest
]

def compute_crc(data):
    return 0xFFFFFFFF & -zlib.crc32(data) -1
def build(file,targets,device=DEFAULT_DEVICE):
    data = b''
    for t,target in enumerate(targets):
        tdata = b''
        for image in target:
          tdata += struct.pack('<2I',image['address'],len(image['data']))+image['data']
        tdata = struct.pack('<6sBI255s2I',b'Target',0,1, b'ST...',len(tdata),len(target)) + tdata
        data += tdata
    data  = struct.pack('<5sBIB',b'DfuSe',1,len(data)+11,len(targets)) + data
    v,d=map(lambda x: int(x,0) & 0xFFFF, device.split(':',1))
    data += struct.pack('<4H3sB',0,d,v,0x011a,b'UFD',16)
    crc   = compute_crc(data)
    data += struct.pack('<I',crc)
    open(file,'wb').write(data)

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Convert bin to dfu")
    parser.add_argument('binary',  type=str, help="bin file input")
    parser.add_argument('--address', type=str, help="flash address. Default 0x8000000",default = "0x8000000")
    #parser.add_argument('--addroffset', type=str, help="flash address offset after eeprom emulation. Default 0xc000",default = "0xc000")
    parser.add_argument('--out', nargs='?', type=str,help = ".dfu file output",default = None)

    args = parser.parse_args()
    binfile = args.binary
    outfile = args.out

    if not outfile:
        outfile = binfile.replace(".bin","") + ".dfu"
    if(args.address):
        address = int(args.address,0)
    # if(args.addroffset):
    #     addroffset = int(args.addroffset,0)

    if not os.path.isfile(binfile):
        print("Invalid file '%s'." % binfile)
    data = bytes(open(binfile,'rb').read())

    ## F4 targets
    target = []
    for page in flash_sectors_f4:
        start_offset = page[0]-address
        if start_offset > len(data):
            break
        print("Appending %x - %x" % (page[0],page[0]+page[1]))
        stop = min(start_offset+page[1],len(data))
        if page[1] == -1:
            stop = len(data)
        print("%x - %x" % (start_offset,stop))
        target.append({'address': page[0], 'data': data[start_offset:stop]})

    print("Saving to", outfile)
    build(outfile,[target],DEFAULT_DEVICE)
