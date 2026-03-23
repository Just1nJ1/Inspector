"""
Python Inspector - Inline step-by-step code debugger.

Usage:
    Drop these lines anywhere in your code to inspect a region::

        import inspector
        inspector.start()   # tracing begins on the NEXT line
        ...
        inspector.stop()    # tracing ends here

    You can also pass options::

        inspector.start(step=True)   # pause every line (default)
        inspector.start(step=False)  # only pause at breakpoints
        inspector.start(gui=True)    # use Tkinter GUI instead of CLI

Commands while inspecting (CLI mode):
    [Enter] / n    - Step to next line
    c              - Continue running until next breakpoint or end
    b <line>       - Set a breakpoint at a line number
    bc <line> <cond> - Set conditional breakpoint (triggers when condition is true)
    rb <line>      - Remove a breakpoint at a line number
    rbc <line>     - Remove a conditional breakpoint
    p <expr>       - Evaluate and print an expression
    v              - Show all current variables
    filter <regex> - Filter variables by regex pattern
    filter off     - Clear variable filter
    watch <expr>   - Add a watch expression (shown at every step)
    unwatch <expr> - Remove a watch expression
    watches        - Show all current watches
    w              - Show call stack (where)
    context <n>    - Set number of source lines around current line
    stack <n>      - Set max number of stack frames to display
    clear / clear off - Toggle screen clearing on each step
    q              - Quit the inspector (continues execution normally)
    h              - Show help

GUI mode:
    When gui=True, a Tkinter window opens with:
    - Call stack panel (left) with source context for each frame
    - Source code panel (right) with current line highlighted
    - Variables panel (bottom left) with filter entry
    - Watches panel (bottom right)
    - Configuration and command areas
    - Control buttons: Step (n), Continue (c), Quit (q)
"""

from .engine import Inspector as _Inspector

_instance = _Inspector()


def start(step: bool = True, gui: bool = False):
    """Start the inspector from the calling line.

    Args:
        step: If True, pause every line. If False, only pause at breakpoints.
        gui: If True, use Tkinter GUI instead of command-line interface.

    Usage in your code::

        import inspector
        inspector.start()              # CLI mode
        inspector.start(gui=True)      # GUI mode
    """
    _instance.start(step=step, gui=gui)


def start_gui(step: bool = True):
    """Start the inspector with GUI mode enabled.

    Convenience function equivalent to start(step=step, gui=True).

    Usage in your code::

        import inspector
        inspector.start_gui()
    """
    _instance.start(step=step, gui=True)


def stop():
    """Stop the inspector.

    Usage in your code::

        inspector.stop()
    """
    _instance.stop()
