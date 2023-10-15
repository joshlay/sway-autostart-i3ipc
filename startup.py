#!/usr/bin/env python3
# pylint: disable=line-too-long
"""
A smart but also lazy login autostart manager for i3/Sway.

Will conditionally exec other things defined in a YML dict. ie: every day, work days, or weekends

Required i3/Sway config line:
    exec /home/jlay/.config/sway/scripts/startup.py

Config sample:
---
autostarts:
  pre: []  # blocking tasks that run every day, before any other section. intended for backups/updates
  common: []  # non-blocking tasks that run every day
  weekend: []  # blocking tasks for weekends, after 'pre' but before 'common'
  work: []  # non-blocking tasks run if Monday through Friday between 8AM - 4PM

Dependencies: python3-i3ipc
"""
import os
import subprocess
from datetime import datetime
from time import sleep
import argparse
from textwrap import dedent
from systemd import journal
import yaml.loader
from i3ipc import Connection
from xdg import XDG_CONFIG_HOME  # pylint: disable=no-name-in-module


def log_message(
    message: str, level: str, syslog_identifier: str = "sway-autostart"
) -> None:
    """Given `message`, send it to the journal and print

    Accepts 'journal' levels. ie: `journal.LOG_{ERR,INFO,CRIT,EMERG}'
    """
    valid_levels = {
        journal.LOG_EMERG,
        journal.LOG_ALERT,
        journal.LOG_CRIT,
        journal.LOG_ERR,
        journal.LOG_WARNING,
        journal.LOG_NOTICE,
        journal.LOG_INFO,
        journal.LOG_DEBUG,
    }
    if level not in valid_levels:
        raise ValueError(f"Invalid log level: {level}")
    print(message)
    journal.send(message, PRIORITY=level, SYSLOG_IDENTIFIER=syslog_identifier)


def parse_args():
    """If run interactively, this provides arg function to the user"""
    description_text = dedent(
        f"""\
    A smart but also lazy login autostart manager for i3/Sway.

    Will conditionally exec other things defined in a YML dict. ie: every day, work days, or weekends

    Required i3/Sway config line:
        exec {os.path.abspath(__file__)}

    Config sample:
    ---
    autostarts:
      pre: []  # blocking tasks that run every day, before any other section. intended for backups/updates
      common: []  # non-blocking tasks that run every day
      weekend: []  # blocking tasks for weekends, after 'pre' but before 'common'
      work: []  # non-blocking tasks run if Monday through Friday between 8AM - 4PM
    """
    )

    class PlainDefaultFormatter(
        argparse.ArgumentDefaultsHelpFormatter, argparse.RawDescriptionHelpFormatter
    ):
        """Combines two ArgParse formatter classes:
        - argparse.ArgumentDefaultsHelpFormatter
        - argparse.RawDescriptionHelpFormatter"""

    parser = argparse.ArgumentParser(
        description=description_text, formatter_class=PlainDefaultFormatter
    )

    # Default path for the config
    default_config = os.path.join(XDG_CONFIG_HOME, "autostart-i3ipc.yml")

    parser.add_argument(
        "-c",
        "--config",
        default=default_config,
        help="Path to the YML configuration file.",
    )

    return parser.parse_args()


# OOPy way to determine if it's a work day -- mon<->friday, 3AM<->5PM
class WorkTime(datetime):
    """datetime but with work on the mind"""

    def is_workday(self):
        """determine if it's a work day: monday-friday between 3AM and 5PM.
        Use .vacation file to go on vacation"""

        # first check if ~/.vacation exists - if so, not a work day
        if os.path.isfile(os.path.expanduser("~/.vacation")):
            return False

        # note: last number in range isn't included
        if not self.is_weekend() and self.hour in range(8, 16):
            return True
        return False

    def is_weekend(self):
        """determine if it's the weekend or not, ISO week day outside 1-5"""
        if self.isoweekday() not in range(1, 6):
            return True
        return False


if __name__ == "__main__":
    args = parse_args()
    config_path = args.config

    # get the current time
    now = WorkTime.now()
    # determine if it's a work day using WorkTime above
    workday = now.is_workday()
    weekend = now.is_weekend()

    # initialize empty lists for the different categories
    wants = []  # non-blocking tasks from 'common' and 'workday' sections in config
    pre_list = []  # blocking tasks before the rest
    weekend_list = []  # non-blocking tasks for weekend days/logins

    # check the config file for existence/structure. if found, extend the lists
    if os.path.exists(config_path):
        print(f"found/loading config: '{config_path}'")
        with open(config_path, "r", encoding="utf-8") as _config:
            config_file = yaml.load(_config, Loader=yaml.FullLoader)
            try:
                loaded_starts = config_file["autostarts"]
                wants.extend(loaded_starts["common"])
                if loaded_starts["pre"]:
                    pre_list.extend(loaded_starts["pre"])
                if workday:
                    wants.extend(loaded_starts["work"])
                if weekend:
                    weekend_list.extend(loaded_starts["weekend"])
            except KeyError as key_err:
                log_message(
                    f"Key not found in {config_path}: {key_err.args[0]}",
                    journal.LOG_ERR,
                )
            except NameError as name_err:
                log_message(f"name error: {name_err}", journal.LOG_ERR)

    # get the party started, create a connection to the window manager
    _wm = Connection(auto_reconnect=True)

    # start the blocking tasks - 'pre' and 'weekend'
    # avoid sending them to the WM, would become backgrounded/async
    for pre_item in pre_list:
        try:
            log_message(
                f'running (blocking) "pre" task: "{pre_item}"', journal.LOG_INFO
            )
            subprocess.run(pre_item, shell=True, check=False)
        except subprocess.CalledProcessError as pre_ex:
            log_message(f'failed "{pre_item}": {pre_ex.output}', journal.LOG_ERR)

    if weekend:
        for weekend_item in weekend_list:
            try:
                log_message(
                    f'running (blocking) "weekend" task: "{weekend_item}"',
                    journal.LOG_INFO,
                )
                subprocess.check_output(weekend_item, shell=True)
            except subprocess.CalledProcessError as weekend_except:
                log_message(
                    f'Exception during "{weekend_item}": {weekend_except.output}',
                    journal.LOG_ERR,
                )

    # launch 'common' and 'work' tasks; not expected to block, sent to window manager
    for wanteditem in wants:
        command = "exec " + wanteditem
        log_message(f'sending to WM: "{command}"', journal.LOG_INFO)
        reply = _wm.command(command)
        sleep(0.1)
        if reply[0].error:
            # note: this doesn't check return codes
            # serves to check if there was a parsing/comm. error with the WM
            log_message(
                f'autostart "{command}" failed, couldn\'t reach WM', journal.LOG_ERR
            )

    _wm.main_quit()
