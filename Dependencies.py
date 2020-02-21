import paramiko
from threading import Thread
from Globals import nodes
def install_dependencies(node, user):
    client = paramiko.client.SSHClient()
    client.set_missing_host_key_policy(paramiko.client.AutoAddPolicy())
    client.load_system_host_keys()
    client.connect(node, username=user)

    t = client.get_transport()
    sftp = paramiko.SFTPClient.from_transport(t)
    local_file = "install_dependencies.sh"
    remote_file = "/root/install_dependencies.sh"
    print("Copying file: %s to path: %s" % (local_file, remote_file))
    sftp.put(local_file, remote_file)
    sftp.close()
    # get a session
    s = t.open_session()
    # set up the agent request handler to handle agent requests from the server
    paramiko.agent.AgentRequestHandler(s)
    # PF ring is disabled by default
    stdin, stdout, stderr = client.exec_command(
        "cd /root/; chmod +x install_dependencies.sh; ./install_dependencies.sh")
    for line in stdout.readlines():
        print(line)
    for line in stderr.readlines():
        print(line)


if __name__ == "__main__":

    '''
        This script installs dependencies  of Heartbeat (libtins, libcperm)
    '''

    threads = []
    for node, user, home_dir in nodes:
        if node == "localhost":
            continue
        t = Thread(target=install_dependencies,
                   args=(node, user,))
        t.start()
        threads.append(t)
    for t in threads:
        t.join()