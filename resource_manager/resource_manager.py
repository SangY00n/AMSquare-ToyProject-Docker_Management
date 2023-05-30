import os
from pynvml import *
from collections import defaultdict, OrderedDict
from typing import Optional, Tuple
import typer

def shell_run(command: str) -> str:
    output = os.popen(command).read()
    return output

def find_docker_container_from_pid(pid:str)->Optional[Tuple[str, str]]:
    cpid = pid
    depth=0
    while depth<10:
        if cpid == '1' or cpid == '0':
            return None, None
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
        _, container_name, container_id = shell_run(f"docker ps -q | xargs docker inspect --format '{{{{.State.Pid}}}}, {{{{.Name}}}}, {{{{.Id}}}}' | grep {cpid}").replace(' ', '').replace('\n', '').split(',')
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
            # print(i, p.pid, p.usedGpuMemory) # GPU 번호, pid, GPU 메모리 사용량(in bytes)
            resultList.append({"gpuNum": i, "pid": p.pid, "usedGpuMemory":p.usedGpuMemory})
    nvmlShutdown()

    return resultList


def check_container_occupying_GPU():
    runningContainerOnGPU = defaultdict(lambda:defaultdict(list)) # 이중 dict 사용하기 위해서 lambda 함수 사용
    
    runningComputeProcessList = getRunningComputeProcessesOnGPU() # (사용중인 GPU 번호, pid, GPU 메모리 사용량(in bytes)) 들의 list
    # Example for debug
    # runningComputeProcessList = [{"gpuNum": 0, "pid": "31663", "usedGpuMemory": "10000"}, {"gpuNum": 1, "pid": "31663", "usedGpuMemory": "10000"}, {"gpuNum": 2, "pid": "31736", "usedGpuMemory": "10000"}, {"gpuNum": 2, "pid": "31736", "usedGpuMemory": "10000"}, {"gpuNum": 3, "pid": "31736", "usedGpuMemory": "10000"}]
    
    for p in runningComputeProcessList:
        # print(p)
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
        
    
    print("[GPU Memory Usage per Container]")
    for c, gpuNums in runningContainerOnGPU.items():
        print(f"-Container: {c}")
        for g, procList in gpuNums.items():
            print(f"\tㄴGPU: GPU{g}")
            for proc in procList:
                print(f"\t\tㄴProcessID: {proc['pid']}, GPUMemoryUsage(bytes): {proc['usedGpuMemory']}")
    print()

def check_container_occupying_memory(top_process_num: int):
    username_pid_pmem_list = shell_run(f"ps aux --sort=-pmem | head -{top_process_num} | awk '{{print $1, $2, $4}}'").split('\n')[1:]
    username_pid_pmem_list = list(
        filter(None, username_pid_pmem_list)
    )  # filtering to remove empty string element
    username_pid_pmem_list: tuple[str, str, str] = [(username_pid_pmem.split()[0], username_pid_pmem.split()[1], username_pid_pmem.split()[2]) for username_pid_pmem in username_pid_pmem_list] # username과 pid와 %mem의 tuple

    container_pmem_dict: defaultdict[(str, str, str), float] = defaultdict(float)
    
    for (username, pid, pmem) in username_pid_pmem_list:
        container_id, container_name = find_docker_container_from_pid(pid)
        if container_id is None or container_name is None:
            continue
        container_pmem_dict[(container_id, container_name)] += float(pmem)
            # print(f"{(container_id, container_name)}: {container_pmem_dict[(container_id, container_name)]}")
    
    container_pmem_dict = OrderedDict(
        sorted(container_pmem_dict.items(), key=lambda x:x[1], reverse=True)
    )
    
    print("[Memory Usage per Container]")
    for i in container_pmem_dict.items():
        print(f"-Container: {i[0]}")
        print(f"\tㄴMemory Usage(%): {i[1]}")

def main(top_process_num: int = 10, check_gpu: bool = True, check_memory: bool = True):
    """
    Args:\n
        top_process_num (int, optional): Check docker containers' memory usage only among TOP_PROCESS_NUM processes' containers. Defaults to 10.\n
        check_gpu (bool, optional): Check docker containers occupying GPU Memory. Defaults to True.\n
        check_memory (bool, optional): Check docker containers occupying Memory. Defaults to True.\n
    """
    if check_gpu:
        check_container_occupying_GPU()
    if check_memory:
        check_container_occupying_memory(top_process_num)

if __name__ == "__main__":
    typer.run(main)