#!/usr/bin/env python
"""
Snapshot time
"""
from pyVmomi import vim
from pyVim.connect import SmartConnect, Disconnect
import atexit
import argparse
import getpass
import ssl
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

    args = parser.parse_args()

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


def get_obj(content, vimtype, name):
    """
    Return an object by name, if name is None the
    first found object is returned
    """
    obj = None
    container = content.viewManager.CreateContainerView(
        content.rootFolder, vimtype, True)
    for c in container.view:
        if name:
            if c.name == name:
                obj = c
                break
        else:
            obj = c
            break

    return obj


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

    if args.insecure:
        context = ssl.SSLContext(ssl.PROTOCOL_TLSv1)
        context.verify_mode = ssl.CERT_NONE
        si = SmartConnect(
            host=args.host,
            user=args.user,
            pwd=args.password,
            port=args.port,
            sslContext=context)
    else:
        si = SmartConnect(
            host=args.host,
            user=args.user,
            pwd=args.password,
            port=args.port)
    # disconnect this thing
    atexit.register(Disconnect, si)

    content = si.RetrieveContent()

    vm = get_obj(content, [vim.VirtualMachine], args.vm_name)

    if vm:
        if args.snapshot_name:
            print "Creating snapshot {} for {}".format(args.snapshot_name, vm.name)
            take_vm_snapshot(si, vm, args.snapshot_name)
        elif args.revert:
            print "Reverting to latest snapshot for {}".format(vm.name)
            revert_to_latest_snapshot(si, vm)
            tasks.wait_for_tasks(si, [vm.PowerOn()])
        else:
            print "No actions requested. Doing nothing"
    else:
        print "{} not found".format(args.vm_name)

if __name__ == "__main__":
    main()
