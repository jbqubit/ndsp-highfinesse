#!/usr/bin/env python3

# Written by Joe Britton, 2015
# Modified by Ryan Gresia, 2021

import argparse
import logging
import sys
import os
import asyncio

from highfinesse.driver import HighFinesse
from sipyco.pc_rpc import simple_server_loop
from sipyco import common_args

logger = logging.getLogger(__name__)


def get_argparser():
    parser = argparse.ArgumentParser(
        description="ARTIQ controller for the Britton Lab High Finesse wavemeter")
    common_args.simple_network_args(parser, 3260)
    parser.add_argument(
        "--simulation", action="store_true",
        help="Put the driver in simulation mode, even if --device is used.")
    common_args.verbosity_args(parser)
    return parser


def main():
    args = get_argparser().parse_args()
    common_args.init_logger_from_args(args)

    if os.name == "nt":
        asyncio.set_event_loop(asyncio.ProactorEventLoop())

    dev = HighFinesse(args.simulation)
    asyncio.get_event_loop().run_until_complete(dev.init())
    try:
        simple_server_loop(
            {"HighFinesse": dev}, common_args.bind_address_from_args(args), args.port)
    finally:
        dev.close()

if __name__ == "__main__":
    main()
