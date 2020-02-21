from subprocess import Popen, PIPE
import paramiko
import time
import sys
import getopt
from getpass import getpass
from Options import Options
from Processing.Steps import *

def stochastic_snapshot(snapshot_number, starting_round, n_round, table, probing_rate, options):
    '''
    Entire routine
    :return:
    '''
    start_time = time.time()
    for round in range(starting_round, n_round + 1):
        pcap_file = options.probe_dir + "resources/" + options.pcap_file_prefix + str(snapshot_number) + "_" + str(round) + ".pcap"
        shuffled_probes_csv_file = options.heartbeat_dir + "resources/" + options.probes_file_prefix + str(snapshot_number) + "_" + str(round) + "_shuffled.csv"
        replies_csv_file = options.heartbeat_dir + "resources/" + options.replies_file_prefix + str(snapshot_number) + "_" + str(round) + ".csv"
        next_round_csv_file = options.heartbeat_dir + "resources/" + options.probes_file_prefix + str(snapshot_number) + "_" + str(round + 1) + ".csv"
        shuffled_next_round_csv_file = options.heartbeat_dir + "resources/" + options.probes_file_prefix + str(snapshot_number) + "_" + str(round + 1) + "_shuffled.csv"

        # Probe
        is_stochastic = False
        if round == 1:
            is_stochastic = True
        probe_time = time.time()
        probe(pcap_file, shuffled_probes_csv_file, probing_rate, options, is_stochastic)
        end_probe_time = time.time()
        print("probe round " + str(round) + " time: " + str(end_probe_time-probe_time) + " seconds.")

        # Parse pcap file
        pcap_to_csv(snapshot_number, round, pcap_file, replies_csv_file, options)
        end_pcap_to_csv_time = time.time()
        print("pcap_to_csv round " + str(round) + " time: " + str(end_pcap_to_csv_time - end_probe_time) + " seconds.")

        # Insert CSV into DB
        insert_csv_to_db(replies_csv_file, table, options)
        end_insert_csv_to_db_time = time.time()
        print("insert_csv_to_db round " + str(round) + " time: " + str(end_insert_csv_to_db_time - end_pcap_to_csv_time) + " seconds.")

        if round == n_round:
            break
        # Compute the next rounds probes.
        next_round_csv(round, next_round_csv_file, table, options)
        end_next_round_csv_time = time.time()
        print("next_round_csv round " + str(round) + " time: " + str(end_next_round_csv_time - end_insert_csv_to_db_time) + " seconds.")

        # Shuffle the next rounds probes
        shuffle_next_round_csv(next_round_csv_file, shuffled_next_round_csv_file, options)
        end_shuffle_next_round_csv_time = time.time()
        print("shuffle_next_round_csv round " + str(round) + " time: " + str(end_shuffle_next_round_csv_time - end_next_round_csv_time) + " seconds.")

    end_time = time.time()
    print("Full snapshot took: " + str(end_time-start_time) + " seconds.")

    # Move the output with time in the right directory


if __name__ == "__main__":

    usage = 'Usage : StochasticHeartbeat.py <options> \n' \
            'options : \n' \
            '--cpp-heartbeat-dir path to the directory of the binary heartbeat tool \n' \
            '-r --probing-rate define the probing rate of the machine (100Kpps by default) \n' \
            '--db-host IP address of the DB\n' \
            '-t --table name of the database table to store and process the data\n' \
            '--remote-probing boolean if the probing and the processing are made on a different machines \n' \
            '--remote-probing-host IP address of the probing machine \n'\
            '--remote-cpp-heartbeat-dir path to the remote directory of the binary heartbeat tool \n'

    try:
        opts, args = getopt.getopt(sys.argv[1:], "hr:t:", ["help",
                                                           "cpp-heartbeat-dir=",
                                                           "probing-rate=",
                                                           "db-host=",
                                                           "table=",
                                                           "remote-probing",
                                                           "remote-probing-host=",
                                                           "remote-cpp-heartbeat-dir="
                                                        ])

    except getopt.GetoptError as e:
        print(e)
        print(usage)
        sys.exit(2)

    n_rounds = 1
    starting_round = 1

    options = Options()

    options.probes_file_prefix = "probes_round_"
    options.replies_file_prefix = "replies_round_"
    options.pcap_file_prefix = "heartbeat-pfring-round-"
    # options.heartbeat_dir = "/work/kvermeulen/Heartbeat/"
    options.heartbeat_dir = "/root/Heartbeat/"
    options.probe_dir = "/slush/kvermeulen/Heartbeat/"
    if options.is_remote_probe:
        options.heartbeat_binary = options.probe_dir + "build/Heartbeat"
    else:
        options.heartbeat_binary = options.heartbeat_dir + "build/Heartbeat"
    options.process_binary = options.heartbeat_dir + "build/Reader"
    options.probing_rate = 100000
    options.db_host = "localhost"
    # options.db_host = "132.227.123.200"
    options.is_remote_probe = False
    options.remote_probe_hostname = "vesper.tancad.net"
    if options.is_remote_probe:
        options.remote_probe_host_sudo_password = getpass()

    options.stochastic_snapshot_number = 5

    for opt, arg in opts:

        if opt in ('-h', "--help"):
            print(usage)
            exit(0)

        elif opt in ("cpp-heartbeat-dir"):
            options.heartbeat_dir = arg
        elif opt in ("-r", "--probing-rate"):
            options.probing_rate = int(arg)
        elif opt in ("--db-host"):
            options.db_host = arg
        elif opt in ("-t", "--table"):
            options.db_table = arg
        elif opt in ("--remote-probing"):
            options.is_remote_probe = True
        elif opt in ("--remote-probing-host"):
            options.remote_probe_hostname = arg
        elif opt in ("--remote-cpp-heartbeat-dir"):
            options.probe_dir = arg

        print(opt + " set to:" + arg)

    probing_rates = [10000 for i in range(1, 25)]

    for i  in range(len(probing_rates)):
        '''
        This is a full stochastic Internet snapshot composed of rounds based on combination of Yaarp and MDA.
        A round is composed of the following steps:
        (1) Probe from a file, or exhaustive probing for round 1.
        (2) Pcap->CSV from replies.
        (3) Insert into the DB and sort by (src_ip, dst_ip)
        (4) Query the next round on a link based MDA and output the next probes in a CSV file.
        (5) Shuffle the next round CSV probe file.
        (6) Go to (1) and execute it with the shuffled next round probe file.

        The stopping condition is the number of rounds desired.
        '''
        stochastic_snapshot(i, starting_round, n_rounds, options.db_table, probing_rates[i], options)







