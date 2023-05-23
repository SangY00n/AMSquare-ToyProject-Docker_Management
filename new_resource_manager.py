import os
from pynvml import *
from collections import defaultdict, OrderedDict

def shell_run(command: str) -> str:
    output = os.popen(command).read()
    return output

def find_docker_container_from_pid(pid:str)->str:
    cpid = pid
    depth=0
    while depth<10:
        depth+=1
        print(cpid)
        ppid = shell_run(f"ps -o ppid= -p {cpid}").replace(' ', '').replace('\n', '')
        print(ppid)
        pname = shell_run(f"ps -o comm= -p {ppid}").replace(' ', '').replace('\n', '')
        print(pname)
        if pname == "containerd-shim":
            break
        else:
            cpid = ppid
        
    # print(shell_run(f"docker ps -q | xargs docker inspect --format '{{{{.State.Pid}}}}, {{{{.Name}}}}, {{{{.Id}}}}' | grep {cpid}"))
    _, container_name, container_id = shell_run(f"docker ps -q | xargs docker inspect --format '{{{{.State.Pid}}}}, {{{{.Name}}}}, {{{{.Id}}}}' | grep {cpid}")
    
    return (container_name, container_id)


def getRunningComputeProcessesOnGPU()->list:
    resultList = []
    
    nvmlInit()
    deviceCount = nvmlDeviceGetCount()
    for i in range(deviceCount):
        handle = nvmlDeviceGetHandleByIndex(i)
        listofprocs = nvmlDeviceGetComputeRunningProcesses(handle)
        for p in listofprocs:
            print(i, p.pid, p.usedGpuMemory) # GPU 번호, pid, GPU 메모리 사용량(in bytes)
            resultList.append({"gpuNum": i, "pid": p.pid, "usedGpuMemory":p.usedGpuMemory})
    nvmlShutdown()

    return resultList


def check_container_occupying_GPU():
    runningContainerOnGPU = dict(dict(list)) ## 이거 안된다 어케 하지
    
    
    runningComputeProcessList = getRunningComputeProcessesOnGPU() # (사용중인 GPU 번호, pid, GPU 메모리 사용량(in bytes)) 들의 list
    for p in runningComputeProcessList:
        container_name, container_id = find_docker_container_from_pid(p.pid)
        if (container_name, container_id) in runningContainerOnGPU:
            if p.gpuNum in runningContainerOnGPU[(container_name, container_id)]:
                runningContainerOnGPU[(container_name, container_id)][p.gpuNum].append(p)
            else:
                runningContainerOnGPU[(container_name, container_id)][p.gpuNum]=[p]
        else:
            runningContainerOnGPU[(container_name, container_id)][p.gpuNum]=[p]
        
    
    for c, gpuNums in runningContainerOnGPU.items():
        print(f"-Container: {c}")
        for g, procList in gpuNums.items():
            print(f"\tㄴGPU: GPU{g}")
            for proc in procList:
                print(f"\t\tㄴProcessID: {proc.pid}, {proc.usedGpuMemory}")
                

check_container_occupying_GPU()