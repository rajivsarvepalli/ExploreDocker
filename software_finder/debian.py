import subprocess
import os
import re
import json

def grab_version(output):
    if not output:
        return None
    if re.search('(\d+\.)(\d+\.)?(\*|\d+)', output):
        result =  re.findall('(\d+\.)(\d+\.)?(\*|\d+)',output)[0]
        return "".join(result)
    return None
    
def find_user_installed_packages(container_id, image_name, default_installs='default_installs.txt'):
    with open(default_installs) as f:
        default_packages = f.read()
    default_packs = list()
    for line in default_packages.split("\n"): 
        package = line.split("\t")[0]
        package = package.strip()
        default_packs.append(package)
    temp = subprocess.Popen("docker exec -ti "  +  container_id + """ dpkg --get-selections""", stdout = subprocess.PIPE, shell=True)
    output = temp.communicate()[0].decode("utf-8")
    package_names = list()
    for line in output.split("\n"):
        package = line.split("\t")[0]
        package = package.strip()
        if package not in default_packs:
            package_names.append(package)
    package_names_and_verson = dict()
    for p in package_names:
        try:
            temp = subprocess.run("docker exec -ti "  +  container_id + " " + p + " --version", shell=True, timeout=1,capture_output=True, text=True)
            output_version = temp.stdout
            if not output_version:
                output_version = temp.stderr
        except subprocess.TimeoutExpired:
            output_version = None
        try:
            temp = subprocess.run("docker exec -ti "  +  container_id + " " + p + " -v", shell=True, timeout=1, capture_output=True, text=True)
            output_v = temp.stdout
            if not output_v:
                output_v = temp.stderr
        except subprocess.TimeoutExpired:
            output_v = None
        try:
            temp = subprocess.run("docker exec -ti "  +  container_id + " " + p + " -V", shell=True, timeout=1, capture_output=True, text=True)
            output_V = temp.stdout
            if not output_V:
                output_V = temp.stderr
        except subprocess.TimeoutExpired:
            output_V = None
        version_num = grab_version(output_version) or grab_version(output_v) or grab_version(output_V)
        if version_num:
            package_names_and_verson[p] = version_num
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