import os


class Options:
    def __init__(self):
        self.probes_file_prefix = "probes_round_"
        self.replies_file_prefix = "replies_round_"
        self.pcap_file_prefix = "heartbeat-pfring-round-"
        # self.heartbeat_dir = "/slush/kvermeulen/Heartbeat/"
        self.home_dir = "/root/"
        self.heartbeat_dir = self.home_dir + "Heartbeat/"
        self.probe_dir = ""
        self.heartbeat_binary = self.heartbeat_dir + "build/Heartbeat"
        self.process_binary = self.heartbeat_dir + "build/Reader"
        self.probing_rate = 100000
        self.buffer_sniffer_size = 2000000
        # self.db_host = "localhost"
        self.db_host = "132.227.123.200"
        self.db_table = ""
        self.is_remote_probe = False
        self.remote_resources_dir = ""
        self.remote_probe_hostname = "vesper.tancad.net"
        self.remote_probe_ip = ""
        self.remote_probe_user = "root"
        self.remote_probe_host_sudo_password = ""
        self.inf_born = 0
        self.sup_born = 0
        self.proto = None
        self.dport = 33434
        self.min_ttl = 3
        self.max_ttl = 30
        self.targets = None
        self.nodes = os.path.dirname(__file__) + "/nodes/localhost.json"
        self.only_analyse = False

        self.remote_probe_type = "vm"
        self.remote_kubernetes_kubeconfig = None
        self.remote_kubernetes_namespace = None


class StochasticOptions(Options):
    def __init__(self):
        super().__init__()
        self.stochastic_snapshot_number = 5
        self.n_destinations_24 = 6
        self.packets_per_flow = 1
        self.is_split_ipv4_space = True


class DynamicsOptions(Options):
    def __init__(self):
        super().__init__()
        self.previous_window = 5
