#!/usr/bin/env python

from pyVmomi import vim
from pyVim.connect import SmartConnect, Disconnect
import getpass
import atexit
import vmutils
import ssl
import sys

def str2bool(v):
    return str(v.lower()) in ("yes", "true", "t", "1")

def wait_for_task(task):
    """ wait for a vCenter task to finish """
    task_done = False
    while not task_done:
        if task.info.state == 'success':
            return task.info.result

        if task.info.state == 'error':
            print "there was an error - {}".format(task.info.error.msg)
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

def migrate_vm(vm_object, host):
    """
    Migrate a virtual machine to the least used host
    """
    current_host_name = vm_object.summary.runtime.host.name
    target_host_name = host.name
    if host.name == current_host_name:
        return "{} is already located on the optimal host.".format(vm_object.name)
    print "Migrating {} from {} to {}".format(vm_object.name, current_host_name, target_host_name)
    move_vm(vm_object, host)

def move_vm(vm_object, host):
    """
    Move vm to specified host
    """
    relospec = vim.vm.RelocateSpec()
    relospec.host = host
    task = vm_object.Relocate(spec=relospec)
    wait_for_task(task)

def find_target_hosts(host, rebalance, cpu_limit=75, memory_limit=80, limit=True):
    """
    Find a host to migrate to

    Ensure the host matches the CPU model. At present it is exact.
    Return the host with the least amount of CPU used.
    Ensure host is in the green state with no errors reported.
    Ensure host is not in maintenance mode
    """
    model = get_host_model(host)
    hosts = host.parent.host
    if not rebalance:
        hosts.remove(host)
    target_hosts = []
    for host in hosts:
        if host_is_available(host, model):
            combined_usage, utilization = get_host_utilization(host)
            target_hosts.append([combined_usage, utilization, host])
    if limit:
        for host in target_hosts:
            if host_exceeded_utilization_limit(host[1], memory_limit, cpu_limit):
                target_hosts.remove(host)
#                    target_hosts.append([combined_usage, host])
#            else:
    #return vmsource, target_host, current_host.name, target_host.name
    return target_hosts

def average_utilization(hosts_list):
    """Return average host utilization based on a input range"""
    utilization = []
    for host in hosts_list:
        utilization.append(host[0])
    avg_utilization = sum(utilization) / len(hosts_list)
    return avg_utilization

def ensure_vm_object(vm, content):
    """Verify input is a VM object. If it is not, attempt to locate the object by name"""
    if isinstance(vm, str):
        vm_object = get_obj(content, [vim.VirtualMachine], vm)
    else:
        vm_object = vm
    return vm_object

def get_vm_parents(vm_object):
    """Return a host and cluster for a VM"""
    current_host = vm_object.summary.runtime.host
    model = get_host_model(current_host)
    cluster = current_host.parent
    return [current_host, model, cluster]

def host_exceeded_utilization_limit(utilization, memory_limit, cpu_limit):
    """Check if host has reached a defined utilization limit"""
    if utilization['memory'] > memory_limit:
        return True
    if utilization['cpu'] > cpu_limit:
        return True
    return False

def get_host_utilization(host):
    """Return host utilization"""
    cpu = host.summary.quickStats.overallCpuUsage
    memory = host.summary.quickStats.overallMemoryUsage
    memory_size = host.summary.hardware.memorySize / 1024 / 1024
    cpu_size = host.summary.hardware.cpuMhz * host.summary.hardware.numCpuCores
    memory_utilization = (float(memory) / memory_size) * 100
    cpu_utilization = (float(cpu) / cpu_size) * 100
    combined_usage = int(cpu + (memory / 2))
    return (
        combined_usage,
        {'memory': memory_utilization, 'cpu': cpu_utilization}
    )

def get_host_model(host):
    """Crudely return CPU model by version number"""
    model = host.hardware.cpuPkg[0].description
    return model

def host_is_available(host, model):
    """Check to see if a host meets criteria to be available for placement"""
    if host.runtime.inMaintenanceMode:
        return False
    if not host.overallStatus == 'green':
        return False
    if not get_host_model(host) == model:
        return False
    return True

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

def build_vm_list(host, skip_vm):
    """Build list of host VMs, skipping any identified in skip_vm"""
    vm_list = sort_vms(host.vm)
    if skip_vm:
        for vm in vm_list:
            if vm.name in skip_vm:
                vm_list.remove(vm)
    return vm_list

def migrate_host_vms(content, host, skip_vm, rebalance, limit):
    """
    Migrate vms of the provided host

    Skip vms provided in the skip parameter
    """
    migrate_count = 0
    vm_list = build_vm_list(host, skip_vm)
    for vm in vm_list:
        migrate = migrate_vm(content, vm, rebalance, limit)
        if isinstance(migrate, str):
            print ' '.join([migrate, 'Skipping remaining VMs.'])
            break
        else:
            migrate_count = migrate_count + 1
    if migrate_count > 1:
        print 'Successfully migrated {} vms from {}'.format(migrate_count, host.name)
    else:
        print 'No vms found on {}'.format(host.name)

def mount_datastore(specification, host):
    try:
        host.configManager.datastoreSystem.CreateNasDatastore(specification)
        return True
    except (vim.fault.DuplicateName, vim.fault.AlreadyExists) as e:
        return '{} is already mounted on {}'.format(specification.localPath, host.name)
    except:
        raise
        return 'Cannot mount {} on {}'.format(specification.localPath, host.name)

def unmount_datastore(datastore, host):
    """Unmount a datastore"""
    try:
        for d in host.datastore:
            if d.name == datastore:
                host.configManager.datastoreSystem.RemoveDatastore(d)
                return True
        return False
    except:
        return False

def datastore_spec(target, name=None):
    """Build a datastore spec for mounting the datastore"""
    dsspec = vim.host.NasVolume.Specification()
    target_parts = target.split(':')
    dsspec.remoteHost, dsspec.remotePath = target_parts
    dsspec.localPath = dsspec.remotePath.split('/')[-1]
    dsspec.accessMode = 'readWrite'
    if name:
        dsspec.localPath = name
    return dsspec

def migrate_vm_datastore(vm, datastore):
    """
    Migrate a VM to a alternate datastore
    """
    # set relospec
    relospec = vim.vm.RelocateSpec()
    relospec.datastore = datastore
    print "Migrating {} to {}...".format(vm.name, datastore.name)
    task = vm.Relocate(spec=relospec)
    wait_for_task(task)
