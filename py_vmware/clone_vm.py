#!/usr/bin/env python
"""
Written by Dann Bohn
Github: https://github.com/whereismyjetpack
Email: dannbohn@gmail.com
Clone a VM from template example
"""
import argparse
import py_vmware.vmware_lib as vmware_lib
import sys
import getpass
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

    parser.add_argument('--template',
                        required=True,
                        action='store',
                        help='Name of the template/VM \
                            you are cloning from')

    parser.add_argument('--datacenter-name',
                        required=False,
                        action='store',
                        default=None,
                        help='Name of the Datacenter you\
                            wish to use. If omitted, the first\
                            datacenter will be used.')

    parser.add_argument('--vm-folder',
                        required=False,
                        action='store',
                        default=None,
                        help='Name of the VMFolder you wish\
                            the VM to be dumped in. If left blank\
                            The datacenter VM folder will be used')

    parser.add_argument('--datastore-name',
                        required=False,
                        action='store',
                        default=None,
                        help='Datastore you wish the VM to end up on\
                            If left blank, VM will be put on the same \
                            datastore as the template')

    parser.add_argument('--cluster-name',
                        required=False,
                        action='store',
                        default=None,
                        help='Name of the cluster you wish the VM to\
                            end up on. If left blank the first cluster found\
                            will be used')

    parser.add_argument('--resource-pool',
                        required=False,
                        action='store',
                        default=None,
                        help='Resource Pool to use. If left blank the first\
                            resource pool found will be used')

    parser.add_argument('--power-on',
                        dest='power_on',
                        required=False,
                        action='store_true',
                        help='power on the VM after creation')

    parser.add_argument('--no-power-on',
                        dest='power_on',
                        required=False,
                        action='store_false',
                        help='do not power on the VM after creation')

    parser.add_argument('--cpus',
                        required=False,
                        type=int,
                        help='number of CPUs')

    parser.add_argument('--memory',
                        required=False,
                        type=int,
                        help='amount of memory for vm in MB')

    parser.add_argument('-i', '--insecure',
                        required=False,
                        action='store_true',
                        help='disable ssl validation')

    parser.add_argument('-l', '--linked-clone',
                        required=False,
                        action='store_true',
                        help='create linked clone')

    parser.add_argument('-tf', '--template-folder',
                        required=False,
                        action='store',
                        help='parent folder of template')

    parser.set_defaults(power_on=True)

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

def take_template_snapshot(si, vm):
    if len(vm.rootSnapshot) < 1:
        task = vm.CreateSnapshot_Task(name='auto_snapshot_for_linked_clone',
                                      memory=False,
                                      quiesce=False)
        tasks.wait_for_tasks(si, [task])
        print "Successfully taken snapshot of '{}'".format(vm.name)

def clone_vm(
        content, template, vm_name, si,
        datacenter_name, vm_folder, datastore_name,
        cluster_name, resource_pool, power_on, cpus,
        memory, linked_clone, enablehotswap=False):
    """
    Clone a VM from a template/VM, datacenter_name, vm_folder, datastore_name
    cluster_name, resource_pool, and power_on are all optional.
    """

    # if none git the first one
    datacenter = get_obj(content, [vmware_lib.vim.Datacenter], datacenter_name)

    if vm_folder:
        destfolder = get_obj(content, [vmware_lib.vim.Folder], vm_folder)
    else:
        destfolder = datacenter.vmFolder

    if datastore_name:
        datastore = get_obj(content, [vmware_lib.vim.Datastore], datastore_name)
    else:
        datastore = get_obj(
            content, [vmware_lib.vim.Datastore], template.datastore[0].info.name)

    # if None, get the first one
    cluster = get_obj(content, [vmware_lib.vim.ClusterComputeResource], cluster_name)

    if resource_pool:
        resource_pool = get_obj(content, [vmware_lib.vim.ResourcePool], resource_pool)
    else:
        resource_pool = cluster.resourcePool

    # set relospec
    relospec = vmware_lib.vim.vm.RelocateSpec()
    relospec.datastore = datastore
    if linked_clone:
        relospec.diskMoveType = 'moveChildMostDiskBacking'
    #else:
    #    relospec.diskMoveType = 'createNewChildDiskBacking'
    relospec.pool = resource_pool

    vmconf = vmware_lib.vim.vm.ConfigSpec()
    if memory:
        vmconf.memoryMB = memory
    if cpus:
        vmconf.numCPUs = cpus
    if enablehotswap:
        vmconf.cpuHotAddEnabled = True
        vmconf.memoryHotAddEnabled = True
    vmconf.extraConfig = []
    opt = vmware_lib.vim.option.OptionValue()
    options = {'guestinfo.hostname': vm_name}
    for k, v in options.iteritems():
        opt.key = k
        opt.value = v
        vmconf.extraConfig.append(opt)
        opt = vmware_lib.vim.option.OptionValue()

   #if linked_clone:
   #    clonespec = vim.vm.CloneSpec(snapshot=template.snapshot.rootSnapshotList[0].snapshot)
   #else:
    clonespec = vmware_lib.vim.vm.CloneSpec()
    clonespec.location = relospec
    clonespec.config = vmconf
    if power_on == False:
        clonespec.powerOn = False

    print "cloning VM..."
    task = template.Clone(folder=destfolder, name=vm_name, spec=clonespec)
    wait_for_task(task)

def main():
    """
    Let this thing fly
    """
    args = get_args()

    # connect this thing
    si = vmware_lib.connect(args.host, args.user, args.password, args.port, args.insecure)
    content = si.RetrieveContent()

    vm_object = None

    if args.template_folder:
        folder = vmware_lib.get_obj(content, [vmware_lib.vim.Folder], args.template_folder)
        for vm in folder.childEntity:
            if vm.name == args.template:
                vm_object = vm
    else:
        vm_object = vmware_lib.get_obj(content, [vmware_lib.vim.VirtualMachine], args.template)

    if vm_object:
        clone_vm(
            content, vm_object, args.vm_name, si,
            args.datacenter_name, args.vm_folder,
            args.datastore_name, args.cluster_name,
            args.resource_pool, args.power_on,
            args.cpus, args.memory, args.linked_clone)
    else:
        print "template not found"

# start this thing
if __name__ == "__main__":
    main()
