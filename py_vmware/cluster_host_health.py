#!/usr/bin/env python

from pyVmomi import vim
from pyVim.connect import SmartConnect, Disconnect
import vmutils
import atexit
import argparse
import getpass
import ssl
import sys


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

    parser.add_argument('-c', '--cluster', action='store', help='Target cluster')

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

    cluster = get_obj(content, [vim.ClusterComputeResource], args.cluster)
    if not cluster:
        print 'Cannot find cluster {}'.format(args.cluster)
        sys.exit(1)
    problem_hosts = []
    for host in cluster.host:
        if host.overallStatus == 'yellow':
            if len(host.configIssue) > 0:
                message = '{} - {}'.format(host.name, host.configIssue[0].fullFormattedMessage)
                if host.runtime.inMaintenanceMode:
                    message = '. '.join([message, 'Host is in maintenance mode'])
                problem_hosts.append(message)
            else:
                problem_hosts.append(host.name)

    if problem_hosts:
        print "{} hosts found with issues.\n{}".format(len(problem_hosts), '\n'.join(problem_hosts))
    else:
        print "no hosts with issues found in {} cluster".format(args.cluster)

# start this thing
if __name__ == "__main__":
    main()
