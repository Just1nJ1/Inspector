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

Commands while inspecting:
    [Enter] / n    - Step to next line
    c              - Continue running until next breakpoint or end
    b <line>       - Set a breakpoint at a line number
    rb <line>      - Remove a breakpoint at a line number
    p <expr>       - Evaluate and print an expression
    v              - Show all current variables
    watch <expr>   - Add a watch expression (shown at every step)
    unwatch <expr> - Remove a watch expression
    watches        - Show all current watches
    w              - Show call stack (where)
    q              - Quit the inspector (continues execution normally)
    h              - Show help
"""

from .engine import Inspector as _Inspector

_instance = _Inspector()


def start(step: bool = True):
    """Start the inspector from the calling line.

    Usage in your code::

        import inspector
        inspector.start()
    """
    _instance.start(step=step)


def stop():
    """Stop the inspector.

    Usage in your code::

        inspector.stop()
    """
    _instance.stop()
