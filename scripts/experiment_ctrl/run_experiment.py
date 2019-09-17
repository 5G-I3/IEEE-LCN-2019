#! /usr/bin/env python3
# -*- coding: utf-8 -*-
# vim:fenc=utf-8
#
# Copyright (C) 2019 Freie Universität Berlin
#
# This file is subject to the terms and conditions of the GNU Lesser
# General Public License v2.1. See the file LICENSE in the top level
# directory for more details.

import asyncio
import argparse
import csv
import logging
import multiprocessing
import os
import pexpect
import pprint
import random
import signal
import sys
import time
import urllib.error

from iotlabcli.profile import ProfileM3

from iotlab_controller.common import get_default_api, get_uri
from iotlab_controller.constants import IOTLAB_DOMAIN
from iotlab_controller.experiment.base import ExperimentError
from iotlab_controller.experiment.tmux import TmuxExperiment
from iotlab_controller.riot import RIOTFirmware
from iotlab_controller.nodes import SinkNetworkedNodes

import construct_network


__author__ = "Martine S. Lenders"
__copyright__ = "Copyright 2019 Freie Universität Berlin"
__license__ = "LGPL v2.1"
__email__ = "m.lenders@fu-berlin.de"

BOARD = os.environ.get("BOARD", "iotlab-m3")
SINK_FIRMWARE_NAME = os.environ.get("SINK_FIRMWARE_NAME", "lcn19_sink")
SOURCE_FIRMWARE_NAME = os.environ.get("SOURCE_FIRMWARE_NAME",
                                      "lcn19_source")


SCRIPT_PATH = os.path.dirname(os.path.realpath(__file__))
APPS_PATH = os.path.join(SCRIPT_PATH, "..", "..", "apps")

DATA_PATH = os.environ.get("DATA_PATH",
                           os.path.join(SCRIPT_PATH, "..", "..", "results"))
RUNNING_EXPERIMENT_FILE = os.environ.get(
    "RUNNING_EXPERIMENT_FILE", os.path.join(SCRIPT_PATH,
                                            "running_experiment.txt")
)
ULA_PREFIX = os.environ.get("ULA_PREFIX", "2001:db8:0:1:")

ARCHI_SHORT = "m3"
ARCHI_FULL = "m3:at86rf231"

MODES = set(("reass", "fwd"))
SINK_PORT = 6383
LINK_LOCAL_PREFIX = "fe80::"

DEFAULT_EXP_NAME_FORMAT = "lcn19_n{network}_c{channel}"
DEFAULT_SINK_FIRMWARE_PATH = os.path.join(APPS_PATH, "sink")
DEFAULT_SOURCE_FIRMWARE_PATH = os.path.join(APPS_PATH, "source")
DEFAULT_MODE = "fwd"
DEFAULT_DATA_LEN = 16
DEFAULT_COUNT = 100
DEFAULT_DELAY = 10000
DEFAULT_CHANNEL = 26
DEFAULT_DURATION = 60


def run_experiment(exp, mode, data_len, count, delay, sniff=False,
                   run_duration=None):
    sources = exp.nodes.non_sink_nodes
    run_name = os.path.join(
        DATA_PATH,
        "{exp_name}__m{mode}_r{data_len}Bx{count}x{delay}ms_{timestamp}"
        .format(exp_name=exp.name, mode=mode, data_len=data_len, count=count,
                delay=delay, timestamp=int(time.time()))
    )
    if run_duration is None:
        # wait mean time for all packets + the mean delay + some extra time
        run_duration = (count * (delay / 1000)) + (delay / 1000) + 120
    if ("SSH_AUTH_SOCK" in os.environ) and ("SSH_AGENT_PID" in os.environ):
        exp.cmd("export SSH_AUTH_SOCK='{}'"
                .format(os.environ["SSH_AUTH_SOCK"]))
        exp.cmd("export SSH_AGENT_PID='{}'"
                .format(os.environ["SSH_AGENT_PID"]))
    if sniff:
        sniffer = _start_sniffer(exp, "{}.pcap".format(run_name))
    else:
        sniffer = None
    _load_lladdr_ifaces(exp)
    exp.start_serial_aggregator(exp.nodes.site,
                                logname="{}.log".format(run_name))
    logging.info("Constructing routes")
    sink_addr = _construct_routes(exp)
    exp.cmd("ifconfig", wait_after=3)
    exp.cmd("nib route", wait_after=3)
    random.shuffle(sources)
    logging.info("Starting experiment")
    # Non existing command to mark start of experiment
    exp.cmd("{};starting experiment".format(exp.nodes.sink), wait_after=.5)
    tasks = map(lambda n:
                _start_source(exp, n[0], n[1], sink_addr,
                              data_len, count, delay),
                enumerate(sources))
    asyncio.get_event_loop().run_until_complete(asyncio.gather(*tasks))
    logging.info("Waiting for {}s for experiment {} (until {}) to finish"
                 .format(run_duration, run_name,
                         time.asctime(time.localtime(time.time() +
                                                     run_duration))))
    time.sleep(run_duration)
    exp.hit_enter()
    exp.cmd("6lo_frag", wait_after=3)
    exp.cmd("ifconfig")
    logging.info("Waiting for 120 s for queues to empty to dump packet "
                 "buffer stats")
    # give packet queues etc some time to empty
    time.sleep(120)
    exp.cmd("pktbuf", wait_after=3)
    exp.stop_serial_aggregator()
    _stop_sniffer(sniffer)


async def _start_source(exp, i, nodename, sink_addr, data_len, count, delay):
    # wait at least .1 seconds to not mix-up send-keys to tmux
    if delay > 10:
        wait = (i * 0.01) + \
               random.randint(0, (delay * 1500) - (delay * 500)) / 1000000
    else:
        wait = 0.1
    logging.info("Waiting for {}s for {} to start".format(wait, nodename))
    await asyncio.sleep(wait)
    exp.cmd("{};source {} {} {} {} {}"
            .format(nodename, sink_addr, SINK_PORT, data_len, count, delay))


def _load_lladdr_ifaces(exp):
    logging.info("Loading interfaces and link-local addresses of nodes")
    lla_file = os.path.join(DATA_PATH, "{}.link_local.csv".format(exp.nodes))
    if os.path.exists(lla_file):
        with open(lla_file) as csvfile:
            reader = csv.DictReader(csvfile)
            cnt = 0
            for row in reader:
                node = row["node"]
                exp.nodes[node].iface = row["iface"]
                exp.nodes[node].lla = row["lla"]
                cnt += 1
            if cnt == len(exp.nodes):
                return
    child = pexpect.spawnu(
            "ssh {}@{}.{} serial_aggregator -i {}".format(
                    exp.username, exp.nodes.site, IOTLAB_DOMAIN, exp.exp_id
                ),
            timeout=3
        )
    if logging.root.level == logging.DEBUG:
        child.logfile = sys.stdout
    with open(lla_file, "w") as csvfile:
        writer = csv.writer(csvfile)
        writer.writerow(["node", "iface", "lla"])
        for node in exp.nodes:
            nodename = node.uri.split(".")[0]
            child.sendline("{};ifconfig".format(nodename))
            res = child.expect([r"{};Iface\s+(\d+)".format(nodename),
                                r"Node not managed: m3-(\d+)"])
            if res > 0:
                raise ExperimentError("Network contains node not within the "
                                      "experiment: m3-{}"
                                      .format(child.match.group(1)))
            node.iface = int(child.match.group(1))
            child.expect(r"{};\s+inet6 addr: ({}[0-9a-f:]+)\s+scope: local\s+"
                         r"VAL".format(nodename, LINK_LOCAL_PREFIX))
            node.lla = child.match.group(1)
            writer.writerow([nodename, node.iface, node.lla])
        while not child.terminated:
            try:
                os.killpg(os.getpgid(child.pid), signal.SIGKILL)
            except ProcessLookupError:
                break
            else:
                child.close()
                time.sleep(5)


def _ula_from_link_local(link_local):
    return link_local.replace(LINK_LOCAL_PREFIX, ULA_PREFIX)


def _construct_routes(exp):
    # construct network using depth-first search
    stack = []
    stack.append(exp.nodes.sink)
    visited = set()
    while stack:
        n = stack.pop()
        if n not in visited:
            node = exp.nodes[n]
            nll = node.lla
            # Add global unicast address to interface
            exp.cmd("{nodename};ifconfig {iface} add {ula}"
                    .format(nodename=n, iface=node.iface,
                            ula=_ula_from_link_local(nll)), wait_after=.1)
            for neighbor in exp.nodes.neighbors(n):
                # setting default route from neighbors to n
                if neighbor not in visited:
                    exp.cmd("{nodename};nib route add {iface} default {ll}"
                            .format(nodename=neighbor,
                                    iface=exp.nodes[neighbor].iface,
                                    ll=nll),
                            wait_after=.3)
                stack.append(neighbor)
            visited.add(n)
    return _ula_from_link_local(exp.nodes[exp.nodes.sink].lla)


def _start_sniffer(exp, pcap_file):
    sniffer = exp.tmux_session.session.find_where({"window_name": "sniffer"})
    if sniffer is None:
        sniffer = exp.tmux_session.session.new_window("sniffer", DATA_PATH,
                                                      attach=False)
    sniffer = sniffer.select_pane(0)
    # kill currently running sniffer
    sniffer.send_keys("C-c", suppress_history=False)
    sniffer.send_keys("ssh {}@{}.{} sniffer_aggregator -o - -i {} > {}"
                      .format(exp.username, exp.nodes.site,
                              IOTLAB_DOMAIN, exp.exp_id, pcap_file),
                      enter=True, suppress_history=False)
    return sniffer


def _stop_sniffer(sniffer=None):
    if sniffer is not None:
        sniffer.cmd("send-keys", "C-c")


def _get_sniffer_profile(api, channel=DEFAULT_CHANNEL):
    for profile in api.get_profiles(ARCHI_SHORT):
        if (profile.get("radio") is not None) and \
           (profile["radio"].get("mode") == "sniffer") and \
           (channel in profile["radio"].get("channels")):
            return profile["profilename"]
    profile = ProfileM3(profilename="sniffer{}".format(channel), power="dc")
    profile.set_radio(channels=[channel], mode="sniffer")
    api.add_profile(profile.profilename, profile)
    return profile.profilename


def _parse_tmux_target(tmux_target, name):
    res = {}
    if tmux_target is not None:
        session_window = tmux_target.split(":")
        res["session_name"] = session_window[0]
        if len(session_window) > 1:
            window_pane = (":".join(session_window[1:])).split(".")
            res["window_name"] = window_pane[0]
            if len(window_pane) > 1:
                res["pane_id"] = ".".join(window_pane[1:])
    else:
        res["session_name"] = name
    return res


def start_experiment(network, name=None, duration=DEFAULT_DURATION,
                     sink_firmware_path=DEFAULT_SINK_FIRMWARE_PATH,
                     source_firmware_path=DEFAULT_SOURCE_FIRMWARE_PATH,
                     exp_id=None, channel=DEFAULT_CHANNEL, reflash=False,
                     tmux_target=None, mode=DEFAULT_MODE,
                     data_len=DEFAULT_DATA_LEN, count=DEFAULT_COUNT,
                     delay=DEFAULT_DELAY, run_duration=None, sniff=False,
                     api=None):
    if name is None:
        name = DEFAULT_EXP_NAME_FORMAT.format(network=network, channel=channel)
    if api is None:
        api = get_default_api()

    logging.info("Building firmwares")
    env = {"MODE": mode, "DEFAULT_CHANNEL": str(channel)}
    sink_firmware = RIOTFirmware(sink_firmware_path, BOARD,
                                 SINK_FIRMWARE_NAME, env=env)
    threads = multiprocessing.cpu_count()
    sink_firmware.build(threads=threads)
    source_firmware = RIOTFirmware(source_firmware_path, BOARD,
                                   SOURCE_FIRMWARE_NAME, env=env)
    source_firmware.build(threads=threads)

    # select profiles if user wants to sniff
    if sniff:
        profiles = [_get_sniffer_profile(api, channel)]
        logging.info("Selected sniffing profile {}".format(profiles[0]))
    else:
        profiles = None

    # create and prepare IoT-LAB experiment
    exp = TmuxExperiment(name, network, run_experiment,
                         [sink_firmware] +
                         (len(network) - 1) * [source_firmware],
                         exp_id, profiles, mode=mode, count=count,
                         data_len=data_len, delay=delay, sniff=sniff,
                         run_duration=run_duration, api=api)
    if exp.is_scheduled():
        try:
            if sniff:
                logging.info(" ... (re-)setting sniffing profile")
                res = network.profile(exp.exp_id, profiles[0])
                if '1' in res:
                    logging.error(pprint.pformat(res))
                    sys.exit(1)
                else:
                    logging.debug(pprint.pformat(res))
            logging.info(" ... waiting for experiment {} to start"
                         .format(exp.exp_id))
            exp.wait()
            if reflash:
                logging.info(" - reflashing firmwares")
                res = network.flash(exp.exp_id, source_firmware, sink_firmware)
            else:
                logging.info(" - resetting nodes")
                res = network.reset(exp.exp_id)
            if '1' in res:
                logging.error(pprint.pformat(res))
                sys.exit(1)
            else:
                logging.debug(pprint.pformat(res))
        except urllib.error.HTTPError as e:
            if os.path.exists(RUNNING_EXPERIMENT_FILE):
                os.remove(RUNNING_EXPERIMENT_FILE)
            raise e
    else:
        logging.info("Scheduling experiment with duration {}".format(duration))
        exp.schedule(duration)
        logging.info(" - Experiment ID: {}".format(exp.exp_id))
        with open(RUNNING_EXPERIMENT_FILE, "w") as running_exp:
            running_exp.write("-i {}".format(exp.exp_id))
        logging.info(" ... waiting for experiment to start")
        exp.wait()
    tmux_target = _parse_tmux_target(tmux_target, name)
    logging.info("Starting TMUX session in {}".format(tmux_target))
    tmux_session = exp.initialize_tmux_session(**tmux_target)
    assert tmux_session
    exp.hit_ctrl_c()    # Kill potentially still running experiment
    time.sleep(.1)
    exp.run()


def load_network(sink, edgelist_file,
                 iotlab_site=construct_network.DEFAULT_IOTLAB_SITE):
    sink = "m3-{}".format(sink)
    network = SinkNetworkedNodes(iotlab_site, sink, edgelist_file)
    if get_uri(iotlab_site, sink) not in network:
        raise construct_network.NetworkConstructionError(
            "Sink {} not in network {}".format(sink, network)
        )
    return network


def main():
    def existing_file(parser, arg):
        arg = str(arg)
        if not os.path.exists(arg):
            parser.error("The file {} does not exist!".format(arg))
        else:
            return arg

    parser = argparse.ArgumentParser()
    parser.add_argument("-d", "--duration", default=DEFAULT_DURATION, type=int,
                        help="IoT-LAB experiment duration "
                             "(default: {})".format(DEFAULT_DURATION))
    parser.add_argument("-c", "--count", default=DEFAULT_COUNT, type=int,
                        help="Number of UDP packets to send per source "
                             "(default: {})".format(DEFAULT_COUNT))
    parser.add_argument("-l", "--data-len", default=DEFAULT_DATA_LEN, type=int,
                        help="Payload size of the UDP packets to sent "
                             "(default: {})".format(DEFAULT_DATA_LEN))
    parser.add_argument("-W", "--delay", default=DEFAULT_DELAY, type=int,
                        nargs="+", help="Delay between the UDP packets sent "
                                        "(default: {})".format(DEFAULT_DELAY))
    parser.add_argument("-S", "--iotlab-site",
                        default=construct_network.DEFAULT_IOTLAB_SITE,
                        help="IoT-LAB site to pick nodes from (default: {})"
                        .format(construct_network.DEFAULT_IOTLAB_SITE))
    parser.add_argument("-f", "--edgelist-file",
                        default=None, type=lambda t: existing_file(parser, t),
                        help="NetworkX edge-list for the network (optional, "
                             "if not provided `construct_network` will be "
                             "run before experiment starts)")
    parser.add_argument("-i", "--exp-id", default=None, type=int,
                        help="ID of a pre-existing IoT-LAB experiment "
                             "(optional)")
    parser.add_argument("-r", "--reflash", action="store_true",
                        help="When given with --exp-id: reflash nodes of "
                             "IoT-LAB experiment instead of resetting it")
    parser.add_argument("-t", "--tmux-target", default=None,
                        help="TMUX target for experiment control "
                             "(default: the IoT-LAB experiment name)")
    parser.add_argument("-s", "--sniff", action="store_true",
                        help="Activate sniffer profile for all participating "
                             "nodes")
    parser.add_argument("-v", "--verbose", action="store_true",
                        help="Increase output verbosity (logging level DEBUG)")
    parser.add_argument("--channel", default=DEFAULT_CHANNEL, type=int,
                        help="Channel (for sniffer profile) "
                             "(default: {})".format(DEFAULT_CHANNEL))
    parser.add_argument("--run-duration", type=int, default=None,
                        help="Duration of a single run in the experiment in "
                        "seconds (default: calculated from --delay and "
                        "--count)")
    parser.add_argument("sink", type=int,
                        help="Number of the M3 sink node within the network")
    parser.add_argument("mode", default=DEFAULT_MODE, choices=MODES, nargs="?",
                        help="Experiment mode (reass: hop-wise reassembly, "
                             "fwd: fragment forwarding)")
    args = parser.parse_args()
    logging.basicConfig(format='%(asctime)s:%(levelname)s: %(message)s',
                        level=logging.DEBUG if args.verbose else logging.INFO)
    api = get_default_api()
    if args.edgelist_file is None:
        network = construct_network.construct_network(
            args.sink, args.iotlab_site, api=api
        )
    else:
        network = load_network(args.sink, args.edgelist_file, args.iotlab_site)
    start_experiment(network, duration=args.duration, exp_id=args.exp_id,
                     channel=args.channel, reflash=args.reflash,
                     tmux_target=args.tmux_target, mode=args.mode,
                     data_len=args.data_len, count=args.count,
                     delay=args.delay, run_duration=args.run_duration,
                     sniff=args.sniff, api=api)


if __name__ == "__main__":
    main()
