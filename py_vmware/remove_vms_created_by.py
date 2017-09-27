#!/usr/bin/env python

"""
Identify zombie VMs and remove them
"""

import argparse
import py_vmware.vmware_lib as vmware_lib
import re
import datetime
import pytz
from dateutil import parser
import getpass
import json


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

    parser.add_argument('--createdby',
                        required=True,
                        action='store',
                        default=None,
                        help='Part of the username of the vmpooler stored \
                              in VM Notes "created_by" field')

    parser.add_argument('-i', '--insecure',
                        required=False,
                        action='store_true',
                        help='disable ssl validation')

    parser.add_argument('-d', '--destroy',
                        action='store_true',
                        help='Confirm destroy zombie VMs')

    args = parser.parse_args()
    return args

def GetAllVms(vm, target, depth=1):
    """Traverse a tree and find VMs returning them to the target list"""
    maxdepth = 10
    if len(target) > maxquery:
        return
    if hasattr(vm, 'childEntity'):
        if depth > maxdepth:
            return
        vmList = vm.childEntity
        for c in vmList:
            GetAllVms(c, target, depth+1)
        return
    annotation = vm.summary.config.annotation
    if annotation and is_json(annotation):
        annotation = json.loads(annotation)
        if args.createdby in annotation['created_by']:
            print str(len(target)) + "(Debug-progress) " + vm.name + " " + annotation['creation_timestamp']
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
                if len(vms) > maxquery:
                    print "Hit maxquery set to (" + str(maxquery) + ") will process these now. Please run the command again to do another batch"
                    break
    if vms:
        return vms
    else:
        return False

def FindZombieVms(vms):
    """Given a source list find VMs with note equal to X"""
    zombie_vms = []

    for vm in vms:
        try:
            summary = vm.summary
            annotation = summary.config.annotation

            if annotation:
                annotation = json.loads(annotation)
            # created by vmpooler
            if args.createdby in annotation['created_by']:
                # with the random name 15 chars of a-z and 0-9 like rbmj4bvo30v4efg
                if re.match("[a-z0-9]{15}", vm.name):
                    # compare times
                    nowdate = datetime.datetime.now()
                    nowdate = nowdate.replace(tzinfo=pytz.UTC)
                    vmdate = parser.parse(annotation['creation_timestamp'])
                    # timestamp is bigger than 24h
                    deltatime = nowdate-datetime.timedelta(seconds=3600*24*7)
                    if vmdate < deltatime:
                        print "double check: " + vm.name + " " + annotation['created_by'] + " " + annotation['creation_timestamp'] + " host:" + summary.runtime.host.name
                        zombie_vms.append(vm)
        except:
            pass
    if len(zombie_vms):
        return zombie_vms
    else:
        return False

def destroy(zombie_vms):
    print 'Reached destroy'
    for vm in zombie_vms:
        try:
            name = vm.name
            if format(vm.runtime.powerState) == 'poweredOn':
                power_off_vm = vm.PowerOffVM_Task()
                vmware_lib.wait_for_task(power_off_vm)
            destroy_vm = vm.Destroy_Task()
            vmware_lib.wait_for_task(destroy_vm)
            print 'Successfully destroyed {}'.format(name)
        except:
            print 'Failed to destroy {}'.format(name)
            pass

def is_json(myjson):
    try:
        json_object = json.loads(myjson)
    except ValueError, e:
        return False
    return True

args = None
maxquery = 2000

def main():
    """Kill the zombie VMs"""

    global args
    args = get_args()

    if args.password:
        password = args.password
    else:
        password = getpass.getpass(prompt='Enter password for host %s and '
                                      'user %s: ' % (args.host, args.user))

    si = vmware_lib.connect(
        args.host, args.user, password, args.port, args.insecure)
    content = si.RetrieveContent()

    print 'Getting full list of vms'
    vms = GetAllVmsRoot(content.rootFolder.childEntity)
    print 'Checking vm count - is {}'.format(len(vms))
    if vms:
        zombie_vms = FindZombieVms(vms)
    if zombie_vms:
        print 'Found {} zombie VMs'.format(len(zombie_vms))
        if args.destroy:
            destroy(zombie_vms)
        else:
            message = "Please confirm destroying the above in 'double check' list (Y/N) "
            confirm = raw_input(message)
            if confirm.lower() == 'y':
                destroy(zombie_vms)
            else:
                print "Nothing deleted"
    else:
        print 'No zombie VMs found'

if __name__ == "__main__":
    main()
