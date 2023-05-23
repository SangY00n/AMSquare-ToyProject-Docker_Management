from pynvml import *

nvmlInit()
deviceCount = nvmlDeviceGetCount()
for i in range(deviceCount):
    handle = nvmlDeviceGetHandleByIndex(i)
    listofprocs = nvmlDeviceGetComputeRunningProcesses(handle)
    for p in listofprocs:
        print(i, p.pid, p.usedGpuMemory)

nvmlShutdown()
