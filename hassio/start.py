#!/usr/bin/env python
import sys
import threading

import insteon_mqtt
import webcli

threading.Thread(target=webcli.app.start_webcli, daemon=True).start()
status = insteon_mqtt.cmd_line.main()
sys.exit(status)
