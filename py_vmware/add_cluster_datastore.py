#!/usr/bin/env python
"""
Add a datastore to a host or cluster
"""

import argparse
import py_vmware.vmware_lib as vmware_lib


def get_args():
    """ Get arguments from CLI """
    parser = argparse.ArgumentParser(
        description='Arguments for talking to vCenter')

    parser.add_argument('-s', '--host',
                        required=True,
                        action='store',
                        help='vSphere service to connect to')

    parser.add_argument('-o', '--port',
                        type=int,
                        default=443,
                        action='store',
                        help='Port to connect on')

    parser.add_argument('-u', '--user',
                        required=True,
                        action='store',
                        help='Username to use')

    parser.add_argument('-p', '--password',
                        required=False,
                        action='store',
                        help='Password to use')

    parser.add_argument('--datacenter-name',
                        required=False,
                        action='store',
                        default=None,
                        help='Name of the Datacenter you\
                            wish to use. If omitted, the first\
                            datacenter will be used.')

    parser.add_argument('-i', '--insecure',
                        required=False,
                        action='store_true',
                        help='disable ssl validation')

    parser.add_argument('-e', '--esxi_host',
                        action='store',
                        help='host to add datastore to')

    parser.add_argument('-c', '--cluster',
                        action='store',
                        help='cluster to add datastore to')

    parser.add_argument('-d', '--datastore',
                        action='store',
                        help='path to NFS datastore target - $server:/mount/point')

    parser.add_argument('--local_datastore_name',
                        action='store',
                        help='Name of volume when mounted, if different than the remote path')

    parser.add_argument('-m', '--mount',
                        action='store_true',
                        help='Whether to mount the volume')

    parser.add_argument('--unmount',
                        action='store_true',
                        help='Whether to unmount the volume')

    args = parser.parse_args()
    return args

def main():
    """Add datastore to cluster or host"""
    args = get_args()

    si = vmware_lib.connect(
        args.host, args.user, args.password, args.port, args.insecure)
    content = si.RetrieveContent()
    dsspec = vmware_lib.datastore_spec(args.datastore, args.local_datastore_name)

    if args.mount:
        if args.cluster:
            try:
                cluster = vmware_lib.get_obj(content, [vmware_lib.vim.ClusterComputeResource], args.cluster)
                for host in cluster.host:
                    mount = vmware_lib.mount_datastore(dsspec, host)
                    if mount == True:
                        print 'Successfully mounted {} on {}'.format(args.datastore, host.name)
                    else:
                        print mount
            except:
                return 'Could not mount {} on {}'.format(dsspec.localPath, args.cluster)
        elif args.esxi_host:
            try:
                host = vmware_lib.get_obj(content, [vmware_lib.vim.HostSystem], args.esxi_host)
                mount = vmware_lib.mount_datastore(dsspec, host)
                if mount == True:
                    print 'Successfully mounted {} on {}'.format(args.datastore, host.name)
                else:
                    print mount
            except:
                raise
                print 'Failed to mount {} on {}'.format(args.datastore, args.esxi_host)
    elif args.unmount:
        print 'reached unmount'
        if args.cluster:
            cluster = vmware_lib.get_obj(content, [vmware_lib.vim.ClusterComputeResource], args.cluster)
            for host in cluster.host:
                if vmware_lib.unmount_datastore(dsspec.localPath, host):
                    print 'Unmounted {} on {}'.format(dsspec.localPath, host.name)
                else:
                    '{} is not mounted on {}'.format(dsspec.localPath, host.name)
        elif args.esxi_host:
            print 'reached host'
            host = vmware_lib.get_obj(content, [vmware_lib.vim.HostSystem], args.esxi_host)
            if vmware_lib.unmount_datastore(dsspec.localPath, host):
                print 'Successfully unmounted {} on {}'.format(dsspec.localPath, host.name)
            else:
                print '{} is not mounted on {}'.format(dsspec.localPath, host.name)
        else:
            print 'No host or cluster were provided to unmount the volume'
    else:
        print 'No mount or unmount action was specified'

if __name__ == "__main__":
    main()
