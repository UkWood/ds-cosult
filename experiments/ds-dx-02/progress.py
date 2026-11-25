"""Bounded stderr progress with a heartbeat independent of transport data."""
import sys
from contextlib import contextmanager
from threading import Event, Thread

from protocol import Stop, utc_now


class Progress:
    def __init__(self, stage, report, *, interval=15, stream=None):
        self.stage, self.report = stage, report
        self.interval = interval
        self.stream = sys.stderr if stream is None else stream
        self.completed, self.known, self.spent = 0, 0, 0
        self.task = "-"

    def emit(self, event):
        print(f"{utc_now()} {self.stage} {event} task={self.task} "
              f"completed={self.completed}/{self.known} accounted_nd={self.spent}", file=self.stream, flush=True)

    @contextmanager
    def process(self):
        stopped = Event()

        def heartbeat():
            while not stopped.wait(self.interval):
                self.emit("heartbeat")

        self.emit("START")
        worker = Thread(target=heartbeat, daemon=True)
        worker.start()
        try:
            yield self
        finally:
            stopped.set()
            worker.join()

    def terminal(self, status):
        print(f"{utc_now()} {self.stage} {status} completed={self.completed}/{self.known} "
              f"accounted_nd={self.spent} report={self.report}", file=self.stream, flush=True)


@contextmanager
def reporting(progress):
    try:
        with progress.process():
            yield progress
    except (Stop, KeyboardInterrupt):
        progress.terminal("STOP")
        raise
    except BaseException:
        progress.terminal("ERROR")
        raise
