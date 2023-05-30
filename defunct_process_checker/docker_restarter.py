from defunct_checker import *

def print_defunct_list():
    container_id_ppid_defunct_list = []
    defunct_ppid_count = get_defunct_ppid_count()
    docker_container_id_name_list = get_docker_container_id_name_list()
    for ppid, count in defunct_ppid_count.items():
        container_line = get_container_line(ppid)
        if container_line=='': continue
        container_id=''
        container_name=''
        for i in docker_container_id_name_list: 
            if i[0] in container_line:
                container_id = i[0]
                container_name = i[1]
                break
        container_id_ppid_defunct_list.append((container_name, container_id, ppid, count))
        
        
    
    printFormat = '%-10s\t%-20s\t%-15s\t%-10s\t%-10s'
    
    print(printFormat % ("[Num]","[ConName]", "[ConID]", "[PPID]", "[Defuncts]"))
    n = 0
    for i in container_id_ppid_defunct_list:
        n += 1
        print(printFormat % (n, i[0], i[1], i[2], i[3]))
    
    return n, container_id_ppid_defunct_list

def main():
    total_container_num, container_id_ppid_defunct_list = print_defunct_list()
    
    while True:
        user_input = input("Which number's docker container do you want to restart(q to quit): ")
        if user_input == 'q':
            break
        
        if user_input.isdigit() and int(user_input) > 0 and int(user_input) <= total_container_num:
            print("Right input!!!")
            num_to_restart = int(user_input)
            container_id_to_restart = container_id_ppid_defunct_list[num_to_restart-1][1]
            print(container_id_to_restart)
            
            # TODO: activate the code below... DON'T restart any docker container without permission to restart it.
            # result = shell_run(f"docker restart {container_id_to_restart}")
            # print(result)
        else:
            print("Wrong input...")
    
    
    

if __name__ == "__main__":
    main()