# -*- coding: utf-8 -*-
"""
Created by Maen Artimy, 2022 - 2023
"""

import os
import sys
import pandas as pd
from pybatfish.client.commands import bf_session, bf_set_network, bf_init_snapshot
from pybatfish.question import load_questions
from pybatfish.question import bfq
from pybatfish.client.asserts import (
    assert_no_duplicate_router_ids,
    assert_no_incompatible_bgp_sessions,
    assert_no_unestablished_bgp_sessions,
    assert_no_undefined_references,
    assert_num_results,
    assert_zero_results,
)
from rich.console import Console
console = Console(color_system="truecolor")

import logging
logging.getLogger("pybatfish").setLevel(logging.ERROR)


# Get environment variables and constants
BATFISH_SERVER = os.getenv("BATFISH_SERVER")
NETWORK_NAME = "DESIGN_LAB1"
SNAPSHOT_NAME = "lab1"
SNAPSHOT_DIR = "lab"

# from rich import print as rprint

pd.set_option("display.max_columns", None)
pd.set_option("expand_frame_repr", False)


# Snap info
NUM_FILES = 5
DOMAIN_NAME = "inwk.local"
routers = ["r11", "r12", "r21", "r22", "r23"]
servers = set(["10.1.155.100"])


def test_num_routers(num):
    """
    Testing for number of devices

    The test fails if the number of files is not equal to 'num'
    """

    console.rule("[bold yellow]Testing number of config files")
    file_status = bfq.fileParseStatus().answer()
    assert_num_results(file_status, num, soft=False)


def test_init_issues():
    """
    Testing for parsing violations

    The test fails if Batfish cannot recognize certain lines
    in the configuration due to lack of support for certain features.
    """

    console.rule("[bold yellow]Testing for init issues")
    inissue = bfq.initIssues().answer()
    assert_zero_results(inissue, soft=True)


def test_clean_parsing():
    """
    Testing for parsing violations

    The test fails if the returned status is not 'PASSED'
    """

    console.rule("[bold yellow]Testing for clean parsing")
    file_status = bfq.fileParseStatus().answer().frame()
    status_violations = file_status[file_status["Status"] != "PASSED"]
    assert_zero_results(status_violations, soft=True)


def test_host_properties(domain, hosts, ntp_servers):
    """
    Testing correct properties

    Test fails if any device property does not match requirements
    """

    console.rule("[bold yellow]Testing for host properties")

    node_props = (
        bfq.nodeProperties(nodes="", properties="Hostname, Domain_Name, NTP_Servers")
        .answer()
        .frame()
    )
    name_violators = node_props[node_props["Hostname"].apply(lambda x: x not in hosts)]
    assert_zero_results(name_violators, soft=False)

    domain_violators = node_props[
        node_props["Domain_Name"].apply(lambda x: x != domain)
    ]
    assert_zero_results(domain_violators, soft=False)

    ns_violators = node_props[
        node_props["NTP_Servers"].apply(
            lambda x: len(ntp_servers.intersection(set(x))) == 0
        )
    ]
    assert_zero_results(ns_violators, soft=False)


def test_shut_interfaces():
    """
    Testing unused interfaces are shut

    Test fails if ports 2 or 3 are active
    """

    console.rule("[bold yellow]Testing for shut interfaces")
    violators = bfq.interfaceProperties(
        interfaces="/GigabitEthernet[23]/",
        properties="Active",
        excludeShutInterfaces=True,
    ).answer()
    assert_zero_results(violators, soft=True)


def test_undefined_references(snap):
    """
    Test for references to undefined structures

    """

    console.rule("[bold yellow]Testing for undefined references")
    assert_no_undefined_references(snapshot=snap, soft=False)


def test_duplicate_rtr_ids(snap):
    """
    Testing for duplicate router IDs
    """

    console.rule("[bold yellow]Testing for duplicate router IDs")
    assert_no_duplicate_router_ids(snapshot=snap, protocols={"bgp"})


def test_bgp_compatibility(snap):
    """
    Testing for incompatible BGP sessions
    """

    console.rule("[bold yellow]Testing for incompatible BGP sessions")
    assert_no_incompatible_bgp_sessions(snapshot=snap)


def test_bgp_unestablished(snap):
    """
    Testing for BGP sessions that are not established
    """

    console.rule("[bold yellow]Testing for unestablished BGP sessions")
    assert_no_unestablished_bgp_sessions(snapshot=snap)


def main():
    """Initialize batfish"""

    bf_session.host = BATFISH_SERVER
    bf_set_network(NETWORK_NAME)
    init_snap = bf_init_snapshot(SNAPSHOT_DIR, name=SNAPSHOT_NAME, overwrite=True)
    load_questions()

    test_num_routers(NUM_FILES)
    test_init_issues()
    test_clean_parsing()
    test_host_properties(DOMAIN_NAME, routers, servers)
    test_shut_interfaces()
    test_undefined_references(init_snap)
    test_duplicate_rtr_ids(init_snap)
    test_bgp_compatibility(init_snap)
    test_bgp_unestablished(init_snap)

    console.rule("[bold green]:heavy_check_mark: All checks passed :heavy_check_mark:")


if __name__ == "__main__":
    try:
        main()
    except Exception as e:
        console.rule("[bold red]:X: Checks Failed :X:")
        console.print(f"[bold red]{e}")
        sys.exit(1)
