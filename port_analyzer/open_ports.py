import socket
from concurrent import futures


def check_port(targetIp, portNumber, timeout):
   TCPsock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
   TCPsock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
   TCPsock.settimeout(timeout)
   try:
       TCPsock.connect((targetIp, portNumber))
       return (portNumber)
   except:
       return


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
    
def anaylze_current_network(timeout):
    # scans open ports on localhost
    return port_scanner("127.0.0.1", timeout)