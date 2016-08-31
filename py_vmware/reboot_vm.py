#!/usr/bin/env python

import argparse
import py_vmware.vmware_lib as vmware_lib


def get_args():
    """ Get arguments from CLI """
    parser = argparse.ArgumentParser(description='Arguments for talking to vCenter')

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

    parser.add_argument('-i', '--insecure',
                        required=False,
                        action='store_true',
                        help='disable ssl validation')

    parser.add_argument('-v', '--vm',
                        action='store',
                        help='name of vm to reboot')

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

    vm = vmware_lib.get_obj(content, [vmware_lib.vim.VirtualMachine], args.vm)

# does the actual vm reboot
    try:
        vm.RebootGuest()
    except:
        # forceably shutoff/on
        # need to do if vmware guestadditions isn't running
        vm.ResetVM_Task()

if __name__ == "__main__":
    main()
