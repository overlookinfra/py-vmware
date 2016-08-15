#!/usr/bin/env python

from pyVmomi import vim
from pyVim.connect import SmartConnect, Disconnect
import vmutils
import atexit
import argparse
import getpass
import ssl
import sys


def str2bool(v):
    return str(v.lower()) in ("yes", "true", "t", "1")

def get_args():
    """ Get arguments from CLI """
    parser = argparse.ArgumentParser(
        description='Arguments for talking to vCenter')
    parser.register('type', 'bool', str2bool)

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

    parser.add_argument('-e', '--esxi_host', action='store', help='host to migrate VMs from')
    parser.add_argument('-v', '--vm', action='store', help='name of vm to migrate')
    parser.add_argument('-c', '--cluster', action='store', help='Target cluster')
    parser.add_argument('--skip', action='store', help='vm to skip')

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
            print task.info.error.msg
            task_done = True
            sys.exit(1)

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

def migrate_vm(content, virtual_machine, rebalance):
    """
    Migrate a virtual machine to the least used host
    """
    target = find_target_host(virtual_machine, content, rebalance)
    if target:
        vm, target, current_host_name, target_host_name = target
        if target_host_name == current_host_name:
            return "{} is already located on the optimal host.".format(vm.name)
        else:
            print "Migrating {} from {} to {}".format(
                vm.name, current_host_name, target_host_name)
            move_vm(vm, target)
            return True
    else:
        return "vm not found"

def move_vm(vm, host):
    """
    Move vm to specified host
    """
    relospec = vim.vm.RelocateSpec()
    relospec.host = host
    task = vm.Relocate(spec=relospec)
    wait_for_task(task)

def find_target_host(vm, content, rebalance, cpu_limit=75, memory_limit=80):
    """
    Find a host to migrate to

    Ensure the host matches the CPU model. At present it is exact.
    Return the host with the least amount of CPU used.
    Ensure host is in the green state with no errors reported.
    Ensure host is not in maintenance mode
    """
    try:
        if isinstance(vm, str):
            vmsource = get_obj(content, [vim.VirtualMachine], vm)
        else:
            vmsource = vm
        current_host = vmsource.summary.runtime.host
        model = current_host.hardware.cpuPkg[0].description
        cluster = current_host.parent
        hosts = cluster.host
        if not rebalance:
            hosts.remove(current_host)
        target_hosts = []
        for host in hosts:
            if not host.runtime.inMaintenanceMode:
                if host.overallStatus == 'green':
                    if host.hardware.cpuPkg[0].description == model:
                        cpu = host.summary.quickStats.overallCpuUsage
                        memory = host.summary.quickStats.overallMemoryUsage
                        memory_size = host.summary.hardware.memorySize / 1024 / 1024
                        cpu_size = host.summary.hardware.cpuMhz * host.summary.hardware.numCpuCores
                        memory_capacity = int(float(memory) / memory_size * 100)
                        cpu_capacity = int(cpu / cpu_size * 100)
                        if not memory_capacity > memory_limit:
                            if not cpu_capacity > cpu_limit:
                                target_hosts.append([int(cpu + memory), host])
        target_host = sorted(target_hosts)[0][1]
        return vmsource, target_host, current_host.name, target_host.name
    except:
        return False

def maintenance_mode(host, state):
    """
    Enter a host into maintenance mode
    """
    if state:
        if not host.runtime.inMaintenanceMode:
            print 'Placing {} into maintenance mode'.format(host.name)
            wait_for_task(host.EnterMaintenanceMode(0))
        else:
            print '{} is already in maintenance mode'.format(host.name)
    elif state == False:
        if host.runtime.inMaintenanceMode:
            print 'Exiting maintenance mode'
            wait_for_task(host.ExitMaintenanceMode(0))
        else:
            print '{} is not in maintenance mode'.format(host.name)

def reconnect_host(host, user, pwd):
    """
    Reconnect a ESXi host to vcenter
    """
    if host.summary.runtime.connectionState == 'connected':
        print '{} is already connected'.format(host.name)
    elif host.summary.runtime.connectionState == 'disconnected':
        print 'Reconnecting {}'.format(host.name)
        connectspec = vim.host.ConnectSpec()
        connectspec.userName, connectspec.password = user, pwd
        wait_for_task(host.Reconnect(connectspec))

def connect(host, user, pwd, port, insecure):
    if insecure:
        context = ssl.SSLContext(ssl.PROTOCOL_TLSv1)
        context.verify_mode = ssl.CERT_NONE
        si = SmartConnect(
                host=host, user=user, pwd=pwd, port=port, sslContext=context)
    else:
        si = SmartConnect(host=host, user=user, pwd=pwd, port=port)
    # disconnect this thing
    atexit.register(Disconnect, si)
    return si

def sort_vms(vms, cpu_weight=50, memory_weight=50):
    """
    Sort vms in order of most used to least
    """
    sorted_vms, just_vms = [], []
    for vm in vms:
        cpu = vm.summary.quickStats.overallCpuUsage * (cpu_weight / 100.)
        memory = vm.summary.quickStats.guestMemoryUsage * (memory_weight / 100.)
        sorted_vms.append([cpu + memory, vm])
    sorted_vms = sorted(sorted_vms, reverse=True)
    for vm in sorted_vms:
        just_vms.append(vm[1])
    return just_vms

def migrate_host_vms(content, host, skip, rebalance):
    """
    Migrate vms of the provided host

    Skip vms provided in the skip parameter
    """
    if len(host.vm) > 0:
        migrate_count = 0
        vms = sort_vms(host.vm)
        for vm in vms:
            if skip:
                if not vm.name in skip:
                    migrate = migrate_vm(content, vm, rebalance)
                    if isinstance(migrate, str):
                        print ' '.join([migrate, 'Skipping remaining VMs.'])
                        break
                    else:
                        migrate_count = migrate_count + 1
            else:
                migrate = migrate_vm(content, vm, rebalance)
                if isinstance(migrate, str):
                    print ' '.join([migrate, 'Skipping remaining VMs.'])
                    break
                else:
                    migrate_count = migrate_count + 1
        if migrate_count > 1:
            print 'Successfully migrated {} vms from {}'.format(migrate_count, host.name)
    else:
        print 'No vms found on {}'.format(host.name)


def main():
    """
    Let this thing fly
    """
    args = get_args()

    # connect this thing
    si = connect(args.host, args.user, args.password, args.port, args.insecure)
    content = si.RetrieveContent()

    if args.vm:
        result = migrate_vm(content, args.vm, rebalance=False)
        return result

    if args.esxi_host:
        host = get_obj(content, [vim.HostSystem], args.esxi_host)
        if host:
            if args.migrate_vms:
                migrate_host_vms(content, host, args.skip, args.rebalance)

            if args.maintenance_mode or args.maintenance_mode == False:
                maintenance_mode(host, args.maintenance_mode)
            if args.reboot:
                print 'Rebooting {}'.format(host.name)
                wait_for_task(host.Reboot(force=False))
            if args.reconnect:
                reconnect_host(host, args.host_user, args.host_password)
        else:
            print 'Cannot find host {}'.format(args.esxi_host)
            sys.exit(1)

# start this thing
if __name__ == "__main__":
    main()
