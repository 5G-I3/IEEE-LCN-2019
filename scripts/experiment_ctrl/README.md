# Scripts to construct network and conduct experiment

## Overview

The scripts in this directory serve the experiment setup and conduction.

`construct_network.py` constructs a network of up to 50 nodes (may be less due
to bookings within the selected site).

`run_experiment.py` conducts a single experiment run for a single configuration.

`dispatch_runs.sh` starts a number of runs with different configurations of
`run_experiment.py`.

Finally, `setup_exp.sh` ensures the environment for `dispatch_runs.sh` is run in
the background in one TMUX session (called `lcn19`) with insurance that an SSH
authentication agent was started and configured to communicate with the IoT-LAB
frontend server.

## Requirements
The scripts assume they are run with Python 3.

The following python packages are required (version numbers indicate tested
versions):

- `iotlab_controller` (see https://github.com/miri64/iotlab_controller)
- `libtmux` v0.8
- `matplotlib` v3.1
- `networkx` v2.3
- `pexpect` v4.7
- `scipy` v1.3

The required packages are listed in `requirements.txt` and can be installed
using

```sh
pip3 install -r requirements.txt
```

You will also require a version of the `ssh` command (e.g. `openssh-client`) to
interact with the IoT-LAB nodes.

`tmux` is required to multiplex the terminal in the background.

You must also configure your IoT-LAB credentials using `iotlab-auth` which is
provided by the `iotlabcli` python package (which is automatically installed
with `iotlab_controller`). See

```sh
iotlab-auth -h
```

for further instructions.

## Usage

### `construct_network.py`

This script constructs a sink-oriented network on the [M3 nodes] in the [IoT-LAB
testbed] using predefined values. See

```sh
./construct_network.py -h
```

for further information. The resulting `edgelist.gz` file will be stored in
`./../../results`.

**Attention:** Depending on the size, the generation of the edge-list file may
take a while.

We provided the edge-list file for the nodes we used for our experiments in
`./../../results` (at the moment of this writing some of the nodes in that
network are sadly disabled by the IoT-LAB admins).

#### Environment variables

- `DATA_PATH`: (default: `./../../results`) Path to store the edge list file in

### `run_experiment.py`

This script conducts a single experiment with a given configuration on a
selection of [M3 nodes] in the [IoT-LAB testbed]. An experiments configuration
is defined by the tuple

```py
(mode, data_len, count, delay)
```

`mode` is provided as a positional argument and can be either `reass` or `fwd`,
with `reass` being the default. `data_len`, `count`, and `delay` are provided
with the `-l`, `-c`, and `-W` arguments respectively.

You can provide the edge-list of a network constructed with the
[`construct_network.py` script](#construct_networkpy) with `-f` argument.
Alternatively, a network is constructed via that script if the `-f` argument is
not provided. In any case, the sink of the network *must* be provided as a
positional argument before `mode`

When run, the script compiles the applications provided in `./../../apps` with
`MODE` configured to `mode`, starts a new experiment (or resets or reflashes it,
depending if `-i` or `-r` are provided as arguments) at the IoT-LAB testbed
based on the given network. The site of the experiment can be configured using
the `-S` argument (the default is at Lille). The duration of the IoT-LAB
experiment can be set using the `-d` argument in minutes. By setting this to a
high value and using `-i` and `-r`, multiple runs of the experiment can be
conducted within the same IoT-LAB experiment. The name of the experiment will
always be `lcn19_n<network name>_c<channel>`.

The ID of the IoT-LAB experiment will be stored in the format
`-i <exp id>` in the file `./running_experiment.txt`

Once everything is set up, the script will conduct the run in a TMUX session.
The target of that session can be set using the `-t` argument and is expected to
be in the usual TMUX target syntax (so `<session>:<window>.<pane>`). The default
is a session with the name of the IoT-LAB experiment (see previous paragraph)
with an unnamed window and pane.

The logs of the run will be stored in `./../../results` under the name
`lcn19_n<network name>_c<channel>__m<mode>_r<data_len>Bx<count>x<delay>ms__<timestamp>.log`

If you want to sniff the IEEE 802.15.4 traffic during the experiment, use the
`-s` argument. The resulting PCAP file will be stored in `./../../../results/`
under the name
`lcn19_n<network name>_c<channel>__m<mode>_r<data_len>Bx<count>x<delay>ms__<timestamp>.pcap`

To change the channel for the experiment use the `--channel` argument. When used
with the `-i` argument, you have to use the `-r` argument at least for the first
run after you changed the channel.

See

```sh
./run_experiment.py -h
```

for further information.

#### Environment variables

- `DATA_PATH`: (default: `./../../results`) Path to store the edge list file in
- `GLOBAL_PREFIX` (default: `2001:db8:0:1:`) Global IPv6 address prefix for the
  experiment network (has to be of length 64 bits)
- `RUNNING_EXPERIMENT_FILE`: (default: `./running_experiment.txt`) Name of the
  file to store the IoT-LAB experiment ID to
- `SSH_AUTH_SOCK` and `SSH_AGENT_PID`: environment variables to configure the
  SSH authentication agent for communication with the IoT-LAB gateway

Additionally, all environment variables accepted by the RIOT applications can
also be used to configure the applications.

### `dispatch_runs.sh`

This scripts calls [`run_experiment.py`](#run_experimentpy) iteratively until
3 runs of every configuration are done. The script takes no arguments, but is
configurable via environment variables. The defaults are in line with the
configurations in the paper.

When starting the script might it ask you for your SSH key passphrase. It is
used to store your key in the SSH authentication agent, so the called scripts
can communicate with the IoT-LAB SSH frontend.

#### Environment variables
- `CHANNEL`: (default: 26) The channel the nodes in the experiments use their
  radio on.
- `COUNT`: (default: 100) Number of packets per run per configuration.
- `DELAY`: (default: 10000) Mean delay between packets within the experiment
  runs.
- `EXP_DURATION`: (default: 2880) Length of the IoT-LAB experiment in minutes.
- `NETWORK`: (default: `./../../results/m3-55xc7297640.edgelist.gz`) The
  edge-list of the network to use with the experiments. If the file does not
  exist, a network will be created
- `RUNNING_EXPERIMENT_FILE`: (default: `./running_experiment.txt`) Name of the
  file to store the IoT-LAB experiment ID to
- `RUNS`: (default: 3) The number of runs for each configuration
- `SINK`: (default: 55) Sink M3 node for the experiments (must be in line with
  `NETWORK`)
- `SITE`: (default: `lille`) IoT-LAB site the experiment should run at
  (must be in line with `NETWORK`)
- `TMUX_SESSION`: The TMUX target to run the experiments in

Additionally, all environment variables accepted by the
[`run_experiment.py`](#run_experimentpy) script can also be used (unless they
get overwritten by the above-mentioned environment variables).

### `setup_exp.sh`

Helper script to automatically put `dispatch_runs.sh` (and its generated TMUX
windows) in a TMUX session with proper SSH authentication agent configuration.

As such, when starting the script, it might ask you for your SSH key passphrase.
It is used to store your key in the SSH authentication agent, so the called
scripts can communicate with the IoT-LAB SSH frontend.

[M3 nodes]: https://www.iot-lab.info/hardware/m3/
[IoT-LAB testbed]: https://www.iot-lab.info/
