#!/usr/bin/env python
"""
Snapshot time
"""
import argparse
import py_vmware.vmware_lib as vmware_lib
import getpass
from py_vmware.tools import tasks


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
                        help='Name of the VM you wish to make')

    parser.add_argument('-sn', '--snapshot-name',
                        action='store',
                        help='Name of snapshot you wish to make')

    parser.add_argument('-i', '--insecure',
                        required=False,
                        action='store_true',
                        help='disable ssl validation')

    parser.add_argument('-r', '--revert',
                        action='store_true',
                        help='revert to latest snapshot')

    parser.add_argument('-d', '--destroy_all',
                        action='store_true',
                        help='Destroy all VM snapshots')

    parser.add_argument('-w', '--wait_for_task',
                        action='store_true',
                        help='Wait for task to complete before exiting')

    parser.add_argument('-f', '--folder',
                        action='store',
                        help='Parent folder for VM')

    parser.add_argument('-l', '--list_snapshots',
                        action='store_true',
                        help='List VM snapshots, if present')

    args = parser.parse_args()

    if not args.password:
        args.password = getpass.getpass(
            prompt='Enter password')

    return args

def wait_for_task(task):
    """ wait for a vCenter task to finish """
    task_done = False
    while not task_done:
        if task.info.state == 'success':
            return task.info.result

        if task.info.state == 'error':
            print "there was an error"
            task_done = True

def take_vm_snapshot(si, vm, sname):
    #if len(vm.rootSnapshot) < 1:
    task = vm.CreateSnapshot_Task(name=sname,
                                  memory=False,
                                  quiesce=False)
    tasks.wait_for_tasks(si, [task])
    print "Successfully taken snapshot of '{}'".format(vm.name)


def revert_to_latest_snapshot(si, vm):
    task = vm.RevertToCurrentSnapshot()
    tasks.wait_for_tasks(si, [task])

def main():
    """
    Do some stuff
    """
    args = get_args()

    si = vmware_lib.connect(args.host, args.user, args.password, args.port, args.insecure)
    content = si.RetrieveContent()

    if args.folder:
        folder = vmware_lib.get_obj(content, [vmware_lib.vim.Folder], args.folder)
        for vm in folder.childEntity:
            if vm.name == args.vm_name:
                vm_object = vm
    else:
        vm_object = vmware_lib.get_obj(content, [vmware_lib.vim.VirtualMachine], args.vm_name)

    if vm_object == None:
        print 'Cannot find {}'.format(args.vm_name)
        return

    if args.snapshot_name:
        print "Creating snapshot {} for {}".format(args.snapshot_name, args.vm_name)
        take_vm_snapshot(si, vm_object, args.snapshot_name)
    if args.revert:
        print "Reverting to latest snapshot for {}".format(args.vm_name)
        revert_to_latest_snapshot(si, vm_object)
        tasks.wait_for_tasks(si, [vm_object.PowerOn()])
    if args.destroy_all:
        print "Destroying snapshots for {}".format(args.vm_name)
        task = vm_object.RemoveAllSnapshots_Task()
        if args.wait_for_task:
            vmware_lib.wait_for_task(task)
            print 'All snapshots for {} have been destroyed'.format(args.vm_name)
    if args.list_snapshots:
        try:
            snaps = vm_object.snapshot.rootSnapshotList
            for snap in snaps:
                print snap
        except AttributeError:
            print 'No snapshots found for {}'.format(args.vm_name)

if __name__ == "__main__":
    main()
