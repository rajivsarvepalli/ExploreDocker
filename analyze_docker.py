import os
import re
import subprocess
from typing import List, Optional, Dict
import os.path as osp
import time
import requests
from port_analyzer.open_ports import anaylze_current_network
from private_info.external_searcher import search_docker
from software_finder.ubuntu import find_user_installed_packages
from internal.comparison import compare_similar_images
from internal.closeness import closeness
import itertools


class DockerExplorer:
    def __init__(self, num_sets: int) -> None:
        self.num_sets = num_sets
        self.containers = dict()

    def add_set(self, set_name: str, containers: List[str], save_dir: Optional[str] = ".") -> None:
        """Add to the docker explorer a "set" of docker containers that are similar in purpose.
        Creates json "profiles" for each container given.
        Parameters
        ----------
        set_name : str
            The name to give this set of containers
        containers : List[str]
            A list of containers so that docker pull c_str can be run.
        save_dir : Optional[str]
            A save dir to put output files.
        
        """
        self.containers[set_name] = containers
        for c in containers:
            self._anaylze_docker_container(c, osp.join(
                save_dir, c.replace("/", "") + ".json"))

    def compare_set(self, set_name: str, saved_dir: str, containers: Optional[List] = None, save_dir: Optional[str] = ".") -> None:
        """Compares a set of docker containers with every other container in the set.
        Outputs csv tables that show comparison data. These tables are saved in the given save_dir. 
        Parameters
        ----------
        set_name : str
            The name to retrieve a set of containers called that.
        saved_dir : str
            The location of where the json files were stored once add_set was called.
        containers : List[str]
            A list of containers that must have been added to a set previously. 
        save_dir : Optional[str]
            A save dir to put output files.
        """
        if not containers:
            containers = self.containers[set_name]
        for c, c1 in itertools.combinations(self.containers[set_name], 2):
            if c in containers and c1 in containers:
                c = c.replace("/", "")
                c1 = c1.replace("/", "")
                with open(osp.join(saved_dir, c + ".json")) as f:
                    jdict1 = json.load(f)
                with open(osp.join(saved_dir, c1 + ".json")) as f:
                    jdict2 = json.load(f)
                table1 = compare_similar_images(jdict1, jdict2)
                table1.to_csv(
                    osp.join(save_dir, c + '_to_' + c1 + '.csv'), index=False)

    def closeness(self, set_name: str, container1: str, container2: str, saved_dir: str) -> float:
        """Computes a closeness metric for two docker containers. 
        This float should represent a higher number for closer docker containers and lower for 
        different containers. It is highly based on the number of similar packages. 
        Parameters
        ----------
        set_name : str
            The name to retrieve a set of containers called that.
        saved_dir : str
            The location of where the json files were stored once add_set was called.
        containers : List[str]
            A list of containers that must have been added to a set previously. 
        save_dir : Optional[str]
            A save dir to put output files.
        """
        c_list = self.containers[set_name]
        if not (container1 in c_list and container2 in c_list):
            raise ValueError("Both container need to be in given the set")
        with open(osp.join(saved_dir, container2.replace("/", "") + ".json")) as f:
            jdict1 = json.load(f)
        with open(osp.join(saved_dir, container1.replace("/", "") + ".json")) as f:
            jdict2 = json.load(f)
        return closeness(jdict1, jdict2)

    def _anaylze_docker_container(image_name: str, file_name: str) -> None:
        self._run_image(image_name)
        time.sleep(120)
        container_id = _get_docker_container_id(image_name)
        json_res = {}
        exposed_ports = self._get_exposed_ports(image_name)
        interesting_places = search_docker(container_id)
        cur_ports = anaylze_current_network(1000)
        package_names = find_user_installed_packages(container_id, image_name)
        json_res['exposed_ports_by_docker'] = exposed_ports
        json_res['all_listenting_ports'] = cur_ports
        json_res['user_installed_packages'] = package_names
        json_res['os_version'] = self._get_os_version(container_id)
        docker_hub_info = self._get_json_query(image_name)
        json_res['date_image_pushed'] = docker_hub_info['last_updated']
        json_res['pulls'] = docker_hub_info['pull_count']
        json_res['docker_file'] = self._get_dockerfile(image_name)
        with open(file_saved, "w+") as f:
            json.dump(json_res, f, indent=4, sort_keys=True)
        stream = os.popen('docker stop ' + container_id)
        output = stream.read()
        time.sleep(5)
        stream = os.popen('docker rm ' + container_id)

    def _run_image(self, image_name: str) -> None:
        stream = subprocess.Popen('docker run ' + image_name, shell=True)

    def _get_dockerfile(self, image_name: str) -> str:
        temp = subprocess.Popen(
            "docker history --no-trunc " + image_name, stdout=subprocess.PIPE, shell=True)
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

    def _get_docker_container_id(self, image_name: str) -> Optional[int]:
        stream = os.popen('docker container ls')
        output = stream.read()
        lines = output.split("\n")[1:]
        for l in lines:
            line_items = l.split()
            container_id = line_items[0]
            image_name_found = line_items[1]
            if image_name_found == image_name:
                return container_id

    def _get_json_query(self, image_name: str) -> Dict:
        image_n = image_name.split(':')[0]
        url = 'https://hub.docker.com/v2/repositories/' + image_n
        reqstr = url
        req = requests.get(reqstr)
        resp = json.loads(req.content.decode('UTF-8'))
        return resp

    def _get_os_version(self, container_id: str) -> str:
        temp = subprocess.Popen("docker exec -ti " + container_id +
                                """ grep PRETTY /etc/*-release""", stdout=subprocess.PIPE, shell=True)
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

    def _get_exposed_ports(self, image_name: str) -> List:
        stream = os.popen('docker inspect ' + image_name)
        output = stream.read()
        j_dict = json.loads(output)
        try:
            res = j_dict[0]["ContainerConfig"]["ExposedPorts"]
        except:
            res = None
        return res
