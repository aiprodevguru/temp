import psutil

def list_vm_processes():
    instances = dict()
    # Iterate over all running processes
    for process in psutil.process_iter(['pid', 'name']):
        try:
            # Fetch process details as dict
            process_info = process.info
            # Extract process name
            process_name = process_info['name']
            # Print the process name
            if process_name in {'VirtualBoxVM', 'vmware-vmx', 'VirtualBoxVM.exe', 'VMware Workstation VMX.exe'}:
                instances[process_name] = 1 if process_name not in instances else instances[process_name] + 1
        except (psutil.NoSuchProcess, psutil.AccessDenied):
            # Process no longer exists or we don't have permission to access it
            continue

    vm_process_nums = 0
    for key in instances:
        if key in {'VirtualBoxVM.exe'}:
            vm_process_nums = vm_process_nums + instances[key] / 3
        else:
            vm_process_nums = vm_process_nums + instances[key]

    return vm_process_nums


if __name__ == "__main__":
    process_nums = list_vm_processes()
    print("number of vm process:", process_nums)
