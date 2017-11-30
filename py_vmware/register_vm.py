#!/usr/bin/env python
"""
Written by Matt kirby
github: https://github.com/mattkirby
Email: kirby@puppet.com
Register VM to a target folder by storage path
"""
import argparse
import py_vmware.vmware_lib as vmware_lib
import getpass
import sys
from tools import tasks


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

    parser.add_argument('-v', '--vm-name',
                        required=True,
                        action='store',
                        help='Name of the VM to register')

    parser.add_argument('--vm-path',
                        required=False,
                        action='store',
                        help='Full path to VM')

    parser.add_argument('--datacenter-name',
                        required=False,
                        action='store',
                        default=None,
                        help='Name of the Datacenter you\
                            wish to use. If omitted, the first\
                            datacenter will be used.')

    parser.add_argument('--vm-folder',
                        required=True,
                        action='store',
                        help='Name of the target folder')

    parser.add_argument('--datastore-name',
                        required=True,
                        action='store',
                        help='Datastore to find the target VM')

    parser.add_argument('--cluster-name',
                        required=True,
                        action='store',
                        help='Target cluster for VM registration')

    parser.add_argument('-i', '--insecure',
                        required=False,
                        action='store_true',
                        help='disable ssl validation')

    args = parser.parse_args()

    if not args.password:
        args.password = getpass.getpass(
            prompt='Enter password')

    return args


def main():
    args = get_args()

    si = vmware_lib.connect(args.host, args.user, args.password, args.port, args.insecure)
    content = si.RetrieveContent()

    folder = vmware_lib.get_obj(content, [vmware_lib.vim.Folder], args.vm_folder)
    if not folder:
        print 'Cannot find folder {}'.format(args.vm_folder)
        sys.exit(1)

    cluster = vmware_lib.get_obj(content, [vmware_lib.vim.ClusterComputeResource], args.cluster_name)
    if not cluster:
        print 'Cannot find cluster {}'.format(args.cluster_name)
        sys.exit(1)

    resource_pool = cluster.resourcePool
    if args.vm_path:
        full_path = args.vm_path
    else:
        full_path = '{}/{}.vmx'.format(args.vm_name, args.vm_name)
    datastore_path = '[{}] {}'.format(args.datastore_name, full_path)

    print 'Registering {}'.format(args.vm_name)
    folder.RegisterVm(datastore_path, args.vm_name, False, resource_pool)

# start this thing
if __name__ == "__main__":
    main()
