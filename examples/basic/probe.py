"""Synthetic process outcomes used by the public quick-start manifest."""

import os
import signal
import sys
import time


mode = sys.argv[1]
if mode == "clean":
    print("SURVIVED")
elif mode == "crlf-clean":
    sys.stdout.buffer.write(b"SURVIVED\r\n")
elif mode == "declared-crash":
    raise SystemExit(99)
elif mode == "signal-crash":
    os.kill(os.getpid(), signal.SIGSEGV)
elif mode == "timeout":
    time.sleep(60)
elif mode == "malformed":
    print("finished without the required marker")
elif mode == "error":
    print("synthetic harness error", file=sys.stderr)
    raise SystemExit(2)
else:
    raise SystemExit(f"unknown mode: {mode}")
