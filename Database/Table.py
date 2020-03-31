from subprocess import Popen, PIPE


def node_to_table(node):
    table = node.replace("-", "_")
    table = table.replace(".", "_")
    table_prefix = "replies_"
    return table_prefix + table


def create_datebase(db_host, database_name):
    cmd = (
        "clickhouse-client --host="
        + db_host
        + " --query='CREATE DATABASE IF NOT EXISTS"
        + database_name
        + "'"
    )

    print("Executing " + cmd)
    p = Popen(cmd, stdout=PIPE, stderr=PIPE, shell=True)
    out, err = p.communicate()

    out = [line.decode("utf-8") for line in out.splitlines()]
    err = [line.decode("utf-8") for line in err.splitlines()]
    for line in out:
        print(line)
    for line in err:
        print(line)


def create_table(db_host, table):

    drop_cmd = (
        "clickhouse-client --host=" + db_host + " --query='DROP TABLE " + table + "'"
    )

    print("Executing " + drop_cmd)
    p = Popen(drop_cmd, stdout=PIPE, stderr=PIPE, shell=True)
    out, err = p.communicate()

    out = [line.decode("utf-8") for line in out.splitlines()]
    err = [line.decode("utf-8") for line in err.splitlines()]
    for line in out:
        print(line)
    for line in err:
        print(line)

    cmd = (
        "clickhouse-client --host="
        + db_host
        + " --query='CREATE TABLE "
        + table
        + "(src_ip UInt32, dst_prefix UInt32, dst_ip UInt32, reply_ip UInt32, "
        + "proto UInt8, src_port UInt16, dst_port UInt16, ttl UInt8, type UInt8, "
        + "code UInt8, rtt Float64, reply_ttl UInt8, reply_size UInt16, round UInt32, "
        + "snapshot UInt16) ENGINE=MergeTree() "
        + "ORDER BY (src_ip, dst_prefix, dst_ip, ttl, src_port, dst_port, snapshot)"
        + " '"
    )

    print("Executing " + cmd)
    p = Popen(cmd, stdout=PIPE, stderr=PIPE, shell=True)
    out, err = p.communicate()

    out = [line.decode("utf-8") for line in out.splitlines()]
    err = [line.decode("utf-8") for line in err.splitlines()]
    for line in out:
        print(line)
    for line in err:
        print(line)


def clean_table(db_host, table):
    cmd = (
        "clickhouse-client --host="
        + db_host
        + " --query='ALTER TABLE "
        + table
        + " DELETE WHERE 1=1"
        + " '"
    )

    print("Executing " + cmd)
    p = Popen(cmd, stdout=PIPE, stderr=PIPE, shell=True)
    out, err = p.communicate()

    out = [line.decode("utf-8") for line in out.splitlines()]
    err = [line.decode("utf-8") for line in err.splitlines()]
    for line in out:
        print(line)
    for line in err:
        print(line)


def dump_table_names(tables, resources_dir):
    with open(resources_dir + "d_miner_tables", "w") as f:
        for table in tables:
            f.write(table + "\n")
