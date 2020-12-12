import sys
import subprocess
import os
import json 
import socket
from concurrent import futures
import time
import re
import datetime

def check_port(targetIp, portNumber, timeout):
   TCPsock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
   TCPsock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
   TCPsock.settimeout(timeout)
   try:
       TCPsock.connect((targetIp, portNumber))
       return (portNumber)
   except:
       return

def list_cmd_parser(output): 
    output = output.split("\n")   
    res = [] 
    for line in output: 
        if line.strip():
            res.append(line.strip()) 

    return res

def port_scanner(targetIp, timeout):
    threadPoolSize = 500
    portsToCheck = 65535

    executor = futures.ThreadPoolExecutor(max_workers=threadPoolSize)
    checks = [
        executor.submit(check_port, targetIp, port, timeout)
        for port in range(0, portsToCheck, 1)
    ]
    ports = []
    for response in futures.as_completed(checks):
        if (response.result()):
            print('Listening on port: {}'.format(response.result()))
            ports.append(response.result())
    return ports
   
def list_cmd_parser(output): 
    output = output.split("\n")   
    res = [] 
    for line in output: 
        if line.strip():
            res.append(line.strip()) 
    return res

def check_for_keywords(container_id):
    cmd = 'ls'
    temp = subprocess.Popen(['docker', 'exec', '-ti', container_id, 'find', '/', '-maxdepth', '1'], stdout = subprocess.PIPE, shell=False) 
    output = temp.communicate()[0].decode("utf-8")
    folders = list_cmd_parser(output)
    default_folders = ['/', '/root', '/usr', '/proc', '/opt', '/lib', '/bin', '/mnt', '/media', '/sys', '/dev', '/sbin', '']
    non_default_folders = []
    for f in folders:
        if f not in default_folders:
            non_default_folders.append(f)
    interesting_info = dict()
    keywords = ["password", "username", "credStore", "cred", "secret"]
    for n_f in non_default_folders:
        for k in keywords:
            stream = os.popen('docker exec -ti ' + container_id + ' grep  -r "' + k + '" /' + n_f)
            output = stream.read()
            lines = output.split("\n")
            # for each of the these files 
            # get file timestamp (and compare to base system file modificaiton time)
            for l in lines:
                parts = l.split(":")
                if len(parts) < 2:
                    continue
                file_name = parts[0]
                if file_name in interesting_info:
                    interesting_info[file_name] = [interesting_info[file_name], parts[1]]
                interesting_info[file_name] = parts[1]
    return interesting_info

def get_file_timestamp(file_name, container_id):
    temp = subprocess.Popen(['docker', 'exec', '-ti', container_id, 'stat', file_name], stdout = subprocess.PIPE, shell=False) 
    output = temp.communicate()[0].decode("utf-8")
    lines = output.split("\n")
    modify_time = lines[4]
    time = datetime.datetime.strptime(modify_time.replace('Modify: ', ''), '%Y-%m-%d %H:%M:%S.%f %z')
    return time

def filter_keyword_search(keyword_search, earliest_timestamp):
    new_keyword_search = dict()
    for f in keyword_search:
        if get_file_timestamp(f.replace('//', '/')) > earliest_timestamp:
            new_keyword_search[f] = keyword_search[f]
    return new_keyword_search

def anaylze_current_network(timeout):
    # scans open ports on localhost
    return port_scanner("127.0.0.1", timeout)

def search_docker(container_id):
    temp = subprocess.Popen(['docker', 'exec', '-ti', container_id, 'wget', 'https://raw.githubusercontent.com/0xmitsurugi/gimmecredz/master/gimmecredz.sh'], stdout = subprocess.PIPE, shell=False) 
    output = temp.communicate()[0].decode("utf-8")
    temp = subprocess.Popen(['docker', 'exec', '-ti', container_id, 'chmod', '+x', 'gimmecredz.sh'], stdout = subprocess.PIPE, shell=False) 
    output = temp.communicate()[0].decode("utf-8")
    temp = subprocess.Popen(['docker', 'exec', '-ti', container_id, 'bash', 'gimmecredz.sh'], stdout = subprocess.PIPE, shell=False)
    output = temp.communicate()[0].decode("utf-8")
    ansi_escape = re.compile(r'\x1B(?:[@-Z\\-_]|\[[0-?]*[ -/]*[@-~])')
    result = ansi_escape.sub('', output)
    return result

def find_user_installed_packages(container_id):
    temp = subprocess.Popen("docker exec -ti "  +  container_id + """ sh -c "(zcat $(ls -tr /var/log/apt/history.log*.gz); cat /var/log/apt/history.log) 2>/dev/null |  egrep '^(Commandline: apt(-get)? install)' |  grep -v aptdaemon |  egrep '^Commandline:'" """, stdout = subprocess.PIPE, shell=True)
    output = temp.communicate()[0].decode("utf-8")
    package_names = list()
    for o in output.split("\n"):
        o = o.strip()
        if o:
            package_names.append(o)
    return package_names

def get_docker_container_id(image_name):
    stream = os.popen('docker container ls')
    output = stream.read()
    lines = output.split("\n")[1:]
    for l in lines:
        line_items = l.split()
        container_id = line_items[0]
        image_name_found = line_items[1]
        if image_name_found == image_name:
            return container_id

def get_exposed_ports(image_name):
    stream = os.popen('docker inspect ' + image_name)
    output = stream.read()
    j_dict = json.loads(output)
    try:
        res = j_dict[0]["ContainerConfig"]["ExposedPorts"]
    except:
        res = None
    return res


def run_image(image_name):
    stream = subprocess.Popen('docker run ' + image_name, shell=True)

def json_to_str(json_dict):
    s = ''
    for key in json_dict:
        s += str(key) + ' : ' + str(json_dict[key])
        s += '\n'
    return s

def anaylze_docker_container(image_name, file_saved):
    run_image(image_name)
    time.sleep(120)
    container_id = get_docker_container_id(image_name)
    json_res = {}
    exposed_ports = get_exposed_ports(image_name)
    interesting_places = search_docker(container_id)
    keyword_search = check_for_keywords(container_id)
    early_time = get_file_timestamp('/etc/ssh/ssh_host_rsa_key')
    keyword_search = filter_keyword_search(keyword_search, early_time)
    cur_ports = anaylze_current_network(1000)
    package_names = find_user_installed_packages(container_id)
    json_res['exposed_ports_by_docker'] = exposed_ports
    json_res['password_finder'] = interesting_places
    json_res['listenting_ports'] = cur_ports
    json_res['package_names'] = package_names
    json_res['keyword_seacrh'] = keyword_search
    with open(file_saved, "w+") as f:
        json.dump(json_res, f, indent=4, sort_keys=True)
    print(json_to_str(json_res))
    stream = os.popen('docker stop ' + container_id)
    output = stream.read()
    print(output)
    time.sleep(5)
    stream = os.popen('docker rm ' + container_id)

def anyalze_containers(containers, save_dir):
    for c in containers:
        anaylze_docker_container(c, os.path.join(save_dir, c.replace("/", "") + ".json"))


    
# past containers : ["008ak89/ssh_enabled_server:1.0", "00theballs00/web_server", "openhack/minecraft-server"]
anyalze_containers(["008ak89/ssh_enabled_server:1.0"], "/home/student/Research/explore_docker/results")
