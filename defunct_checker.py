import os
import time
import schedule
import requests
from datetime import datetime
from collections import OrderedDict

TIMEOUT = 1 # Schedule every TIMEOUT minutes
THRESHOLD = 20 # Find the container IDs with most defuncts when the total number of defuncts > THRESHOLD
TOPCONTAINER = 3 # 찾아서 알림으로 보낼 Container ID 최대 개수, defuncts 개수가 많은 순으로 최대 TOPCONTAINER 개만큼 찾는다.



def shell_run(command):
    # print('[SHELL] {command}'.format(command=command))
    output = os.popen(command).read()
    return output

def get_docker_container_id_name_list():
    container_id_name_list = shell_run("docker ps --format \"table {{.ID}}\t{{.Names}}\"").split('\n')
    container_id_name_list = list(filter(None, container_id_name_list)) # filtering to remove empty string element
    container_id_name_list = [(line.split()[0][0:6], line.split()[1]) for line in container_id_name_list if line.split()[0] != 'CONTAINER']
    
    return container_id_name_list

# pid를 받아 해당 process가 돌아가고 있는 container의 id를 포함하는 process 정보 라인을 찾아서 반환
# 못 찾을 경우 빈 문자열 '' 반환
def get_container_line(pid):
    next_ppid = pid
    container_line=''
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
            print("Cannot find the line with \'containerd-shim\' keyword..")
            break
    
    return container_line

def get_defunct_ppid_count():
    defunct_ppid_list = shell_run("ps -ef | grep defunct | grep -v grep | grep -v 'defunct_checker' | awk '{print $3}'").split('\n')
    defunct_ppid_list = list(filter(None, defunct_ppid_list)) # filtering to remove empty string element
    defunct_ppid_count = {}
    for ppid in defunct_ppid_list:
        if defunct_ppid_count.get(ppid): defunct_ppid_count[ppid]+=1
        else: defunct_ppid_count[ppid]=1
    defunct_ppid_count = OrderedDict(sorted(defunct_ppid_count.items(), key=lambda item: -item[1]))
    return defunct_ppid_count

def check_defunct():
    total_defunct_num = int(shell_run("ps -ef | grep defunct | grep -v grep | grep -v 'defunct_checker' | wc -l"))

    now = datetime.now()
    print("###########################", now, "###########################")
    print("The result of [ps -ef | grep defunct | grep -v grep | grep -v 'defunct_checker']:")
    print(shell_run("ps -ef | grep defunct | grep -v grep | grep -v 'defunct_checker'"))

    if total_defunct_num > THRESHOLD:
        container_id_ppid_defunct_list = []
        defunct_ppid_count = get_defunct_ppid_count()
        num_appended_container_id=0
        docker_container_id_name_list = get_docker_container_id_name_list()
        for ppid, count in defunct_ppid_count.items():
            container_line = get_container_line(ppid)
            if container_line=='': continue
            container_id=''
            container_name=''
            for i in docker_container_id_name_list: 
                # TODO: 아이디에 더해서 container 이름도 추가하기
                if i[0] in container_line:
                    container_id = i[0]
                    container_name = i[1]
                    break
            container_id_ppid_defunct_list.append((container_name, container_id, ppid, count))
            num_appended_container_id += 1
            if num_appended_container_id >= TOPCONTAINER:
                break

        
        printFormat = '%-10s\t%-8s\t%-8s\t%-8s'
        
        print(printFormat % ("[ConName]", "[ConID]", "[PPID]", "[Dfncts]"))
        for i in container_id_ppid_defunct_list:
            print(printFormat % (i[0][:8], i[1], i[2], i[3]))

        ## Notification is needed.
        push_content=''
        push_content += (printFormat % ("[ConName]", "[ConID]", "[PPID]", "[Dfncts]")) + '\n'
        for i in container_id_ppid_defunct_list:
            push_content += (printFormat % (i[0][:8], i[1], i[2], i[3])) + '\n'
        push_notification(push_content)
        print("\nNofication is sended.")
        
    else:
        print(f"Number of defunct processes is less than THRESHOLD.\n \
                The Number of defunct processes: {total_defunct_num}. \
        ")
    
    print("\n\n---------------------------------------------------------------------------------\n\n")


def push_notification(content):
    requests.post("https://ntfy.sh/defunct_checker_for_docker",
        data=f"{content}".encode('utf-8'),
        headers={
            "Title": "Defunct Checker"
        })

def main():
    print(f"Run the defunct checker every {TIMEOUT} minutes.\n\n")
    check_defunct()

    schedule.every(TIMEOUT).minutes.do(check_defunct)
    # schedule.every(10).seconds.do(check_defunct)
    while True:
        schedule.run_pending()
        time.sleep(1)

if __name__ == "__main__":
    main()