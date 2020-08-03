from __future__ import print_function
import base64
import os
import hashlib
import struct
import sys

# refer to https://stackoverflow.com/a/53016240/2613194

# This is the password we wish to encode
password = sys.argv[1]

# 1.Generate a random 32 bit salt:
salt = os.urandom(4)

# 2.Concatenate that with the UTF-8 representation of the plaintext password
step2 = salt + password.encode("utf-8")

# 3. Take the SHA256 hash and get the bytes back
step3 = hashlib.sha256(step2).digest()

# 4. Concatenate the salt again:
salted_hash = salt + step3

# 5. convert to base64 encoding:
password_hash = base64.b64encode(salted_hash)

print(password_hash.decode("utf-8"))