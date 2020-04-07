import json

from pprint import pprint
from subprocess import Popen, PIPE


def kube_cmd(cmd, verbose=True):
    print("Executing " + cmd)
    p = Popen(cmd, stdout=PIPE, stderr=PIPE, shell=True)
    out, err = p.communicate()

    out = [line.decode("utf-8") for line in out.splitlines()]
    err = [line.decode("utf-8") for line in err.splitlines()]
    if err:
        for line in err:
            pprint(line)
    else:
        if verbose:
            pprint(out)
        return out


def create_pods(kubernetes):
    kube_cmd(
        f'kubectl apply -f {kubernetes["deployer"]}'
        f' --kubeconfig {kubernetes["kubeconfig"]}'
        f' --namespace {kubernetes["namespace"]}'
    )


def get_pods(kubernetes):
    res = kube_cmd(
        f"kubectl get pods"
        f' --kubeconfig {kubernetes["kubeconfig"]}'
        f' --namespace {kubernetes["namespace"]} -o json',
        verbose=False,
    )

    if res:
        return [
            {
                "type": "pod",
                "server": i["metadata"]["name"],
                "user": None,
                "home": "/root/",
                "resources": "/srv/",
                "host_ip": i["status"]["hostIP"],
            }
            for i in json.loads("\n".join(res)).get("items", [])
            if i["status"]["phase"] == "Running"
        ]


def delete_pods(kubernetes):
    kube_cmd(
        f'kubectl delete -f {kubernetes["deployer"]}'
        f' --kubeconfig {kubernetes["kubeconfig"]}'
        f' --namespace {kubernetes["namespace"]}'
    )


def kube_target_server_to_prober(
    local_target_file, remote_target_file, node, kubernetes
):
    kube_cmd(
        f"kubectl cp {local_target_file} {node['server']}:{remote_target_file}"
        f' --kubeconfig {kubernetes["kubeconfig"]}'
        f' --namespace {kubernetes["namespace"]}'
    )


def test_ls(file, node, kubernetes):
    kube_cmd(
        f"kubectl exec -i {node['server']}"
        f' --kubeconfig {kubernetes["kubeconfig"]}'
        f' --namespace {kubernetes["namespace"]}'
        f" -- bash -c 'ls -la {file}'"
    )


def kube_next_round_server_to_prober_csv(local_csv_file, remote_csv_file, options):
    kube_cmd(
        f"kubectl cp {local_csv_file} {options.remote_probe_hostname}:{remote_csv_file}"
        f" --kubeconfig {options.remote_kubernetes_kubeconfig}"
        f" --namespace {options.remote_kubernetes_namespace}"
    )


def kube_remove_file_from_remote(file_to_rm, options):
    kube_cmd(
        f"kubectl exec -i {options.remote_probe_hostname}"
        f" --kubeconfig {options.remote_kubernetes_kubeconfig}"
        f" --namespace {options.remote_kubernetes_namespace}"
        f" -- bash -c 'rm {file_to_rm}'"
    )


def kube_prober_to_server(remote_file, local_file, options):
    kube_cmd(
        f"kubectl cp {options.remote_probe_hostname}:{remote_file} {local_file}"
        f" --kubeconfig {options.remote_kubernetes_kubeconfig}"
        f" --namespace {options.remote_kubernetes_namespace}"
    )


def kube_probe(pcap_file, csv_file, start_time_log_file, options, is_stochastic):
    ofile = pcap_file
    ifile = csv_file
    cmd = (
        options.heartbeat_binary
        + " -o "
        + ofile
        + " -r "
        + str(options.probing_rate)
        + " -d "
        + str(options.n_destinations_24)
        + " -i "
        + str(options.inf_born)
        + " -s "
        + str(options.sup_born)
        + " -p "
        + str(options.proto)
        + " --dport="
        + str(options.dport)
        + " --min-ttl="
        + str(options.min_ttl)
        + " --max-ttl="
        + str(options.max_ttl)
        + " --record-timestamp "
        + " --start-time-log-file="
        + start_time_log_file
    )

    if not is_stochastic:
        # First round, do a 6 Flow IDs Yaarp
        cmd += " -F -f " + ifile

    if options.targets is not None:
        cmd += " -T -t " + options.targets

    kube_cmd(
        f"kubectl exec -i {options.remote_probe_hostname}"
        f" --kubeconfig {options.remote_kubernetes_kubeconfig}"
        f" --namespace {options.remote_kubernetes_namespace}"
        f" -- bash -c '{cmd}'"
    )
