usurp systemd user service

Install:

  mkdir -p ~/.config/systemd/user ~/.config/usurp ~/.cache/usurp
  install -m 0644 packaging/systemd/usurp.service ~/.config/systemd/user/usurp.service
  chmod 700 ~/.config/usurp
  systemctl --user daemon-reload
  systemctl --user enable --now usurp.service

The unit expects the checkout and uv-managed environment at:

  %h/Projects/usurp/.venv/bin/python

Override WorkingDirectory or ExecStart in a user drop-in when deploying elsewhere. Check status and logs with:

  systemctl --user status usurp.service
  journalctl --user -u usurp.service -e

Do not place real credentials in this repository. The environment file is optional; omit USURP_API_KEY to run without API-key enforcement.
