#!/usr/bin/env python
"""
Empty a datastore

This program will find a datastore by name and migrate all VMs
on it to an alternate datastore.

Find datacenters
Find datastore that matches names
Migrate VMs from source to destination datastore
Alert if target datastore is not available on the cluster
"""


import argparse
import py_vmware.vmware_lib as vmware_lib
import sys

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

    parser.add_argument('-d', '--datastore_source',
                        required=True,
                        action='store',
                        help='source datastore title')

    parser.add_argument('-z', '--datastore_destination',
                        required=True,
                        action='store',
                        help='destination datastore title')

    parser.add_argument('-m', '--mount',
                        action='store_true',
                        help='Whether to mount the volume')

    parser.add_argument('--unmount',
                        action='store_true',
                        help='Whether to unmount the volume')

    args = parser.parse_args()
    return args

def main():
    """Migrate VMs to target datastore"""
    args = get_args()

    si = vmware_lib.connect(
        args.host, args.user, args.password, args.port, args.insecure)
    content = si.RetrieveContent()

    source_datastore = vmware_lib.get_obj(
        content, [vmware_lib.vim.Datastore], args.datastore_source)
    destination_datastore = vmware_lib.get_obj(
        content, [vmware_lib.vim.Datastore], args.datastore_destination)
    if source_datastore and destination_datastore:
        print 'Found {} and {}. Checking for VMs.'.format(
            args.datastore_source, args.datastore_destination)
        if source_datastore.vm:
            print 'Found {} VMs on {}. Starting migration to {}.'.format(
                len(source_datastore.vm), args.datastore_source, args.datastore_destination)
            for vm in source_datastore.vm:
                if destination_datastore in vm.summary.runtime.host.parent.datastore:
                    vmware_lib.migrate_vm_datastore(vm, destination_datastore)
                else:
                    print 'Destination datastore {} is not available in the {} cluster.'.format(args.datastore_destination, vm.summary.runtime.host.parent.name)
                    sys.exit(1)
                    break
            print 'Successfully migrated all VMs'
        else:
            print 'There are no VMs to migrate on {}.'.format(args.datastore_source)
    else:
        if not source_datastore:
            print 'Cannot locate datastore {}'.format(args.datastore_source)
            sys.exit(1)
        if not destination_datastore:
            print 'Cannot locate datastore {}'.format(args.datastore_destination)
            sys.exit(1)

if __name__ == "__main__":
    main()
