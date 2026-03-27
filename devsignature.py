from cryptography.hazmat.primitives import serialization
from cryptography.exceptions import InvalidSignature
from cryptography.hazmat.primitives.asymmetric import ed25519

import struct

class ECSignature:

    @staticmethod
    # Loads a public key from raw bytes
    def key_from_bytes_public(key):
        return ed25519.Ed25519PublicKey.from_public_bytes(key)
    
    # Converts a public key to raw bytes
    @staticmethod
    def bytes_from_key_public(key : ed25519.Ed25519PublicKey):
        return key.public_bytes_raw()

    # Load public key file
    @staticmethod
    def load_public_key(filename):
        with open(filename, "rb") as key_file:
            return serialization.load_pem_public_key(key_file.read())
        
    # Load private key file
    @staticmethod
    def load_private_key(filename,password):
        with open(filename, "rb") as key_file:
            return serialization.load_pem_private_key(key_file.read(),password=password if password else None)
        
    # Convert UID string to bytes
    @staticmethod
    def processuid(uidstr):
        uidsplit = uidstr.split(":")
        devid = struct.pack(">iq",int(uidsplit[1]),int(uidsplit[0]))
        return devid

    # Sign a new device with private key
    @staticmethod
    def sign(devid : bytes,private_key,licensetype : bytes=b''):
        if licensetype == None:
            licensetype = b''

        signature = private_key.sign( devid+(licensetype))
        return signature

    # Verify if a device matches a signature object
    @staticmethod
    def check(devid : bytes,signature,public_key,licensetype : bytes=b''):
        if licensetype == None:
            licensetype = b''
        try:
            public_key.verify( signature,devid+(licensetype))
        except InvalidSignature:
            return False
        return True
    
    # Convert signature object to ints for storage
    @staticmethod
    def signature_to_ints(signature,le = False):
        return  struct.unpack( ("<" if le else ">" )+"qqqqqqqq",signature)

    # Convert r,s points to signature object
    @staticmethod
    def ints_to_signature(ints,le=False):
        signature = struct.pack( ("<" if le else ">")+"q"*len(ints),*ints)
        return bytes(signature)
