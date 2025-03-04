all:
  vars:
    ceph_fsid: "e2850e1f-7aab-472e-b6b1-824e19a75071"
    ceph_rbd_cache: "2048Mi"
    ceph_rbd_cache_max: "1792Mi"
    ceph_rbd_cache_target: "1536Mi"
    ceph_release: "distro"

    incus_name: "baremetal"
    incus_release: "stable"

    ovn_name: "baremetal"
    ovn_az_name: "zone1"
    ovn_release: "distro"
  children:
    baremetal:
      vars:
        ansible_become: "yes"
        ansible_user: "ubuntu"

        ceph_roles:
          - client
          - mon
          - mds
          - mgr
          - osd

        incus_ip_address: "{{ cluster_address }}"
        incus_init:
          network:
            LOCAL:
              type: physical
              local_config:
                parent: br0
              description: Directly attach to host networking
            UPLINK:
              type: physical
              config:
                ipv4.gateway: "172.17.33.1/24"
                ipv6.gateway: "2602:fc62:b:3003::1/64"
                ipv4.ovn.ranges: "172.17.33.100-172.17.33.254"
                dns.nameservers: "1.1.1.1,1.0.0.1"
              local_config:
                parent: bond0.3003
              description: Physical network for OVN routers
            default:
              type: ovn
              config:
                network: UPLINK
              default: true
              description: Initial OVN network
          storage:
            local:
              default: true
              driver: zfs
              local_config:
                source: "/dev/disk/by-id/{{ incus_local_disk }}"
              description: Local storage pool
            remote:
              driver: ceph
              local_config:
                source: "incus_{{ incus_name }}"
              description: Distributed storage pool (cluster-wide)
        incus_roles:
          - cluster
          - ui

        ovn_ip_address: "{{ cluster_address }}"
        ovn_roles:
          - central
          - host

      hosts:
        asuras:
          ansible_ssh_host: ASURAS_IPV6
          cluster_address: 2602:fc62:b:3002::101
          ceph_disks:
            - data: ata-SAMSUNG_MZ7LM1T9HMJP-00005_S2TVNX0K602532
            - data: ata-SAMSUNG_MZ7LM1T9HMJP-00005_S2TVNX0K602761
            - data: ata-SAMSUNG_MZ7LM1T9HMJP-00005_S2TVNX0K604640
          incus_local_disk: ata-SAMSUNG_MZ7LM1T9HMJP-00005_S2TVNX0K409253

        entak:
          ansible_ssh_host: ENTAK_IPV6
          cluster_address: 2602:fc62:b:3002::102
          ceph_disks:
            - data: ata-SAMSUNG_MZ7LM1T9HMJP-00005_S2TVNX0K409270
            - data: ata-SAMSUNG_MZ7LM1T9HMJP-00005_S2TVNX0K602861
            - data: ata-SAMSUNG_MZ7LM1T9HMJP-00005_S2TVNX0KC11784
          incus_local_disk: ata-SAMSUNG_MZ7LM1T9HMJP-00005_S2TVNX0K408983

        velona:
          ansible_ssh_host: VELONA_IPV6
          cluster_address: 2602:fc62:b:3002::103
          ceph_disks:
            - data: ata-SAMSUNG_MZ7LM1T9HMJP-00005_S2TVNX0K411490
            - data: ata-SAMSUNG_MZ7LM1T9HMJP-00005_S2TVNX0K412096
            - data: ata-SAMSUNG_MZ7LM1T9HMJP-00005_S2TVNX0K602551
          incus_local_disk: ata-SAMSUNG_MZ7LM1T9HMJP-00005_S2TVNX0K410283
