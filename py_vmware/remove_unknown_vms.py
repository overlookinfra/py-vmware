#!/usr/bin/env python

"""
Identify unknown VMs and remove them
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

    parser.add_argument('-d', '--destroy',
                        action='store_true',
                        help='Destroy unknown VMs')

    args = parser.parse_args()
    return args

def GetAllVms(vm, target, depth=1):
    """Traverse a tree and find VMs returning them to the target list"""
    maxdepth = 10
    if hasattr(vm, 'childEntity'):
        if depth > maxdepth:
            return
        vmList = vm.childEntity
        for c in vmList:
            GetAllVms(c, target, depth+1)
        return
    target.append(vm)

def GetAllVmsRoot(content):
    """Find all VMs starting from root"""
    vms = []
    for child in content:
        if hasattr(child, 'vmFolder'):
            datacenter = child
            vmFolder = datacenter.vmFolder
            vmList = vmFolder.childEntity
            for vm in vmList:
                GetAllVms(vm, vms)
    if vms:
        return vms
    else:
        return False

def FindUnknownVms(vms):
    """Given a source list find VMs titled 'Unknown'"""
    unknown_vms = []
    for vm in vms:
        try:
            if 'Unknown' in vm.name:
                unknown_vms.append(vm)
        except:
            pass
    if len(unknown_vms):
        return unknown_vms
    else:
        return False

def main():
    """Kill the unknown VMs"""
    args = get_args()

    si = vmware_lib.connect(
        args.host, args.user, args.password, args.port, args.insecure)
    content = si.RetrieveContent()

    print 'Looking for vms'
    vms = GetAllVmsRoot(content.rootFolder.childEntity)
    print 'Checking vm count - is {}'.format(len(vms))
    if vms:
        unknown_vms = FindUnknownVms(vms)
    if unknown_vms:
        print 'Found {} unknown VMs'.format(len(unknown_vms))
        if args.destroy:
            print 'Destroy for unknown VMs requested'
            for vm in unknown_vms:
                try:
                    if format(vm.runtime.powerState) == 'poweredOn':
                        power_off_vm = vm.PowerOffVM_Task()
                        vmware_lib.wait_for_task(power_off_vm)
                    destroy_vm = vm.Destroy_Task()
                    name = vm.name
                    vmware_lib.wait_for_task(destroy_vm)
                    print 'Successfully destroyed {}'.format(name)
                except:
                    print 'Failed to destroy {}'.format(vm.name)
                    pass
    else:
        print 'No unknown VMs found'

if __name__ == "__main__":
    main()
