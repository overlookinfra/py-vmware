from setuptools import setup, find_packages


setup(
    name='py-vmware',
    version='0.0.1',
    packages=find_packages(),
    install_requires=['pyvmomi'],
    entry_points={
        'console_scripts': [
            'vmware_clone_vm = py-vmware.clone_vm:main',
            'vmware_check_cluster = py-vmware.cluster_host_health:main',
            'vmware_destroy_vm = py-vmware.destroy_vm:main',
            'vmware_getvms = py-vmware.getallvms:main',
            'vmware_host_maintenance = py-vmware.migrate_host_vms:main',
            'vmware_migrate_vm_datastore = py-vmware.migrate_vm_datastore:main',
            'vmware_vm_snapshot = py-vmware.vm_snapshot:main',
        ]
    },
    author='Matt Kirby',
    author_email='kirby@puppet.com',
    description='A CLI tool for interacting with vmware vSphere and ESXi',
    license='MIT License',
    url='github.com/mattkirby/py-vmware'
)
