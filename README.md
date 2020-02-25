# Diamond-Miner

Diamond-Miner is a Internet topology measurement software that provides statistical guarantees to discover load balanced paths at Internet Scale.

This work has been published to USENIX NSDI 2020.

Link to the paper: https://www.usenix.org/system/files/nsdi20-paper-vermeulen.pdf

## Getting Started

These instructions will get you a copy of the project up and running on your local server.

### Prerequisites

Diamond-Miner has two main components: the core of diamond-miner, containing all of the routines of the algorithm (probing, computation of the next round of probes, database driver) written in C++
and the wrapper which provides a friendly python API to launch D-Miner on multiple vantage points.

You will need to clone both of the projects:
```
git clone https://github.com/dioptra-io/diamond-miner-cpp.git
```

```
git clone https://github.com/dioptra-io/diamond-miner-wrapper.git
```

You also need to install several libraries on which diamond-miner relies.

Please install boost program_options
libcperm (https://github.com/lancealt/libcperm)
libtins (http://libtins.github.io)

If you want to be able to run it at > 100K packets per second, you will have to install PF_RING (https://www.ntop.org/guides/pf_ring/)

You finally need to install and start a clickhouse database (https://clickhouse.tech/docs/en/getting_started/)

### Install the core routines
You first need to configure and compile the core-routines of Diamond-Miner.
Diamond-Miner has two main core routines: the prober and the central, where the database computation is made.
```
cd /where/you/have/cloned/diamond-miner-cpp
mkdir build
cd build
cmake -DPROBER=1 -DCENTRAL=1 ..
```

If you want to activate PF_RING, you put the PF_RING option in the cmake command:
```
cmake -DPROBER=1 -DCENTRAL=1 -DPF_RING=1 ..
```

If you only want the prober component, because you install the database in a single server, remove the CENTRAL option:
```
cmake -DPROBER=1 -DPF_RING ..
```

Once it is configured, you can run:
```
make -j8
```

### Install the python wrapper
No further action are required to install the wrapper.

## Running
Once you have installed the core routines and the database, you can run the following command to run
Diamond-Miner from the python wrapper directory.

```
python3 StochasticHeartbeat.py --cpp-heartbeat-dir=/where/core/routines/are/installed --db-host=IP_address_where_the_database_is_installed --table=name_of_the_database_table_to_save_the_replies --remote-probing (if multiple vantage points version) -r 100000 (probing rate) --proto=(udp,tcp)
```

The different options are described by running:
```
python3 StochasticHeartbeat.py --help
```

## Running on multiple vantage points
If you want to run it from multiple vantage points from a centralized server,
you just have to modify the file Globals.py and put the vantage points informations.

For example, if you uncomment the line:
```
("ple1.cesnet.cz", "root", "/root/", "/where/to/store/pcap/")
```

Diamond-Miner will be run from ple1.cesnet.cz, using the user root, the home directory being /root/ and the directory to store the pcap files is /where/to/store/pcap/

Notice that you can install the core routines on the vantage points of the Globals.py file by running:
```
python3 Install.py
```

## Deploying in a docker container.
Coming soon.
<!-- You can also deploy Diamond-Miner in a docker container. -->

<!-- Be sure that the database is running. -->
<!-- In the python wrapper installation directory, run: -->
<!-- ``` -->
<!-- docker build -t "d-miner" . -->
<!-- ``` -->
<!-- Then you can just run it: -->
<!-- ``` -->

<!-- ``` -->

<!-- To run it: -->
<!-- ``` -->
<!-- docker run -d name/of/your/docker/image -->
<!-- ``` -->

<!--- ## Contributing

Please read [CONTRIBUTING.md](https://gist.github.com/PurpleBooth/b24679402957c63ec426) for details on our code of conduct, and the process for submitting pull requests to us.

## Versioning

We use [SemVer](http://semver.org/) for versioning. For the versions available, see the [tags on this repository](https://github.com/your/project/tags). 

## Authors

* **Billie Thompson** - *Initial work* - [PurpleBooth](https://github.com/PurpleBooth)

See also the list of [contributors](https://github.com/your/project/contributors) who participated in this project.

## License

This project is licensed under the MIT License - see the [LICENSE.md](LICENSE.md) file for details

## Acknowledgments

* Hat tip to anyone who's code was used
* Inspiration
* etc
-->
