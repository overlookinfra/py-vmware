from setuptools import setup, find_packages


setup(
    name='py_vmware',
    version='0.0.7',
    packages=find_packages(),
    install_requires=['pyvmomi'],
    entry_points={
        'console_scripts': [
            'vmware_clone_vm = py_vmware.clone_vm:main',
            'vmware_check_cluster = py_vmware.cluster_host_health:main',
            'vmware_destroy_vm = py_vmware.destroy_vm:main',
            'vmware_reboot_vm = py_vmware.reboot_vm:main',
            'vmware_getvms = py_vmware.getallvms:main',
            'vmware_host_maintenance = py_vmware.migrate_host_vms:main',
            'vmware_migrate_vm_datastore = py_vmware.migrate_vm_datastore:main',
            'vmware_vm_snapshot = py_vmware.vm_snapshot:main',
            'vmware_mount_datastore = py_vmware.add_cluster_datastore:main',
        ]
    },
    author='Matt Kirby',
    author_email='kirby@puppet.com',
    description='A CLI tool for interacting with vmware vSphere and ESXi',
    license='MIT License',
    url='github.com/mattkirby/py-vmware'
)
