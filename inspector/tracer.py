"""sys.settrace callback -- the heart of the inspector."""

import os
import sys

from .utils import shallow_copy
from . import display
from .commands import handle_prompt


def _get_gui():
    """Lazy import and get GUI instance."""
    from .gui import InspectorGUI
    return InspectorGUI()


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

    def _check_conditional_breakpoint(lineno: int, frame) -> bool:
        """Check if a conditional breakpoint at lineno should trigger."""
        if lineno not in engine._conditional_breakpoints:
            return False
        condition = engine._conditional_breakpoints[lineno]
        try:
            return eval(condition, frame.f_globals, frame.f_locals)
        except Exception:
            # If condition fails to evaluate, don't break
            return False

    def _build_display_stack(frame, lineno: int) -> list[dict]:
        """Build the call stack for display.
        
        Stack is ordered top to bottom: top = oldest caller, bottom = current line.
        Uses _call_stack which tracks calls within the target file only.
        """
        stack = list(engine._call_stack)  # Copy parent frames (callers)
        
        # Add current frame entry
        func = frame.f_code.co_name
        fname = os.path.basename(frame.f_code.co_filename)
        stack.append({
            "func": func,
            "file": fname,
            "line": lineno,
        })
        
        # Limit stack depth
        if len(stack) > engine._stack_depth:
            stack = stack[-engine._stack_depth:]
        
        return stack

    def _collect_frame_variables(frame) -> dict[int, dict]:
        """Collect variables for each frame in the call stack.
        
        Returns a dict mapping frame index to variables dict.
        Frame index 0 is the oldest caller, last index is current frame.
        """
        frame_vars = {}
        
        # Walk up the frame chain to collect all frames in target file
        frames = []
        f = frame
        while f is not None:
            f_filename = os.path.abspath(f.f_code.co_filename)
            if f_filename == engine._target_file:
                frames.append(f)
            f = f.f_back
        
        # Reverse to get oldest first
        frames.reverse()
        
        # Map each frame to its index in the display stack
        # The display stack uses _call_stack for callers (excluding current)
        # So frame index i corresponds to caller_frames[i] for i < len(frames)-1
        
        for i, f in enumerate(frames[:-1]):  # Exclude current frame (last)
            frame_vars[i] = dict(f.f_locals)
        
        return frame_vars

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
            # Store the CALLER's info: the function that called us and the line where the call was made
            # This builds a chain: caller1 -> caller2 -> ... -> current function
            caller_frame = frame.f_back
            if caller_frame is not None:
                # Only track if caller is also in the target file
                caller_file = os.path.abspath(caller_frame.f_code.co_filename)
                if caller_file == engine._target_file:
                    engine._call_stack.append({
                        "func": caller_frame.f_code.co_name,
                        "file": os.path.basename(caller_frame.f_code.co_filename),
                        "line": caller_frame.f_lineno,  # The line where the call was made
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

            # Check if we should pause (step mode, regular breakpoint, or conditional breakpoint)
            should_pause = (
                engine._step_mode or 
                (lineno in engine._breakpoints) or
                _check_conditional_breakpoint(lineno, frame)
            )
            if not should_pause:
                return trace

            engine._steps_taken += 1
            
            # Build display stack
            display_stack = _build_display_stack(frame, lineno)
            
            # Use GUI or CLI based on engine setting
            if engine._use_gui:
                # Get or create GUI
                if engine._gui is None:
                    engine._gui = _get_gui()
                    # Wire up callbacks from GUI to engine
                    engine._gui.on_add_breakpoint = lambda line: engine._breakpoints.add(line)
                    engine._gui.on_remove_breakpoint = lambda line: engine._breakpoints.discard(line)
                    engine._gui.on_add_conditional_breakpoint = lambda line, cond: engine._conditional_breakpoints.update({line: cond})
                    engine._gui.on_remove_conditional_breakpoint = lambda line: engine._conditional_breakpoints.pop(line, None)
                    engine._gui.on_add_watch = lambda expr: engine._watches.append(expr) if expr not in engine._watches else None
                    engine._gui.on_remove_watch = lambda expr: engine._watches.remove(expr) if expr in engine._watches else None
                    engine._gui.on_set_context = lambda val: setattr(engine, '_context_lines', val)
                    engine._gui.on_set_stack_depth = lambda val: setattr(engine, '_stack_depth', val)
                
                # Collect frame variables for caller frames
                frame_variables = _collect_frame_variables(frame)
                
                # Show step in GUI and wait for user action
                action = engine._gui.show_step(
                    frame=frame,
                    lineno=lineno,
                    source_lines=engine._source_lines,
                    breakpoints=engine._breakpoints,
                    conditional_breakpoints=engine._conditional_breakpoints,
                    variables=frame.f_locals,
                    prev_variables=engine._prev_vars,
                    watches=engine._watches,
                    call_stack=display_stack,
                    context_lines=engine._context_lines,
                    stack_depth=engine._stack_depth,
                    frame_variables=frame_variables,
                )
                
                if action == "step":
                    engine._step_mode = True
                    engine._prev_vars = shallow_copy(frame.f_locals)
                    return trace
                elif action == "continue":
                    engine._step_mode = False
                    engine._prev_vars = shallow_copy(frame.f_locals)
                    return trace
                else:  # quit
                    engine.stop()
                    return None
            else:
                # CLI mode
                # Clear screen before showing next step
                if engine._clear_screen:
                    display.clear_screen()
                
                display.print_location(frame, lineno)
                display.print_call_stack(
                    display_stack, engine._source_lines, context=engine._context_lines
                )
                display.print_variables(frame.f_locals, engine._prev_vars, var_filter=engine._var_filter)
                display.print_watches(engine._watches, frame)

                if not handle_prompt(engine, frame, lineno):
                    return None

                engine._prev_vars = shallow_copy(frame.f_locals)
                return trace

        return trace

    return trace
