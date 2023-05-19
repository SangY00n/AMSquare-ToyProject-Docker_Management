import os
from typing import Optional
from loguru import logger
from collections import defaultdict, OrderedDict

def shell_run(command: str) -> str:
    output = os.popen(command).read()
    return output

def get_docker_container_id_name_dict() -> dict[str, str]:
    container_id_name_list = shell_run(
        'docker ps --format "table {{.ID}}\t{{.Names}}"'
    ).split("\n")
    container_id_name_list = list(
        filter(None, container_id_name_list)
    )  # filtering to remove empty string element

    container_id_name_dict = {
        line.split()[0][:8]: line.split()[1]
        for line in container_id_name_list
        if line.split()[0] != "CONTAINER"
    }
    return container_id_name_dict


# pid를 받아 해당 process가 돌아가고 있는 container의 id를 포함하는 process 정보 라인을 찾아서 반환
# 못 찾을 경우 None 반환
def get_container_line(pid: str) -> Optional[str]:
    next_ppid = pid
    container_line = None
    container_line_flag = False
    depth = 0
    while container_line_flag is False:
        grep_results = shell_run(
            "ps -ef | grep {ppid} | grep -v grep".format(ppid=next_ppid)
        ).split("\n")
        grep_results = list(
            filter(None, grep_results)
        )  # filtering to remove empty string element
        for line in grep_results:
            line_to_list = line.split()

            if "containerd-shim" in line_to_list:
                container_line = line
                container_line_flag = True
                break

            if line_to_list[1] == next_ppid:
                next_ppid = line_to_list[2]
        depth = depth + 1
        if depth > 10:
            logger.error(
                f"Cannot find the line with 'containerd-shim' keyword for the pid {pid}"
            )
            break
    # container_line's example: root     14969  2098  0 Apr20 ?        00:06:59 containerd-shim -namespace moby -workdir /var/lib/containerd/io.containerd.runtime.v1.linux/moby/6c3b6dc90fd7ff56dd296fe2ffc34656211de25bb3d6207d721dc883b939f228 -address /run/containerd/containerd.sock -containerd-binary /usr/bin/containerd -runtime-root /var/run/docker/runtime-runc
    return container_line


def get_container_id_name_from_container_line(
    line: str,
) -> tuple[Optional[str], Optional[str]]:
    docker_container_id_name_dict = get_docker_container_id_name_dict()
    line_to_list = line.replace("/", " ").split()
    for i in line_to_list:
        if i[:8] in docker_container_id_name_dict:
            return (i[:8], docker_container_id_name_dict[i[:8]])

    logger.error(f"Cannot find the container id and name for the process: {line}")
    return (None, None)


def check_container_occupying_memory(top_process_num: int):
    pid_pmem_list = shell_run(f"ps aux --sort=-pmem | head -{top_process_num} | awk '{{print $2, $4}}'").split('\n')[1:]
    pid_pmem_list = list(
        filter(None, pid_pmem_list)
    )  # filtering to remove empty string element
    pid_pmem_list = [(pid_pmem.split()[0], pid_pmem.split()[1]) for pid_pmem in pid_pmem_list]

    container_pmem_dict: defaultdict[(str, str), float] = defaultdict(float)
    
    for (pid, pmem) in pid_pmem_list:
        container_line = get_container_line(pid)
        if container_line == None:
            continue
        container_id, container_name = get_container_id_name_from_container_line(container_line)
        if container_id != None and container_name != None:
            container_pmem_dict[(container_id, container_name)] += float(pmem)
            # print(f"{(container_id, container_name)}: {container_pmem_dict[(container_id, container_name)]}")
    
    container_pmem_dict = OrderedDict(
        sorted(container_pmem_dict.items(), key=lambda x:x[1], reverse=True)
    )
    
    for i in container_pmem_dict.items():
        print(i[0], i[1])
        

def check_container_occupying_GPU(type:str):
    
    nvidiasmi_line_list = shell_run("nvidia-smi | awk '{print $2,$3,$4,$5,$6,$7,$8}'").split('\n')
    nvidiasmi_line_list = list(
        filter(None, nvidiasmi_line_list)
    )  # filtering to remove empty string element
    process_part_line_count=0
    process_occupying_gpu_list = []
    for line in nvidiasmi_line_list:
        if process_part_line_count>0:
            # GPU GI CI PID Type Process name 라인이랑
            # ID ID Usage | 라인 날리기
            if process_part_line_count < 4:
                process_part_line_count += 1
            else:
                # GPU를 사용하고 있는 process를 기록
                print(line)
                line_to_list = line.split()
                if len(line_to_list) >= 7:
                    process_occupying_gpu_list.append((line_to_list[3], line_to_list[0], line_to_list[4], line_to_list[6])) # ('pid','GPUNum', 'Type', 'MemUsage')
            
        elif 'Processes' in line:
            process_part_line_count = 1
    
    print(process_occupying_gpu_list)
    
    container_GPU_dict = defaultdict(list)
    
    for pid, GPUNum, Type, MemUsage in process_occupying_gpu_list:
        # if type=='C' or 'c':
        #     pass
        # elif type=='G' or 'g':
        #     pass
        #     #TODO:check only graphic type process
        # else:
        container_line = get_container_line(pid)
        if container_line == None:
            continue
        container_id, container_name = get_container_id_name_from_container_line(container_line)
        if container_id != None and container_name != None:
            container_GPU_dict[(container_id, container_name)].append((pid, GPUNum, Type, MemUsage))
    
    for k,v in container_GPU_dict.items():
        print(k)
        for vv in v:
            print(f"\t{vv}")

    


if __name__ == "__main__":
    # check_container_occupying_memory(10)
    check_container_occupying_GPU('c')