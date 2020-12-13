import sys
import subprocess
import os
import json 
import socket
from concurrent import futures
import time
import re
import datetime
import requests
import pandas as pd 

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

def find_user_installed_packages(container_id, image_name):
    temp = subprocess.Popen("docker exec -ti "  +  container_id + """ sh -c "(zcat $(ls -tr /var/log/apt/history.log*.gz); cat /var/log/apt/history.log) 2>/dev/null |  egrep '^(Commandline: apt(-get)? install)' |  grep -v aptdaemon |  egrep '^Commandline:'" """, stdout = subprocess.PIPE, shell=True)
    output = temp.communicate()[0].decode("utf-8")
    
    package_names = list()

    for o in output.split("\n"):
        o = o.replace('Commandline: apt-get install -y', '')
        o = o.replace('Commandline: apt-get install ', '')
        o = o.strip()
        if o:
            package_names.extend(o.split(" "))
    package_names_and_verson = dict()
    for p in package_names:
        temp = subprocess.Popen("docker exec -ti "  +  container_id + " " + p + " --version", stdout = subprocess.PIPE, shell=True)
        output = temp.communicate()[0].decode("utf-8")
        if re.search('^(\d+\.)?(\d+\.)?(\*|\d+)$', output):
            package_names_and_verson[p] = output
        else:
             package_names_and_verson[p] = 'unknown'
    stream = os.popen('docker inspect ' + image_name)
    output = stream.read()
    j_dict = json.loads(output)
    docker_packages = dict()
    try:
        res = j_dict[0]["Config"]["Env"]
    except:
        res = []
    for r in res:
        if 'version' in r.lower():
            package, version = r.split("=")[0], r.split("=")[1]
            docker_packages[package] = version
    package_names_and_verson.update(docker_packages)
    return package_names_and_verson

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

# given two containers compute the closeness between them 
def closeness(j_dict1, j_dict2):
    #j_dict1 = json.load(json_res1)
    #j_dict2 = json.load(json_res2)
    packages1 = j_dict1['user_installed_packages']
    packages2 = j_dict2['user_installed_packages']
    same_packges = 0
    similar_packges = list()
    for p in packages1:
        for p2 in packages2:
            if p.lower() in p2.lower() or p2.lower() in p.lower():
                # same package
                same_packges += 1
                similar_packges.append((p.lower(), packages1[p].lower(), p2.lower(), packages2[p2].lower()))
                # same version
                if packages2[p2].lower() in packages1[p].lower() or packages1[p].lower() in packages2[p2].lower():
                    same_packges += 1
                break
    min_len = len(packages1) if len(packages1) > len(packages2) else len(packages2)
    return same_packges/ (min_len*2), similar_packges

def get_json_query(image_name):
    image_n = image_name.split(':')[0]     
    url = 'https://hub.docker.com/v2/repositories/'  + image_n
    reqstr = url
    req = requests.get(reqstr)
    resp = json.loads(req.content.decode('UTF-8'))
    return resp
    
def get_os_version(container_id):
    temp = subprocess.Popen("docker exec -ti "  +  container_id + """ grep PRETTY /etc/*-release""", stdout = subprocess.PIPE, shell=True)
    output = temp.communicate()[0].decode("utf-8")
    lines = output.split("\n")
    # for each of the these files 
    # get file timestamp (and compare to base system file modificaiton time)
    for l in lines:
        parts = l.split(":")
        if len(parts) < 2:
            continue
        file_name = parts[0]
        os_version = parts[1]
        if 'PRETTY_NAME' in os_version:
            os_version = os_version.replace("PRETTY_NAME=", '')
            os_version = os_version.replace('"', '')
            os_version = os_version.strip()
            return os_version

def get_dockerfile(image_name):
    
    temp = subprocess.Popen("docker history --no-trunc "  +  image_name, stdout = subprocess.PIPE, shell=True)
    output = temp.communicate()[0].decode("utf-8")
    lines = output.split("\n")
    docker_file = list()
    lines = lines[1:]
    for l in lines:
        command = l.split("ago")[-1]
        command = command.strip()
        command = command.split("   ")[0]
        docker_file.append(command)
    return docker_file

def compare_similar_images(j_dict1, j_dict2):
    packages1 = j_dict1['user_installed_packages']
    packages2 = j_dict2['user_installed_packages']
    same_packages = list()
    different_packages = list()
    different_versions = list()
    found_package = False
    for p in packages1:
        for p2 in packages2:
            
            if p.lower() in p2.lower() or p2.lower() in p.lower():
                # same package
                found_package = True
                same_packages.append(p.lower())
                # same version
                if packages2[p2].lower() in packages1[p].lower() or packages1[p].lower() in packages2[p2].lower():
                    pass
                else:
                    different_versions.append((p.lower(), packages1[p].lower(), packages2[p2].lower()))
                break
        if not found_package:
            different_packages.append(p.lower())
    tabular_similarity_info = pd.DataFrame(
            {'similar_packages': pd.Series(same_packages),
            'different_packages': pd.Series(different_packages),
            'package_version1_version2': pd.Series(different_versions)
            })
    return tabular_similarity_info

def anaylze_docker_container(image_name, file_saved):
    run_image(image_name)
    time.sleep(120)
    container_id = get_docker_container_id(image_name)
    json_res = {}
    exposed_ports = get_exposed_ports(image_name)
    interesting_places = search_docker(container_id)
    cur_ports = anaylze_current_network(1000)
    package_names = find_user_installed_packages(container_id, image_name)
    json_res['exposed_ports_by_docker'] = exposed_ports
    json_res['all_listenting_ports'] = cur_ports
    json_res['user_installed_packages'] = package_names
    json_res['os_version'] = get_os_version(container_id)
    docker_hub_info  = get_json_query(image_name)
    json_res['date_image_pushed'] = docker_hub_info['last_updated']
    json_res['pulls'] = docker_hub_info['pull_count']
    json_res['docker_file'] = get_dockerfile(image_name)
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
#anyalze_containers(["008ak89/ssh_enabled_server:1.0"], "/home/researchmachine/Research/results/")
with open("/home/researchmachine/Research/results/serverninjaminecraft:v0.0.6.json") as f:
    jdict1 = json.load(f)
with open("/home/researchmachine/Research/results/openhackminecraft-server:latest.json") as f:
    jdict2 = json.load(f)
print(closeness(jdict1, jdict2))
table1 = compare_similar_images(jdict1, jdict2)
table2 = compare_similar_images(jdict2, jdict1)
table1.to_csv("/home/researchmachine/Research/results/" + 'serverninjaminecraft:v0.0.6_to_openhackminecraft-server:latest.csv', index=False)
table2.to_csv("/home/researchmachine/Research/results/" + 'openhackminecraft-server:latest_to_serverninjaminecraft:v0.0.6.csv', index=False)

