import os
import json
import paramiko
import sys

from threading import Thread
from subprocess import Popen, PIPE
from Processing.IPv4SSHClient import IPv4SSHClient

password = ""


def rm(path, sftp):
    files = sftp.listdir(path)
    for f in files:
        filepath = os.path.join(path, f)
        try:
            sftp.remove(filepath)
        except IOError:
            rm(filepath, sftp)
    sftp.rmdir(path)


def clean(node, user, home):
    client = IPv4SSHClient()
    client.load_system_host_keys()
    client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    print("Connecting to %s \n with username=%s... \n" % (node, user))
    client.connect(node, username=user, password=password)
    t = client.get_transport()
    sftp = paramiko.SFTPClient.from_transport(t)
    print("Cleaning Heartbeat dir")
    try:
        rm(home + "Heartbeat/", sftp)
    except IOError as e:
        print(e)
    sftp.close()
    t.close()
    client.close()


def rsync(node, user, home):
    cmd = (
        "cd ~/Heartbeat; "
        "rsync -v --progress --stats -a -m  -e 'ssh -o StrictHostKeyChecking=no' "
        "--exclude='*build*' --exclude='*cmake-build*' --exclude='*.git' "
        "--exclude='*.idea' --exclude='resources/*' --exclude='*.libs' "
        "--exclude='.gitlab' "
        " /home/survey/Heartbeat/ " + user + "@" + node + ":~/Heartbeat/"
    )

    print(cmd)

    process = Popen(cmd, stdout=PIPE, stderr=PIPE, shell=True)
    out, err = process.communicate()
    out = [line.decode("utf-8") for line in out.splitlines()]
    err = [line.decode("utf-8") for line in err.splitlines()]
    for line in out:
        print(node + ": " + line)
    for line in err:
        print(node + ": " + line)

    client = IPv4SSHClient()
    client.set_missing_host_key_policy(paramiko.client.AutoAddPolicy())
    client.load_system_host_keys()
    client.connect(node, username=user, password=password)
    # get a session
    s = client.get_transport().open_session()
    # set up the agent request handler to handle agent requests from the server
    paramiko.agent.AgentRequestHandler(s)
    # PF ring is disabled by default
    stdin, stdout, stderr = client.exec_command(
        "cd " + home + "Heartbeat/; mkdir resources"
    )

    client.close()


def copy_targets(node, user, home, targets_file):
    cmd = (
        "cd ~/Heartbeat; "
        "rsync -v --progress --stats -a -m  -e 'ssh -o StrictHostKeyChecking=no' "
        + targets_file
        + " "
        + user
        + "@"
        + node
        + ":~/Heartbeat/resources/"
    )

    process = Popen(cmd, stdout=PIPE, stderr=PIPE, shell=True)
    out, err = process.communicate()
    out = [line.decode("utf-8") for line in out.splitlines()]
    err = [line.decode("utf-8") for line in err.splitlines()]
    for line in out:
        print(node + ": " + line)
    for line in err:
        print(node + ": " + line)


def compile(node, user, home):
    client = IPv4SSHClient()
    client.set_missing_host_key_policy(paramiko.client.AutoAddPolicy())
    client.load_system_host_keys()
    client.connect(node, username=user, password=password)
    # get a session
    s = client.get_transport().open_session()
    # set up the agent request handler to handle agent requests from the server
    paramiko.agent.AgentRequestHandler(s)
    # PF ring is disabled by default
    cmd = "cd " + home + "Heartbeat/; mkdir build"
    cmd += (
        "; cd build; cmake .. -DCMAKE_BUILD_TYPE=RelWithDebInfo -DPROBER=1 -DCENTRAL=0"
    )
    if "vesper" in node:
        cmd += " -DCMAKE_CXX_COMPILER=g++-8"
    cmd += "; make -j2; cd .."
    stdin, stdout, stderr = client.exec_command(cmd)
    for line in stdout.readlines():
        line = line.encode("utf-8", "ignore").decode("utf-8")
        print(node + ": " + line)
    for line in stderr.readlines():
        line = line.encode("utf-8", "ignore").decode("utf-8")
        print(node + ": " + line)

    client.close()


def install_dependencies(node, user, home_dir, install_dependencies_script):
    cmd = (
        "rsync -v --progress --stats -a -m  -e 'ssh -o StrictHostKeyChecking=no' "
        + install_dependencies_script
        + " "
        + user
        + "@"
        + node
        + ":~/"
    )

    process = Popen(cmd, stdout=PIPE, stderr=PIPE, shell=True)
    out, err = process.communicate()
    out = [line.decode("utf-8") for line in out.splitlines()]
    err = [line.decode("utf-8") for line in err.splitlines()]
    for line in out:
        print(node + ": " + line)
    for line in err:
        print(node + ": " + line)

    client = IPv4SSHClient()
    client.set_missing_host_key_policy(paramiko.client.AutoAddPolicy())
    client.load_system_host_keys()
    client.connect(node, username=user, password=password)
    # get a session
    s = client.get_transport().open_session()
    # set up the agent request handler to handle agent requests from the server
    paramiko.agent.AgentRequestHandler(s)
    # PF ring is disabled by default
    stdin, stdout, stderr = client.exec_command(
        "chmod +x "
        + install_dependencies_script
        + "; "
        + "./"
        + install_dependencies_script
    )
    for line in stdout.readlines():
        line = line.encode("utf-8", "ignore").decode("utf-8")
        print(node + ": " + line)
    for line in stderr.readlines():
        line = line.encode("utf-8", "ignore").decode("utf-8")
        print(node + ": " + line)


def full_install(node, user, home_dir):
    targets_file = "/home/survey/Heartbeat-py/resources/traceroute_list.txt"
    install_dependencies_script = "install_dependencies.sh"
    # install_dependencies(node, user, home_dir, install_dependencies_script)
    clean(node, user, home_dir)
    rsync(node, user, home_dir)
    copy_targets(node, user, home_dir, targets_file)

    compile(node, user, home_dir)


if __name__ == "__main__":

    """
        This script installs dependencies  of Heartbeat (libtins, libcperm)
    """

    nodes = json.load(open(sys.argv[1]))

    threads = []
    for node in nodes["nodes"]:
        if node["server"] == "localhost":
            continue
        t = Thread(
            target=full_install, args=(node["server"], node["user"], node["home"])
        )
        t.start()
        threads.append(t)
    for t in threads:
        t.join()
