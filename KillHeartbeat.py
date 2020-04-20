import paramiko
from threading import Thread
import json
import sys

from Processing.IPv4SSHClient import IPv4SSHClient

def kill_heartbeat(node, user):
    client = IPv4SSHClient()
    client.set_missing_host_key_policy(paramiko.client.AutoAddPolicy())
    client.load_system_host_keys()
    client.connect(node, username=user)
    t = client.get_transport()
    # get a session
    s = t.open_session()
    # set up the agent request handler to handle agent requests from the server
    paramiko.agent.AgentRequestHandler(s)
    # PF ring is disabled by default
    stdin, stdout, stderr = client.exec_command("sudo -S pkill -f Heartbeat")
    for line in stdout.readlines():
        print(line)
    for line in stderr.readlines():
        print(line)


if __name__ == "__main__":

    '''
        This script installs dependencies  of Heartbeat (libtins, libcperm)
    '''
    nodes = json.load(open(sys.argv[1]))
    threads = []
    for node in nodes["nodes"]:
        if node["server"] == "localhost":
            continue
        t = Thread(target=kill_heartbeat,
                   args=(node["server"], node["user"],))
        t.start()
        threads.append(t)
    for t in threads:
        t.join()