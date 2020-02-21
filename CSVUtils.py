import sys
from subprocess import Popen, PIPE


def insert_clickhouse(csv_file):
    insert_clickhouse_cmd = 'cat ' + csv_file +' | clickhouse-client -h132.227.123.200  --query="INSERT INTO heartbeat.versioned_probes FORMAT CSV"'
    insert_clickhouse_process = Popen(insert_clickhouse_cmd,
                                stdout=PIPE, stderr=PIPE, shell=True)

    stdout, stderr = insert_clickhouse_process.communicate()

    print(insert_clickhouse_cmd)

def remove_version(version, csv_file, ofile):
    remove_version_cmd = "time awk -F, '{$(NF+1)=-1 FS 1;}1' OFS=, " + csv_file + " > " + ofile
    Popen(remove_version_cmd,
          stdout=PIPE, stderr=PIPE, shell=True)


def add_version(version, csv_file, ofile):
    add_version_cmd = "time awk -F, '{$(NF+1)=1 FS "+ str(version)+ ";}1' OFS=, " + csv_file + " > " + ofile
    add_version_process = Popen(add_version_cmd,
          stdout=PIPE, stderr=PIPE, shell=True)

    add_version_process.communicate()

if __name__ == "__main__":

    # csv_file_prefix = sys.argv[1]
    # ofile_prefix = sys.argv[2]
    # version = sys.argv[3]
    # for i in reversed(range(0, 11)):
    #
    #     csv_file = csv_file_prefix + str(i)+".csv"
    #     ofile =  ofile_prefix + str(i) + ".csv"
    #     print("Processing " + csv_file + "...")
    #     add_version(version, csv_file, ofile)


    snapshots = ["snapshot-0617/",
                    "snapshot-0703/",
                    "snapshot-0704/",
                    "snapshot-0705/",
                    "snapshot-0706/",
                    "snapshot-0707/"]

    for snapshot in snapshots:
        print("Inserting " + snapshot + "...")
        for i in range(1, 3):
            print("Inserting round " + str(i))
            versioned_csv_file = "resources/" + snapshot + "versioned_replies_round_" + str(i) + ".csv"

            insert_clickhouse(versioned_csv_file)

