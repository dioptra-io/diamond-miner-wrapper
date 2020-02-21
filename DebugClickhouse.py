from threading import Thread
from subprocess import Popen, PIPE
from Globals import nodes
def insert_db(node):

    for i in range(1, 100):
        csv_file =  "/root/Heartbeat/resources/" + node + "_replies_round_1_"+ str(i) + ".csv"
        insert_csv_to_db_cmd = "cat " + csv_file + " | clickhouse-client --host=132.227.123.200 --query='INSERT INTO heartbeat.multi_versioned_probes FORMAT CSV'"

        print("Executing " + insert_csv_to_db_cmd)
        insert_csv_to_db_process = Popen(insert_csv_to_db_cmd,
                                         stdout=PIPE, stderr=PIPE, shell=True)
        out, err = insert_csv_to_db_process.communicate()
        out = [line.decode("utf-8") for line in out.splitlines()]
        err = [line.decode("utf-8") for line in err.splitlines()]
        for line in out:
            print (line)
        for line in err:
            print(line)

if __name__ == "__main__":

    '''
        This script installs dependencies  of Heartbeat (libtins, libcperm)
    '''

    threads = []
    for node, user, home_dir in nodes:
        if node == "localhost":
            continue
        t = Thread(target=insert_db,
                   args=(node,))
        t.start()
        threads.append(t)
    for t in threads:
        t.join()