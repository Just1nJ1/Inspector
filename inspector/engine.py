"""Core Inspector engine -- start / stop and state management."""

import sys
import os
import inspect as _inspect

from .utils import shallow_copy
from . import display
from .tracer import make_trace


class Inspector:
    """Singleton inspector engine.

    Activated by :func:`start` and deactivated by :func:`stop` or the
    interactive ``q`` command.  Traces only the file that called ``start()``.
    """

    def __init__(self):
        self._active = False
        self._target_file: str | None = None
        self._source_lines: list[str] = []
        self._step_mode = True
        self._breakpoints: set[int] = set()
        self._prev_vars: dict = {}
        self._call_stack: list[dict] = []
        self._watches: list[str] = []
        self._steps_taken = 0
        self._trace_fn = None           # built by make_trace()

    # ── public API ───────────────────────────────────────────────────────

    def start(self, step: bool = True, _stack_depth: int = 2):
        """Begin tracing from the caller's next line."""
        caller = _inspect.stack()[_stack_depth]
        caller_frame = caller.frame
        self._target_file = os.path.abspath(caller.filename)
        self._step_mode = step
        self._active = True
        self._call_stack = []
        self._steps_taken = 0
        self._load_source(self._target_file)

        # Snapshot the caller's existing variables so they appear as
        # already-known (not tagged [new]) on the first traced line.
        self._prev_vars = shallow_copy(caller_frame.f_locals)

        # Build a fresh trace closure bound to this engine.
        self._trace_fn = make_trace(self)

        display.print_header(self._target_file)

        # Install the trace on the caller's frame so the very next line
        # is the first one we see.
        caller_frame.f_trace = self._trace_fn
        sys.settrace(self._trace_fn)

    def stop(self):
        """Stop tracing (called from user code or the 'q' command)."""
        if not self._active:
            return
        self._active = False
        sys.settrace(None)
        # Clear f_trace on every frame up the stack that we touched
        frame = _inspect.currentframe()
        while frame is not None:
            frame.f_trace = None
            frame = frame.f_back
        display.print_footer(self._steps_taken)

    # ── source handling ──────────────────────────────────────────────────

    def _load_source(self, path: str):
        try:
            with open(path, "r") as f:
                self._source_lines = f.readlines()
        except FileNotFoundError:
            self._source_lines = []
