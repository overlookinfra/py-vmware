#!/usr/bin/env python
"""
Written by Dann Bohn
Github: https://github.com/whereismyjetpack
Email: dannbohn@gmail.com
Clone a VM from template example
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

    parser.add_argument('-v', '--vm_name',
                        action='store',
                        help='Name of the template/VM you want to migrate')

#   parser.add_argument('--datacenter-name',
#                       required=False,
#                       action='store',
#                       default=None,
#                       help='Name of the Datacenter you\
#                           wish to use. If omitted, the first\
#                           datacenter will be used.')
#
#   parser.add_argument('--vm-folder',
#                       required=False,
#                       action='store',
#                       default=None,
#                       help='Name of the VMFolder you wish\
#                           the VM to be dumped in. If left blank\
#                           The datacenter VM folder will be used')
#
    parser.add_argument('--datastore-name',
                        required=False,
                        action='store',
                        default=None,
                        help='Datastore you wish the VM to end up on\
                            If left blank, VM will be put on the same \
                            datastore as the template')

    parser.add_argument('-i', '--insecure',
                        required=False,
                        action='store_true',
                        help='disable ssl validation')

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

def move_vm(content, template, si, datastore_name, source_title):
    """
    Move a VM to a new datastore
    """
    datastore = get_obj(content, [vim.Datastore], datastore_name)

    # set relospec
    relospec = vim.vm.RelocateSpec()
    relospec.datastore = datastore

    print "moving {} to {}...".format(source_title, datastore_name)
    task = template.Relocate(spec=relospec)
    wait_for_task(task)

def main():
    """
    Let this thing fly
    """
    args = get_args()

    # connect this thing
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
    template = None

    template = get_obj(content, [vim.VirtualMachine], args.vm_name)

    if template:
        move_vm(content, template, si, args.datastore_name, args.vm_name)
    else:
        print "template not found"

# start this thing
if __name__ == "__main__":
    main()
