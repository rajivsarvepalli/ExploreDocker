import os
import subprocess

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