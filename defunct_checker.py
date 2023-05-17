import os
from typing import Optional
import time
import schedule
import requests
from datetime import datetime
from collections import OrderedDict
import argparse

from loguru import logger


def shell_run(command: str) -> str:
    # print('[SHELL] {command}'.format(command=command))
    output = os.popen(command).read()
    return output

def get_docker_container_id_name_dict() -> dict[str, str]:
    container_id_name_list = shell_run("docker ps --format \"table {{.ID}}\t{{.Names}}\"").split('\n')
    container_id_name_list = list(filter(None, container_id_name_list)) # filtering to remove empty string element
    
    container_id_name_dict = {line.split()[0][:8]: line.split()[1] for line in container_id_name_list if line.split()[0] != 'CONTAINER'}
    return container_id_name_dict

# pid를 받아 해당 process가 돌아가고 있는 container의 id를 포함하는 process 정보 라인을 찾아서 반환
# 못 찾을 경우 None 반환
def get_container_line(pid:str)->Optional[str]:
    next_ppid = pid
    container_line=None
    container_line_flag = False
    depth=0
    while(container_line_flag is False):
        grep_results = shell_run("ps -ef | grep {ppid} | grep -v grep".format(ppid=next_ppid)).split('\n')
        grep_results = list(filter(None, grep_results)) # filtering to remove empty string element
        # print(grep_results)
        for line in grep_results:
            line_to_list = line.split()
            # print(line_to_list)

            if 'containerd-shim' in line_to_list:
                container_line = line
                container_line_flag = True
                break

            if line_to_list[1]==next_ppid:
                next_ppid=line_to_list[2]
        depth=depth+1
        if depth > 3:
            logger.error(f"Cannot find the line with 'containerd-shim' keyword for the pid {pid}")
            # print("Cannot find the line with 'containerd-shim' keyword..")
            break
    # container_line's example: root     14969  2098  0 Apr20 ?        00:06:59 containerd-shim -namespace moby -workdir /var/lib/containerd/io.containerd.runtime.v1.linux/moby/6c3b6dc90fd7ff56dd296fe2ffc34656211de25bb3d6207d721dc883b939f228 -address /run/containerd/containerd.sock -containerd-binary /usr/bin/containerd -runtime-root /var/run/docker/runtime-runc
    return container_line

def get_container_id_name_from_container_line(line:str) -> tuple[Optional[str], Optional[str]]:
    docker_container_id_name_dict = get_docker_container_id_name_dict()
    line_to_list = line.replace('/', ' ').split()
    for i in line_to_list:
        if i[:8] in docker_container_id_name_dict:
            return (i[:8], docker_container_id_name_dict[i[:8]])
    
    logger.error(f"Cannot find the container id and name for the process: {line}")
    # print(f"Cannot find the container id and name for the process: {line}")
    return (None, None)
        

def get_defunct_ppid_count() -> OrderedDict[str, int]:
    defunct_ppid_list = shell_run("ps -ef | grep defunct | grep -v grep | grep -v 'defunct_checker' | awk '{print $3}'").split('\n')
    defunct_ppid_list = list(filter(None, defunct_ppid_list)) # filtering to remove empty string element
    defunct_ppid_count = {}
    for ppid in defunct_ppid_list:
        if defunct_ppid_count.get(ppid): defunct_ppid_count[ppid]+=1
        else: defunct_ppid_count[ppid]=1
    defunct_ppid_count = OrderedDict(sorted(defunct_ppid_count.items(), key=(lambda item: -item[1])))
    return defunct_ppid_count

def check_defunct(threshold:int, container_num:int):
    total_defunct_num = int(shell_run("ps -ef | grep defunct | grep -v grep | grep -v 'defunct_checker' | wc -l"))

    now = datetime.now()
    logger.info(f"########################### {now} ###########################")
    logger.info("The result of [ps -ef | grep defunct | grep -v grep | grep -v 'defunct_checker']:")
    logger.info("\n"+ shell_run("ps -ef | grep defunct | grep -v grep | grep -v 'defunct_checker'"))
    # print("###########################", now, "###########################")
    # print("The result of [ps -ef | grep defunct | grep -v grep | grep -v 'defunct_checker']:")
    # print(shell_run("ps -ef | grep defunct | grep -v grep | grep -v 'defunct_checker'"))

    container_id_ppid_defunct_list = []
    defunct_ppid_count = get_defunct_ppid_count()
    num_appended_container_id=0
    for ppid, count in defunct_ppid_count.items():
        container_line = get_container_line(ppid)
        if container_line == None: continue
        
        container_id, container_name = get_container_id_name_from_container_line(container_line)
        
        if container_id is None or container_name is None:
            logger.error(f"Cannot find proper container id/name for defunct pid {ppid}")
            # print(f"Cannot find proper container id/name for defunct pid {ppid}")
            continue
        else:
            container_id_ppid_defunct_list.append((container_name, container_id, ppid, count))
            num_appended_container_id += 1
        if num_appended_container_id >= container_num:
            break

    
    printFormat = '%-20s\t%-8s\t%-8s\t%-8s'
    logger.info(f"Total defuncts number is {total_defunct_num}.\n")
    logger.info(printFormat % ("[ConName]", "[ConID]", "[PPID]", "[Dfncts]"))
    # print(f"Total defuncts number is {total_defunct_num}.\n")    
    # print(printFormat % ("[ConName]", "[ConID]", "[PPID]", "[Dfncts]"))
    for i in container_id_ppid_defunct_list:
        logger.info(printFormat % (i[0], i[1], i[2], i[3]))
        # print(printFormat % (i[0], i[1], i[2], i[3]))

    if total_defunct_num > threshold:
        ## Notification is needed.
        push_content=''
        push_content += (printFormat % ("[ConName]", "[ConID]", "[PPID]", "[Dfncts]")) + '\n'
        for i in container_id_ppid_defunct_list:
            push_content += (printFormat % (i[0], i[1], i[2], i[3])) + '\n'
        push_notification(push_content)
        
    else:
        logger.info(f"Number of defunct processes is less than THRESHOLD.")
        logger.info(f"The Number of defunct processes: {total_defunct_num}.")
        # print(f"Number of defunct processes is less than THRESHOLD.\n \
        #         The Number of defunct processes: {total_defunct_num}. \
        # ")
    
    logger.info("\n\n---------------------------------------------------------------------------------\n\n")
    # print("\n\n---------------------------------------------------------------------------------\n\n")


def push_notification(content:str):
    try:
        requests.post("https://ntfy.sh/defunct_checker_for_docker",
            data=f"{content}".encode('utf-8'),
            headers={
                "Title": "Defunct Checker"
            }, timeout=10)
        logger.info("\nNofication is sended.")
    except requests.exceptions.RequestException as e:
        logger.error(f"[Error in the Notification step] Error occurred: {e}")

def main():
    parser = argparse.ArgumentParser(description = "Arguments for the defunct checker.")
    parser.add_argument('-t', '--timeout', required=False, type=int, default=30, help="The defunct checker will be scheduled every TIMEOUT minutes. (default: 30)")
    parser.add_argument('--threshold', required=False, type=int, default=100, help="Find the container IDs with most defuncts when the total number of defuncts > THRESHOLD. (default: 100)")
    parser.add_argument('-c', '--container_num', required=False, type=int, default=5, help="Find top CONTAINER_NUM container IDs with most defuncts. (default: 5)")
    parser.add_argument('-m', action="store_true", help="Manually enter parameters... Entered parameters will be prioritized.")
    args = parser.parse_args()
    timeout = args.timeout
    threshold = args.threshold
    container_num = args.container_num
    
    if args.m == True: 
        timeout = int(input("Please enter TIMEOUT value: "))
        threshold = int(input("Please enter THRESHOLD value: "))
        container_num = int(input("Please enter CONTAINER_NUM value: "))
    
    log_file_time = datetime.today().strftime("%Y%m%d_%H%M%S")
    logger.add(f"defunct_checker_log_{log_file_time}.log", rotation="5 MB")
    
    logger.info(f"Run the defunct checker every {timeout} minutes.\n")
    logger.info(f"The defunct checker will notify the container IDs with most defuncts when the total number of defuncts > {threshold}\n")
    logger.info(f"The defunct checker will find top {container_num} container IDs with most defuncts\n\n")
    # print(f"Run the defunct checker every {timeout} minutes.\n")
    # print(f"The defunct checker will notify the container IDs with most defuncts when the total number of defuncts > {threshold}\n")
    # print(f"The defunct checker will find top {container_num} container IDs with most defuncts\n\n")

    check_defunct(threshold, container_num)

    schedule.every(timeout).minutes.do(check_defunct, threshold, container_num)
    # schedule.every(10).seconds.do(check_defunct, threshold, container_num) # for debugging
    while True:
        schedule.run_pending()
        time.sleep(1)

if __name__ == "__main__":
    main()