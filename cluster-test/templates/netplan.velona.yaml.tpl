network:
  version: 2
  ethernets:
    eno2:
      mtu: 1500
      dhcp4: false
      dhcp6: false
      accept-ra: false
      link-local: []

    enp1s0f0np0:
      mtu: 9000
      dhcp4: false
      dhcp6: false
      accept-ra: false
      link-local: []

    enp1s0f1np1:
      mtu: 9000
      dhcp4: false
      dhcp6: false
      accept-ra: false
      link-local: []

  bonds:
    bond0:
      mtu: 9000
      dhcp4: false
      dhcp6: false
      accept-ra: false
      link-local: []
      interfaces:
        - enp1s0f0np0
        - enp1s0f1np1
      parameters:
        mode: 802.3ad
        lacp-rate: fast
        mii-monitor-interval: 100
        transmit-hash-policy: layer3+4

  bridges:
    # LAB-MAAS
    br0:
      addresses:
      - VELONA_IPV4/24
      - VELONA_IPV6/64
      nameservers:
        addresses:
        - 2602:fc62:b:3000::10
        search:
        - lab.maas.stgraber.net
      routes:
        - to: 0.0.0.0/0
          via: 172.17.30.1
        - to: ::/0
          via: 2602:fc62:b:3000::1
      mtu: 1500
      interfaces:
      - eno2

  vlans:
    # LAB-CLUSTER-MGMT
    bond0.3002:
      link: bond0
      id: 3002
      mtu: 9000
      dhcp4: false
      dhcp6: false
      accept-ra: false
      addresses:
        - 2602:fc62:b:3002::103/64
      routes:
        - to: 2602:fc62:b:100::/64
          via: 2602:fc62:b:3002::1

    # LAB-CLUSTER-UPLINK
    bond0.3003:
      link: bond0
      id: 3003
      mtu: 1500
      dhcp4: false
      dhcp6: false
      accept-ra: false
      link-local: []
