from subprocess import Popen, PIPE
import paramiko
import os
import ipaddress


def next_round_server_to_prober_csv(local_csv_file, remote_csv_file, options):
    client = paramiko.SSHClient()
    client.load_system_host_keys()
    client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    print("Connecting to %s \n with username=%s... \n" % (options.remote_probe_hostname, options.remote_probe_user))
    client.connect(options.remote_probe_hostname, username=options.remote_probe_user)
    t = client.get_transport()
    sftp = paramiko.SFTPClient.from_transport(t)
    print("Copying file: %s to path: %s" % (local_csv_file, remote_csv_file))
    sftp.put(local_csv_file, remote_csv_file)
    sftp.close()
    t.close()
    client.close()

def shuffle_next_round_csv(csv_file, shuffled_csv_file, options):
    shuffle_next_round_csv_cmd = "export MEMORY=40; export TMPDIR=" + options.home_dir + "Heartbeat/resources/; "+ options.home_dir + "terashuf/terashuf < " + csv_file + " > " + shuffled_csv_file
    print("Executing " + shuffle_next_round_csv_cmd)
    shuffle_next_round_csv_process = Popen(shuffle_next_round_csv_cmd,
                                   stdout=PIPE, stderr=PIPE, shell=True)
    out, err = shuffle_next_round_csv_process.communicate()
def next_round_csv(snapshot, round, csv_file, table, options):
    next_round_csv_cmd = options.process_binary + \
                         " -g  -o " + csv_file + " -R " + str(round) + " -s " + str(snapshot) +  \
                         " -t" + table + " --db-host=" + options.db_host + " -v " + str(int(ipaddress.IPv4Address(options.remote_probe_ip))) + \
                         " --dport=" + str(options.dport) + \
                         " --skip-prefixes=" + options.heartbeat_dir + "resources/" + options.remote_probe_hostname + "_skip_prefix"
    print("Executing " + next_round_csv_cmd)
    next_round_csv_process = Popen(next_round_csv_cmd,
                                stdout=PIPE, stderr=PIPE, shell=True)
    out, err = next_round_csv_process.communicate()
    out = [line.decode("utf-8") for line in out.splitlines()]
    err = [line.decode("utf-8") for line in err.splitlines()]
    # for line in out:
    #     print (line)
    for line in err:
        print(line)

def insert_csv_to_db(csv_file, table, options):
    insert_csv_to_db_cmd =  "cat " + csv_file + " | clickhouse-client --max_insert_block_size=100000 --host=" + options.db_host + " --query='INSERT INTO "+ table + " FORMAT CSV'"

    print("Executing " + insert_csv_to_db_cmd)
    insert_csv_to_db_process = Popen(insert_csv_to_db_cmd,
                                stdout=PIPE, stderr=PIPE, shell=True)
    out, err = insert_csv_to_db_process.communicate()

    out = [line.decode("utf-8") for line in out.splitlines()]
    err = [line.decode("utf-8") for line in err.splitlines()]
    for line in out:
        print(line)
    for line in err:
        print(line)

def pcap_to_csv(snapshot, round, pcap_file, csv_file, start_time_log_file, options):
    pcap_to_csv_cmd = options.process_binary + \
                      " -r " +  \
                      " -i " + pcap_file +  \
                      " -o " + csv_file + \
                      " -R " + str(round) + \
                      " -s " + str(snapshot) + \
                      " --dport=" + str(options.dport) + \
                      " --compute-rtt " + \
                      " --start-time-log-file=" + start_time_log_file
    print("Executing " + pcap_to_csv_cmd)
    pcap_to_csv_process = Popen(pcap_to_csv_cmd,
                         stdout=PIPE, stderr=PIPE, shell=True)
    out, err = pcap_to_csv_process.communicate()

def remove_file_from_remote(file, options):
    client = paramiko.SSHClient()
    client.load_system_host_keys()
    client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    print("Connecting to %s \n with username=%s... \n" % (options.remote_probe_hostname, options.remote_probe_user))
    client.connect(options.remote_probe_hostname, username=options.remote_probe_user)
    t = client.get_transport()
    sftp = paramiko.SFTPClient.from_transport(t)
    print("Removing file: %s " % (
    file))
    sftp.remove(file)
    sftp.close()
    t.close()
    client.close()

def prober_to_server(remote_file, local_file, options):
    client = paramiko.SSHClient()
    client.load_system_host_keys()
    client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    print("Connecting to %s \n with username=%s... \n" % (options.remote_probe_hostname, options.remote_probe_user))
    client.connect(options.remote_probe_hostname, username=options.remote_probe_user)
    t = client.get_transport()
    sftp = paramiko.SFTPClient.from_transport(t)
    print("Copying file: %s to path: %s" % (remote_file, local_file))

    sftp.get(remote_file, local_file)
    sftp.close()
    t.close()
    client.close()



def probe(pcap_file, csv_file, start_time_log_file, options, is_stochastic):
    '''

    :param round:
    :param pcap_file:
    :param csv_file:
    :return:
    '''

    ofile = pcap_file
    ifile = csv_file
    probe_cmd = "sudo -S " + options.heartbeat_binary + \
                " -o " + ofile + \
                " -r " + str(options.probing_rate) + \
                " -d " + str(options.n_destinations_24) + \
                " -i " + str(options.inf_born) + \
                " -s " + str(options.sup_born) + \
                " -p " + str(options.proto) + \
                " --dport=" + str(options.dport) + \
                " --record-timestamp " + \
                " --start-time-log-file=" + start_time_log_file

    if not is_stochastic:
        # First round, do a 6 Flow IDs Yaarp
        probe_cmd += " -F -f " + ifile

    if options.is_remote_probe:
        if options.targets is not None:
            probe_cmd += " -T -t " + options.targets
        '''
        Probing is done on another machine. So probe and then copy the pcap file on the processing machine.
        '''
        client = paramiko.client.SSHClient()
        client.set_missing_host_key_policy(paramiko.client.AutoAddPolicy())
        client.load_system_host_keys()
        print("Connecting to %s \n with username=%s... \n" % (options.remote_probe_hostname, options.remote_probe_user))
        client.connect(options.remote_probe_hostname, username=options.remote_probe_user)
        # get a session
        s = client.get_transport().open_session()
        # set up the agent request handler to handle agent requests from the server
        paramiko.agent.AgentRequestHandler(s)
        print("Executing " + probe_cmd)
        stdin, stdout, stderr = client.exec_command("echo "+ options.remote_probe_host_sudo_password + " | " +
                                                    probe_cmd)
        for line in stdout.readlines():
            print (line)
        for line in stderr.readlines():
            print (line)
        client.close()
    else:
        if options.targets is not None:
            probe_cmd += " -T -t " + options.targets
        print("Executing " + probe_cmd)
        probe_process = Popen(probe_cmd,
                             stdout=PIPE, stderr=PIPE, shell=True)
        probe_process.communicate()




