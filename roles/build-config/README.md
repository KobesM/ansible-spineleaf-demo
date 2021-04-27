# 'build-config' role
This role creates combines all the partial configurations of the other roles into one complete configuration files per router/switch.

 The following roles are combined:
- base
- underlay-ebgp
- overlay-evpn-spine
- overlay-evpn-leaf
- overlay-evpn-access
- intrusion-detection-system