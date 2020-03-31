import copy
import getopt
import os
import json
import socket
import sys
import time

from Options import StochasticOptions
from Database.Table import create_datebase, create_table, clean_table, dump_table_names
from Processing.Steps import *
from threading import Thread


def rotate(l, n):
    return l[n:] + l[:n]


def stochastic_snapshot(snapshot, starting_round, n_round, table, options):
    """
    Entire routine
    :return:
    """
    start_time = time.time()
    for round in range(starting_round, n_round + 1):

        resources_dir = options.heartbeat_dir + "resources/"
        remote_resources_dir = options.remote_resources_dir
        # print(remote_resources_dir)
        # This file is a one line file necessary to compute the RTTs a posteriori.
        start_time_log_file_suffix = (
            options.remote_probe_hostname
            + "_start_time_log_file_"
            + str(snapshot)
            + "_"
            + str(round)
            + ".log"
        )
        pcap_file_suffix = (
            options.remote_probe_hostname
            + "_"
            + options.pcap_file_prefix
            + str(snapshot)
            + "_"
            + str(round)
            + ".pcap"
        )
        shuffled_csv_file_suffix = (
            options.remote_probe_hostname
            + "_"
            + options.probes_file_prefix
            + str(snapshot)
            + "_"
            + str(round)
            + "_shuffled.csv"
        )
        shuffled_next_round_csv_file_suffix = (
            options.remote_probe_hostname
            + "_"
            + options.probes_file_prefix
            + str(snapshot)
            + "_"
            + str(round + 1)
            + "_shuffled.csv"
        )

        # Those files are local to the central server
        replies_csv_file = (
            resources_dir
            + options.remote_probe_hostname
            + "_"
            + options.replies_file_prefix
            + str(snapshot)
            + "_"
            + str(round)
            + ".csv"
        )
        next_round_csv_file = (
            resources_dir
            + options.remote_probe_hostname
            + "_"
            + options.probes_file_prefix
            + str(snapshot)
            + "_"
            + str(round + 1)
            + ".csv"
        )

        # Probe
        is_stochastic = False
        if round == 1:
            is_stochastic = True
        probe_time = time.time()
        if options.is_remote_probe:
            pcap_file = remote_resources_dir + pcap_file_suffix
            shuffled_probes_csv_file = remote_resources_dir + shuffled_csv_file_suffix
            start_time_log_file = remote_resources_dir + start_time_log_file_suffix
        else:
            pcap_file = resources_dir + pcap_file_suffix
            shuffled_probes_csv_file = resources_dir + shuffled_csv_file_suffix
            start_time_log_file = resources_dir + start_time_log_file_suffix

        # if round > 1 or snapshot != 1: # Only for debug
        if round == 2:
            # Second round to detect per packet LB, send 2 probes instead of 1.
            options.packets_per_flow = 2
        else:
            options.packets_per_flow = 1

        if round > 1:
            # Reset the targets to None for the subsequent rounds.
            options.targets = None
        if not options.only_analyse:
            probe(
                pcap_file,
                shuffled_probes_csv_file,
                start_time_log_file,
                options,
                is_stochastic,
            )
            if options.is_remote_probe and round > 1:
                remote_shuffled_probes_csv_file = (
                    remote_resources_dir + shuffled_csv_file_suffix
                )
                remove_file_from_remote(remote_shuffled_probes_csv_file, options)
            end_probe_time = time.time()
            print(
                "probe round "
                + str(round)
                + " time: "
                + str(end_probe_time - probe_time)
                + " seconds."
            )

            if options.is_remote_probe:
                # Get the pcap back to the central place.
                scp_time = time.time()
                remote_pcap_file = remote_resources_dir + pcap_file_suffix
                local_pcap_file = resources_dir + pcap_file_suffix
                prober_to_server(remote_pcap_file, local_pcap_file, options)
                end_scp_time = time.time()
                print(
                    "scp "
                    + remote_pcap_file
                    + " time: "
                    + str(end_scp_time - scp_time)
                    + " seconds."
                )
                # Remove the pcap to not overload the memory of the node
                remove_file_from_remote(pcap_file, options)

                # Get the start log file to the central place.
                if options.proto == "tcp":
                    scp_time = time.time()
                    remote_start_time_log_file = (
                        remote_resources_dir + start_time_log_file_suffix
                    )
                    local_start_time_log_file = (
                        resources_dir + start_time_log_file_suffix
                    )
                    prober_to_server(
                        remote_start_time_log_file, local_start_time_log_file, options
                    )
                    end_scp_time = time.time()
                    print(
                        "scp "
                        + remote_start_time_log_file
                        + " time: "
                        + str(end_scp_time - scp_time)
                        + " seconds."
                    )

        # Parse pcap file
        start_pcap_to_csv_time = time.time()
        local_pcap_file = resources_dir + pcap_file_suffix
        # Need the start time log file to compute the RTT
        local_start_time_log_file = resources_dir + start_time_log_file_suffix
        pcap_to_csv(
            snapshot,
            round,
            local_pcap_file,
            replies_csv_file,
            local_start_time_log_file,
            options,
        )
        end_pcap_to_csv_time = time.time()
        print(
            "pcap_to_csv round "
            + str(round)
            + " time: "
            + str(end_pcap_to_csv_time - start_pcap_to_csv_time)
            + " seconds."
        )

        # Insert CSV into DB
        insert_csv_to_db(replies_csv_file, table, options)
        end_insert_csv_to_db_time = time.time()
        print(
            "insert_csv_to_db round "
            + str(round)
            + " time: "
            + str(end_insert_csv_to_db_time - end_pcap_to_csv_time)
            + " seconds."
        )

        if round == n_round:
            break
        # Compute the next rounds probes.
        start_next_round_csv_time = time.time()
        next_round_csv(snapshot, round, next_round_csv_file, table, options)
        end_next_round_csv_time = time.time()
        print(
            "next_round_csv round "
            + str(round)
            + " time: "
            + str(end_next_round_csv_time - start_next_round_csv_time)
            + " seconds."
        )

        if os.stat(next_round_csv_file).st_size == 0:
            """
            Stop d-miner if the snapshot is completed.
            """
            break

        # Shuffle the next rounds probes
        local_shuffled_next_round_csv_file = (
            resources_dir + shuffled_next_round_csv_file_suffix
        )
        shuffle_next_round_csv(
            next_round_csv_file, local_shuffled_next_round_csv_file, options
        )
        end_shuffle_next_round_csv_time = time.time()
        print(
            "shuffle_next_round_csv round "
            + str(round)
            + " time: "
            + str(end_shuffle_next_round_csv_time - end_next_round_csv_time)
            + " seconds."
        )

        if options.is_remote_probe and not options.only_analyse:
            # Send the next round to the prober
            scp_time = time.time()
            local_shuffled_next_round_csv_file = (
                resources_dir + shuffled_next_round_csv_file_suffix
            )
            remote_shuffled_next_round_csv_file = (
                remote_resources_dir + shuffled_next_round_csv_file_suffix
            )
            next_round_server_to_prober_csv(
                local_shuffled_next_round_csv_file,
                remote_shuffled_next_round_csv_file,
                options,
            )
            end_scp_time = time.time()
            print(
                "scp pcap round "
                + str(round)
                + " time: "
                + str(end_scp_time - scp_time)
                + " seconds."
            )

    end_time = time.time()
    print("Full snapshot took: " + str(end_time - start_time) + " seconds.")

    # Move the output with time in the right directory


def check_options(options):
    """
    TODO
    :param options:
    :return:
    """
    is_valid = True
    if options.proto == "":
        is_valid = False
        print("Please select a protocol for probing (udp, tcp, icmp)")
        exit(2)
    return is_valid


if __name__ == "__main__":

    usage = (
        "Usage : StochasticHeartbeat.py <options> \n"
        "options : \n"
        "--cpp-heartbeat-dir path to the directory of the binary heartbeat tool \n"
        "-r --probing-rate define the probing rate of the machine (100Kpps by default) \n"
        "--db-host IP address of the DB\n"
        "-t --table name of the database table to store and process the data\n"
        "--remote-probing boolean if the probing and the processing are made on a different machines \n"
        "--remote-probing-host IP address of the probing machine \n"
        "--remote-cpp-heartbeat-dir path to the remote directory of the binary heartbeat tool \n"
        "--n_destinations number of destinations per /24 \n"
        "--split-ipv4-space split the IPv4 space across different vantage points\n"
        "--rotation rotation number on the VP\n"
        "--proto protocol for probing (udp, tcp, icmp)\n"
        "--dport destination port for probing (default 33434)\n"
        "--min-ttl minimum ttl to probe\n"
        "--max-ttl maximum ttl to probe\n"
        "--targets targets file if not exhaustive probing\n"
        "--nodes nodes file\n"
    )

    try:
        opts, args = getopt.getopt(
            sys.argv[1:],
            "hr:t:p:",
            [
                "help",
                "cpp-heartbeat-dir=",
                "probing-rate=",
                "db-host=",
                "table=",
                "remote-probing",
                "remote-probing-host=",
                "remote-cpp-heartbeat-dir=",
                "n_destinations=",
                "split-ipv4-space,",
                "rotation=",
                "proto=",
                "dport=",
                "min-ttl=",
                "max-ttl=",
                "targets=",
                "nodes=",
                "only-analyse",
            ],
        )

    except getopt.GetoptError as e:
        print(e)
        print(usage)
        sys.exit(2)

    options = StochasticOptions()
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
    options.remote_probe_user = "root"

    for opt, arg in opts:

        if opt in ("-h", "--help"):
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
        elif opt in ("--n_destinations"):
            options.n_destinations_24 = arg
        elif opt in ("-p", "--proto"):
            options.proto = arg
        elif opt in ("--dport"):
            options.dport = arg
        elif opt in ("--targets"):
            options.targets = arg
        elif opt in ("--min-ttl"):
            options.min_ttl = arg
        elif opt in ("--max-ttl"):
            options.max_ttl = arg
        elif opt in ("--nodes"):
            options.nodes = arg
        elif opt in ("--only-analyse"):
            options.only_analyse = True
        print(opt + " set to:" + arg)

    check_options(options)

    options.stochastic_snapshot_number = 1
    nodes = json.load(open(options.nodes))["nodes"]

    database_name = options.table.split(".")[0]
    print("Create database " + database_name + " if not exists")
    create_datebase(options.db_host, database_name)

    n_snapshots = 1
    n_rounds = 10
    starting_round = 1
    rotation = 0
    localhost = "localhost"
    for snapshot in range(options.stochastic_snapshot_number, n_snapshots + 1):
        """
        This is a full stochastic Internet snapshot composed of rounds based on combination of Yaarp and MDA.
        A round is composed of the following steps:
        (1) Probe from a file, or exhaustive probing for round 1.
        (2) Pcap->CSV from replies.
        (3) Insert into the DB and sort by (src_ip, dst_ip)
        (4) Query the next round on a link based MDA and output the next probes in a CSV file.
        (5) Shuffle the next round CSV probe file.
        (6) Go to (1) and execute it with the shuffled next round probe file.

        The stopping condition is the number of rounds desired.
        """
        snapshot_nodes = rotate(nodes, rotation)
        ipv4_split = len(snapshot_nodes)

        threads = []
        db_tables = []
        time_file = "resources/d-miner.start_time_" + str(n_snapshots)
        with open(options.heartbeat_dir + time_file, "w") as f:
            f.write(str(time.time()))
            f.flush()
        for i in range(len(snapshot_nodes)):
            # inf_born = int((i * (2 ** 32 - 1) / ipv4_split))
            # sup_born = int(((i + 1) * (2 ** 32 - 1) / ipv4_split))

            node = snapshot_nodes[i]["server"]
            user = snapshot_nodes[i]["user"]
            home_dir = snapshot_nodes[i]["home"]
            remote_resources_dir = snapshot_nodes[i]["resources"]

            # Setup the correct options for each node:
            options_node = copy.deepcopy(options)
            # options.probing_rate = 100000 / len(nodes)
            options_node.inf_born = 0
            options_node.sup_born = 2 ** 32 - 1
            table_node = node.replace(".", "_")
            table_node = table_node.replace("-", "_")
            options_node.db_table += "_" + table_node
            if node == localhost:

                options_node.is_remote_probe = False
                options_node.heartbeat_binary = (
                    options.heartbeat_dir + "build/Heartbeat"
                )
                options_node.home_dir = "/root/"
                options_node.remote_probe_hostname = localhost
                options_node.remote_probe_ip = socket.gethostbyname(
                    socket.gethostname()
                )
                options_node.db_table += "_" + str(int(time.time()))
                # options_node.probing_rate = 100
            else:
                options_node.is_remote_probe = True
                options_node.remote_probe_hostname = node
                options_node.remote_probe_ip = socket.gethostbyname(node)
                options_node.remote_probe_user = user
                options_node.remote_resources_dir = remote_resources_dir
                # options_node.probing_rate = 100
                # Central server home dir
                options_node.home_dir = "/root/"
                options_node.probe_dir = home_dir + "Heartbeat/"
                options_node.heartbeat_binary = (
                    options_node.probe_dir + "build/Heartbeat"
                )
                options_node.db_table += "_" + str(int(time.time()))

            create_table(options_node.db_host, options_node.db_table)
            clean_table(options_node.db_host, options_node.db_table)
            db_tables.append(options_node.db_table)

            # Start thread
            t = Thread(
                target=stochastic_snapshot,
                args=(
                    snapshot,
                    starting_round,
                    n_rounds,
                    options_node.db_table,
                    options_node,
                ),
            )
            t.start()
            threads.append(t)
            time.sleep(20)
        dump_table_names(db_tables, options.heartbeat_dir + "resources/")
        for t in threads:
            t.join()

        time_file = "resources/d-miner.end_time_" + str(n_snapshots)
        with open(options.heartbeat_dir + time_file, "w") as f:
            f.write(str(time.time()))
            f.flush()
        # stochastic_snapshot(snapshot_number, starting_round, n_rounds, options.db_table, options)  # noqa
