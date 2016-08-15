# Python vmware tools
To make interacting with vSphere easier we have some python tools available. They provide the capability to manage VMs and hosts. With VMs you have the capability to create, destroy, migrate and create snapshots. With hosts there are some tools provided to support maintenance operations and batch migration tasks, as well as reallocate resources within a cluster.
## Table of Contents

1. [Installation](#installation)
1. [Capabilities](#capabilities)
  1. [VM Capabilities](#vm_capabilities)
    1. [vmware_clone_vm](#clone_vm)
    1. [vmware_destroy_vm](#destroy_vm)
    1. [vmware_getvms](#getvms)
    1. [vmware_vm_snapshot](#vm_snapshot)
    1. [vmware_migrate_vm_datastore](#migrate_vm_datastore)
    1. [vmware_host_maintenance](#host_maintenance)
  1. [Host capabilities](#host_capabilities)
    1. [vmware_host_maintenance](#host_maintenance_)
    1. [vmware_check_cluster](#check_cluster)

## Installation
Our python vmware tools are available in py-vmware and published to our internal pypi repository. You can either clone the repository, or install the pip package.

Capabilities
When installed via pip a number of entry points are provided to assist with easily leveraging the included functionality. Each entry point provides a help menu which can be viewed by typing the command + `-h`
   pip install py_vmware -i https://pypi.ops.puppetlabs.net/simple
VM Capabilities vmware_clone_vm
Provides the capability to clone VMs.
usage: vmware_clone_vm [-h] -s HOST [-o PORT] -u USER [-p PASSWORD] -v VM_NAME --template TEMPLATE [--datacenter-name DATACENTER_NAME]
[--vm-folder VM_FOLDER]
[--datastore-name DATASTORE_NAME]
[--cluster-name CLUSTER_NAME]
[--resource-pool RESOURCE_POOL] [--power-on] [--no-power-on] [--cpus CPUS] [--memory MEMORY] [-i] [-l]
 
Example usage
vmware_clone_vm --host $vmware_server --user $user@puppet.com --password
$puppet_pass \
--template 'centos-7-x86_64' --cluster-name 'operations1' --vm_name
'my_new_vm' \
--datastore_name 'general0' --vm-folder 'my_folder' --cpus 2 --memory 2048
--linked_clone
      vmware_destroy_vm
Provides the capability to destroy a VM. You must provide the UUID, DNS name, or IP address.
    usage: vmware_destroy_vm [-h] -s HOST [-o PORT] -u USER [-p PASSWORD] [-j UUID] [-n NAME] [-i IP]
    Example usage
vmware_destroy_vm --host $vmware_server --user $user@puppet.com --password
$puppet_pass --name $my_vm
  vmware_getvms
List all VMs known to a vSphere instance. Returns UUID, IP address (if it has one), power state and other metadata.
Example usage
     vmware_getvms --host $vmware_server --user $user@puppet.com --password
     $puppet_pass
vmware_vm_snapshot
Manage virtual machine snapshots. Supports creating snapshots, and reverting to the latest snapshot.
Example usage
     vmware_vm_snapshot --host $vmware_server --user $user@puppet.com --password
     $puppet_pass \
     --vm_name $my_vm --snapshot_name $snapshot_name
vmware_migrate_vm_datastore
Migrate a virtual machine to a new datastore.
    usage: vmware_getvms [-h] -s HOST [-o PORT] -u USER [-p PASSWORD]
        usage: vmware_vm_snapshot [-h] -s HOST [-o PORT] -u USER [-p PASSWORD] -v VM_NAME [-sn SNAPSHOT_NAME] [-i] [-r]
          usage: vmware_migrate_vm_datastore [-h] -s HOST [-o PORT] -u USER [-p PASSWORD] [-v VM_NAME]
[--datastore-name DATASTORE_NAME] [-i]
 
            Example usage - migrating a VM to a new datastore
 vmware_migrate_vm_datastore --host $vmware_server --user $user@puppet.com
--password $puppet_pass \
--vm_name $my_vm --datastore_name $new_datastore
vmware_host_maintenance
Migrate a virtual machine to a new host. The new host is selected automatically based on cluster resource utilization. If the option "–rebalance" is provided then the VM will only be migrated if there is a lesser utilized host in the cluster. Most capabilities under this function are host centric, but this does provide the capability to migrate specific virtual machines.
    usage: vmware_host_maintenance [-h] -s HOST [-o PORT] -u USER [--host_user HOST_USER] [-p PASSWORD]
[--host_password HOST_PASSWORD]
[--datacenter-name DATACENTER_NAME] [-i] [--maintenance_mode MAINTENANCE_MODE]
[--reboot] [--reconnect] [--migrate_vms] [--rebalance] [-e ESXI_HOST] [-v VM] [-c CLUSTER] [--skip SKIP]
   Example usage - migrating a VM
     vmware_host_maintenance --host $vmware_server --user $user@puppet.com
     --password $puppet_pass \
     --vm_name $my_vm
Host capabilities vmware_host_maintenance
Provides a set of capabilities to assist in performing routine maintenance. Will migrate all VMs from a host, then place the host into maintenance mode, selecting the least used hosts in the same cluster that support running the VMs as the target, re-evaluating at each migration. This also provides the capability to rebalance cluster resources by migrating VMs from more used hosts to lesser used hosts.
     usage: vmware_host_maintenance [-h] -s HOST [-o PORT] -u USER [--host_user HOST_USER] [-p PASSWORD]
[--host_password HOST_PASSWORD]
[--datacenter-name DATACENTER_NAME] [-i] [--maintenance_mode MAINTENANCE_MODE]
[--reboot] [--reconnect] [--migrate_vms] [--rebalance] [-e ESXI_HOST] [-v VM] [-c CLUSTER] [--skip SKIP]
   Example usage - empty host and place in maintenance mode
vmware_host_maintenance --host $vmware_server --user $user@puppet.com
--password $puppet_pass \
--esxi_host $target_host --migrate_vms --maintenance_mode true


Example usage - rebalance host resources
vmware_host_maintenance --host $vmware_server --user $user@puppet.com
--password $puppet_pass \
--esxi_host $target_host --migrate_vms --rebalance
vmware_check_cluster
Check the specific cluster for hosts with configuration issues and alarms. Configuration issues will be printed, while alarms will cause a host to be reported as having an issue. This does not currently print alarms. A configuration issue arises when a SD card is no longer available, for example.
Example usage - check cluster health
     vmware_check_cluster --host $vmware_server --user $user@puppet.com
     --password $puppet_pass \
     --cluster acceptance1
usage: vmware_check_cluster [-h] -s HOST [-o PORT] -u USER [-p PASSWORD] [--datacenter-name DATACENTER_NAME] [-i]
[-c CLUSTER]

