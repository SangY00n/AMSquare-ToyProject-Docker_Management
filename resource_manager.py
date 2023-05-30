import os
from pynvml import *
from collections import defaultdict, OrderedDict
from typing import Optional, Tuple

def shell_run(command: str) -> str:
    output = os.popen(command).read()
    return output

def find_docker_container_from_pid(pid:str)->Optional[Tuple[str, str]]:
    cpid = pid
    depth=0
    while depth<10:
        # print(cpid)
        ppid = shell_run(f"ps -o ppid= -p {cpid}").replace(' ', '').replace('\n', '')
        # print(ppid)
        pname = shell_run(f"ps -o comm= -p {ppid}").replace(' ', '').replace('\n', '')
        # print(pname)
        if pname == "containerd-shim":
            break
        else:
            cpid = ppid
        depth+=1
    
    if depth == 10:
        return None, None
    
    # print(shell_run(f"docker ps -q | xargs docker inspect --format '{{{{.State.Pid}}}}, {{{{.Name}}}}, {{{{.Id}}}}' | grep {cpid}"))
    try:
        _, container_name, container_id = shell_run(f"docker ps -q | xargs docker inspect --format '{{{{.State.Pid}}}}, {{{{.Name}}}}, {{{{.Id}}}}' | grep {cpid}").replace(' ','').split(',')
    except:
        return None, None

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
    runningContainerOnGPU = defaultdict(lambda:defaultdict(list)) # 이중 dict 사용하기 위해서 lambda 함수 사용
    
    runningComputeProcessList = getRunningComputeProcessesOnGPU() # (사용중인 GPU 번호, pid, GPU 메모리 사용량(in bytes)) 들의 list
    # Example for debug
    runningComputeProcessList = [{"gpuNum": 0, "pid": "31663", "usedGpuMemory": "10000"}, {"gpuNum": 1, "pid": "31663", "usedGpuMemory": "10000"}, {"gpuNum": 2, "pid": "31736", "usedGpuMemory": "10000"}, {"gpuNum": 2, "pid": "31736", "usedGpuMemory": "10000"}, {"gpuNum": 3, "pid": "31736", "usedGpuMemory": "10000"}]
    
    for p in runningComputeProcessList:
        print(p)
        container_name, container_id = find_docker_container_from_pid(p["pid"])
        if container_name is None or container_id is None:
            continue
        if (container_name, container_id) not in runningContainerOnGPU:
            runningContainerOnGPU[(container_name, container_id)][p["gpuNum"]]=[p] # 새롭게 추가
        else:
            if p["gpuNum"] in runningContainerOnGPU[(container_name, container_id)]:
                runningContainerOnGPU[(container_name, container_id)][p["gpuNum"]].append(p)
            else:
                runningContainerOnGPU[(container_name, container_id)][p["gpuNum"]]=[p]
        
    
    for c, gpuNums in runningContainerOnGPU.items():
        print(f"-Container: {c}")
        for g, procList in gpuNums.items():
            print(f"\tㄴGPU: GPU{g}")
            for proc in procList:
                print(f"\t\tㄴProcessID: {proc['pid']}, MemoryUsage: {proc['usedGpuMemory']}")


def main():
    check_container_occupying_GPU()

if __name__ == "__main__":
    main()