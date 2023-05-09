import os
import time
import schedule
import requests


TIMEOUT = 30 # schedule every TIMEOUT minutes
THRESHOLD = 20

def shell_run(command):
    # print('[SHELL] {command}'.format(command=command))
    output = os.popen(command).read()
    return output

def get_docker_container_id_list():
    container_ids = shell_run("docker ps -a | awk \'{print $1}\'")
    container_id_list = container_ids.split('\n')
    container_id_list = list(filter(None, container_id_list)) # filtering to remove empty string element
    return container_id_list

# pid를 받아 해당 process가 돌아가고 있는 container의 id를 찾아서 반환
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

def find_container_id_with_most_defunct():
    total_defunct_num = int(shell_run("ps -ef | grep defunct | grep -v grep | grep -v 'defunct_checker' | wc -l"))

    defunct_ppid_list = shell_run("ps -ef | grep defunct | grep -v grep | grep -v 'defunct_checker' | awk '{print $3}'").split('\n')
    defunct_ppid_list = list(filter(None, defunct_ppid_list)) # filtering to remove empty string element
    print()
    defunct_ppid_count = {}
    for ppid in defunct_ppid_list:
        if defunct_ppid_count.get(ppid): defunct_ppid_count[ppid]+=1
        else: defunct_ppid_count[ppid]=1

    print('ppids with defunct: ', defunct_ppid_count)
    max_defunct_ppid = max(defunct_ppid_count, key=defunct_ppid_count.get)
    print('ppid with the most defunct: ', max_defunct_ppid)

    ## Find container id
    container_line = get_container_line(max_defunct_ppid)
    if container_line == '':
        return '', max(defunct_ppid_count.values()), total_defunct_num

    print('the process creating container: ', container_line)

    ## Check if there is such an id among the docker container ids
    container_id=''
    for i in get_docker_container_id_list():
        if i in container_line:
            container_id = i
            break
    if container_id=='':
        print('There is no such id among the docker container ids')
    print(container_id)
    return container_id, max(defunct_ppid_count.values()), total_defunct_num

def check_defunct():
    total_defunct_num = int(shell_run('ps -ef | grep defunct | grep -v grep | wc -l'))
    if total_defunct_num > THRESHOLD:
        container_id, defunct_num, total_defunct_num = find_container_id_with_most_defunct()
        print(f"The container {container_id} has {defunct_num} defuncts among {total_defunct_num} defuncts.")
        ## Notification is needed.
        push_content = f"The container {container_id} has {defunct_num} defuncts among {total_defunct_num} defuncts."
        push_notification(push_content)
    else:
        print(f"Number of defunct processes is less than THRESHOLD.\n \
                The Number of defunct processes: {total_defunct_num}. \
        ")


def push_notification(content):
    requests.post("https://ntfy.sh/defunct_checker_for_docker",
        data=f"{content}".encode('utf-8'),
        headers={
            "Title": "Defunct Checker"
        })

def main():
    print(f"Run the defunct checker every {TIMEOUT} minutes.")
    # schedule.every(TIMEOUT).minutes.do(check_defunct)
    schedule.every(10).seconds.do(check_defunct)
    while True:
        schedule.run_pending()
        time.sleep(1)

if __name__ == "__main__":
    main()