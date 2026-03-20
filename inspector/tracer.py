"""sys.settrace callback -- the heart of the inspector."""

import os
import sys

from .utils import shallow_copy
from . import display
from .commands import handle_prompt


def make_trace(engine):
    """Return a trace function bound to *engine* (an ``_Inspector`` instance).

    We use a closure so the trace function is a plain function (not a bound
    method) which makes the ``sys.settrace`` / ``frame.f_trace`` contract
    slightly cleaner.
    """

    def _get_source_line(lineno: int) -> str:
        lines = engine._source_lines
        if 1 <= lineno <= len(lines):
            return lines[lineno - 1].rstrip("\n")
        return ""

    def trace(frame, event, arg):
        if not engine._active:
            return None

        filename = frame.f_code.co_filename

        # Only trace the target file (skip inspector package, stdlib, etc.)
        if os.path.abspath(filename) != engine._target_file:
            return trace

        lineno = frame.f_lineno

        # Skip lines that are the start()/stop() calls themselves
        src = _get_source_line(lineno)
        if "inspector.start" in src or "inspector.stop" in src:
            return trace

        if event == "call":
            engine._call_stack.append({
                "func": frame.f_code.co_name,
                "file": os.path.basename(filename),
                "line": lineno,
            })
            return trace

        if event == "return":
            if engine._call_stack:
                engine._call_stack.pop()
            return trace

        if event == "line":
            # Re-check; the line might be stop()
            src = _get_source_line(lineno)
            if "inspector.stop" in src:
                return trace

            should_pause = engine._step_mode or (lineno in engine._breakpoints)
            if not should_pause:
                return trace

            engine._steps_taken += 1
            display.print_location(frame, lineno)
            display.print_source_context(
                engine._source_lines, lineno, engine._breakpoints
            )
            display.print_variables(frame.f_locals, engine._prev_vars)
            display.print_watches(engine._watches, frame)

            if not handle_prompt(engine, frame, lineno):
                return None

            engine._prev_vars = shallow_copy(frame.f_locals)
            return trace

        return trace

    return trace
