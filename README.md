# sway-autostart-i3ipc

A smart but also lazy login autostart manager for i3/Sway.
Will conditionally exec other things defined in a YML dict.

Required i3/Sway config line:

```bash
    exec path/to/startup.py
```

Work days may be temporarily disabled by creating and removing
`~/.vacation` when appropriate.

The config may be chosen with `-c path/to/autostart.yml`.
Default is `$XDG_CONFIG_HOME/sway/autostart.yml`.

## Config sample

```yaml
---
autostarts:
  pre: []  # blocking tasks that run every day, before any other section. intended for backups/updates
  common: []  # non-blocking tasks that run every day
  weekend: []  # blocking tasks for weekends, after 'pre' but before 'common'
  work: []  # non-blocking tasks run if Monday through Friday between 8AM - 4PM
```
