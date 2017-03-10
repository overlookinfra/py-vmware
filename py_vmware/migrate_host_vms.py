#!/usr/bin/env python

import argparse
import py_vmware.vmware_lib as vmware_lib
import sys
from tools import tasks


def get_args():
    """ Get arguments from CLI """
    parser = argparse.ArgumentParser(
        description='Arguments for talking to vCenter')
    parser.register('type', 'bool', vmware_lib.str2bool)

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

    parser.add_argument('--host_user',
                        required=False,
                        action='store',
                        help='ESXi user',
                        default='root')

    parser.add_argument('-p', '--password',
                        required=False,
                        action='store',
                        help='Password to use')

    parser.add_argument('--host_password',
                        action='store',
                        help='ESXi host password')

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

    parser.add_argument('--maintenance_mode',
                        action='store',
                        help='Enter maintenance mode',
                        type='bool')

    parser.add_argument('--reboot',
                        action='store_true',
                        help='Reboot selected host. Requires esxi_host parameter')

    parser.add_argument('--reconnect',
                        action='store_true',
                        help='Reconnect provided host.')

    parser.add_argument('--migrate_vms',
                        action='store_true',
                        help='Whether to migrate host vms')

    parser.add_argument('--rebalance',
                        action='store_true',
                        help='Rebalance the cluster')

    parser.add_argument('--limit',
                        action='store',
                        type='bool',
                        help='Limit host selection on hard resource constraints')

    parser.add_argument('-e', '--esxi_host', action='store', help='host to migrate VMs from')
    parser.add_argument('-v', '--vm', action='store', help='name of vm to migrate')
    parser.add_argument('-c', '--cluster', action='store', help='Target cluster')
    parser.add_argument('--skip', action='store', help='vm to skip')
    parser.add_argument('--cold_migrate', action='store_true', help='Power off VM for migration')

    args = parser.parse_args()
    return args

def main():
    """
    Let this thing fly
    """
    args = get_args()

    # connect this thing
    si = vmware_lib.connect(args.host, args.user, args.password, args.port, args.insecure)
    content = si.RetrieveContent()

    if args.vm:
        if args.cold_migrate:
            vm = vmware_lib.get_obj(content, [vmware_lib.vim.VirtualMachine], args.vm)
            if vm.runtime.powerState == 'poweredOn':
                print 'Powering off {}'.format(args.vm)
                task = vm.PowerOffVM_Task()
                tasks.wait_for_tasks(si, [task])

        print 'Migrating VM'
        result = vmware_lib.migrate_vm(content, args.vm, rebalance=False, limit=90)
        if args.cold_migrate:
            print 'Powering on VM'
            task = vm.PowerOnVM_Task()
            tasks.wait_for_tasks(si, [task])
        return result

    if args.esxi_host:
        host = vmware_lib.get_obj(content, [vmware_lib.vim.HostSystem], args.esxi_host)
        if host:
            if args.migrate_vms:
                vmware_lib.migrate_host_vms(content, host, args.skip, args.rebalance, args.limit)

            if args.maintenance_mode or args.maintenance_mode == False:
                vmware_lib.maintenance_mode(host, args.maintenance_mode)
            if args.reboot:
                print 'Rebooting {}'.format(host.name)
                vmware_lib.wait_for_task(host.Reboot(force=False))
            if args.reconnect:
                vmware_lib.reconnect_host(host, args.host_user, args.host_password)
        else:
            print 'Cannot find host {}'.format(args.esxi_host)
            sys.exit(1)

# start this thing
if __name__ == "__main__":
    main()
