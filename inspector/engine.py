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
        self._conditional_breakpoints: dict[int, str] = {}  # line -> condition
        self._prev_vars: dict = {}
        self._call_stack: list[dict] = []
        self._watches: list[str] = []
        self._steps_taken = 0
        self._trace_fn = None           # built by make_trace()
        # Configurable display options
        self._context_lines: int = 3    # lines of source context around current line
        self._stack_depth: int = 10     # max number of stack frames to display
        self._clear_screen: bool = True # clear screen before each step
        # GUI mode
        self._use_gui: bool = False     # use GUI instead of CLI
        self._gui = None                # InspectorGUI instance
        # Variable filter (regex pattern, None means no filter)
        self._var_filter = None         # re.Pattern or None

    # ── public API ───────────────────────────────────────────────────────

    def start(self, step: bool = True, _stack_depth: int = 2, gui: bool = False):
        """Begin tracing from the caller's next line.
        
        Args:
            step: If True, pause every line. If False, only pause at breakpoints.
            gui: If True, use Tkinter GUI instead of command-line interface.
        """
        caller = _inspect.stack()[_stack_depth]
        caller_frame = caller.frame
        self._target_file = os.path.abspath(caller.filename)
        self._step_mode = step
        self._active = True
        self._call_stack = []
        self._steps_taken = 0
        self._use_gui = gui
        self._load_source(self._target_file)

        # Snapshot the caller's existing variables so they appear as
        # already-known (not tagged [new]) on the first traced line.
        self._prev_vars = shallow_copy(caller_frame.f_locals)

        # Build a fresh trace closure bound to this engine.
        self._trace_fn = make_trace(self)

        if not gui:
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
        # Close GUI if using GUI mode
        if self._use_gui and self._gui:
            self._gui.close()
            self._gui = None
        if not self._use_gui:
            display.print_footer(self._steps_taken)

    # ── source handling ──────────────────────────────────────────────────

    def _load_source(self, path: str):
        try:
            with open(path, "r") as f:
                self._source_lines = f.readlines()
        except FileNotFoundError:
            self._source_lines = []
