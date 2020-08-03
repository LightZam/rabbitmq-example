#!/bin/bash

# ''' ip change action '''
# python federation-mesh.py -c 172.88.0.2 -l 172.88.0.2 172.88.0.3 172.88.0.4
# python federation-mesh.py -c 172.88.0.3 -l 172.88.0.2 172.88.0.3 172.88.0.4
# python federation-mesh.py -c 172.88.0.4 -l 172.88.0.2 172.88.0.3 172.88.0.4

# python federation-mesh.py -c 172.88.0.5 -l 172.88.0.5 172.88.0.3 172.88.0.4
# python federation-mesh.py -c 172.88.0.3 -l 172.88.0.5 172.88.0.3 172.88.0.4
# python federation-mesh.py -c 172.88.0.4 -l 172.88.0.5 172.88.0.3 172.88.0.4


# ''' join '''
python federation-mesh.py -c 172.88.0.2 -l 172.88.0.2 172.88.0.3 172.88.0.4 172.88.0.5
python federation-mesh.py -c 172.88.0.3 -l 172.88.0.2 172.88.0.3 172.88.0.4 172.88.0.5
python federation-mesh.py -c 172.88.0.4 -l 172.88.0.2 172.88.0.3 172.88.0.4 172.88.0.5
python federation-mesh.py -c 172.88.0.5 -l 172.88.0.2 172.88.0.3 172.88.0.4 172.88.0.5

# ''' remove '''
# python federation-mesh.py -c 172.88.0.2
# python federation-mesh.py -c 172.88.0.2
# python federation-mesh.py -c 172.88.0.2
# python federation-mesh.py -c 172.88.0.3
# python federation-mesh.py -c 172.88.0.3
# python federation-mesh.py -c 172.88.0.3
# python federation-mesh.py -c 172.88.0.4
# python federation-mesh.py -c 172.88.0.4
# python federation-mesh.py -c 172.88.0.4
# python federation-mesh.py -c 172.88.0.5
# python federation-mesh.py -c 172.88.0.5
# python federation-mesh.py -c 172.88.0.5


# ''' remove '''
# python federation-mesh.py -c 172.88.0.2 -l 172.88.0.2 172.88.0.3 172.88.0.4
# python federation-mesh.py -c 172.88.0.3 -l 172.88.0.2 172.88.0.3 172.88.0.4
# python federation-mesh.py -c 172.88.0.4 -l 172.88.0.2 172.88.0.3 172.88.0.4


# # ''' join '''
# python federationmq.py -c 172.88.0.2 -l 172.88.0.2 172.88.0.3 172.88.0.4 172.88.0.5
# python federationmq.py -c 172.88.0.3 -l 172.88.0.2 172.88.0.3 172.88.0.4 172.88.0.5
# python federationmq.py -c 172.88.0.4 -l 172.88.0.2 172.88.0.3 172.88.0.4 172.88.0.5
# python federationmq.py -c 172.88.0.5 -l 172.88.0.2 172.88.0.3 172.88.0.4 172.88.0.5