# Contributing

## Helping implement new features

Some features require capturing device data before they can be implemented. If you're affected by one of those open issues and want to help, follow the steps below.

### What you'll be doing

You'll run a monitoring script that logs communication between the Dreame cloud and your device.

### Setup (one time)

You need Python 3.11+ and Git.

```bash
git clone https://github.com/antondaubert/dreame-mower.git
cd dreame-mower
python3 -m venv .venv
.venv/bin/pip install -r tests/requirements.txt
```

### Step 1 – find your device ID

```bash
.venv/bin/python dev/list_devices.py
```

Enter your Dreame account email and password when prompted. You will also be asked for your region — choose the one matching your account (`eu`, `cn`, `us`, `ru`, or `sg`). Note the numeric `did` value for your mower from the output.

### Step 2 – run the monitor

```bash
.venv/bin/python dev/realtime_monitor.py
```

Enter your email, password, region, and the device ID from Step 1 when prompted.

Now use the **Dreame app** to perform the action described in the issue (e.g. switch maps, start a zone mow). Do this a few times if you can. Let the monitor run for a couple of days or at least long enough to capture a few repetitions. Note: please ensure your computer doesn't go into sleep mode during this period.

Stop it with `Ctrl+C` when done. Logs are written to `dev/logs/<timestamp>/`.

### Step 3 – zip and attach

```bash
zip -r logs_capture.zip dev/logs/
```

Attach `logs_capture.zip` as a file to the GitHub issue.

---

That's it — thank you for helping!
