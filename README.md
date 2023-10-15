# autostart-i3ipc

```bash
~ $ .config/sway/scripts/startup.py -h
usage: startup.py [-h] [-c CONFIG]

A smart but also lazy login autostart manager for i3/Sway.

Will conditionally exec other things defined in a YML dict. ie: every day, work days, or weekends

Required i3/Sway config line:
    exec .config/sway/scripts/startup.py

Config sample:
---
autostarts:
  pre: []  # blocking tasks that run every day, before any other section. intended for backups/updates
  common: []  # non-blocking tasks that run every day
  weekend: []  # blocking tasks for weekends, after 'pre' but before 'common'
  work: []  # non-blocking tasks run if Monday through Friday between 8AM - 4PM

options:
  -h, --help            show this help message and exit
  -c CONFIG, --config CONFIG
                        Path to the YML configuration file. (default: /home/user/.config/sway/autostart.yml)
```