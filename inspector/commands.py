"""Interactive command handlers for the inspector prompt."""

from .colors import Colors as C
from .utils import safe_repr
from . import display


def handle_prompt(engine, frame, lineno: int) -> bool:
    """Show the prompt and dispatch commands.

    Returns ``True`` to keep tracing, ``False`` to stop.
    *engine* is the ``_Inspector`` instance so commands can mutate its state.
    """
    while True:
        try:
            cmd = input(f"{C.BOLD}inspect > {C.RESET}").strip()
        except (EOFError, KeyboardInterrupt):
            print()
            engine.stop()
            return False

        if cmd in ("", "n", "next"):
            engine._step_mode = True
            return True

        elif cmd in ("c", "continue"):
            engine._step_mode = False
            return True

        elif cmd.startswith("b "):
            _cmd_bp_add(engine, cmd)

        elif cmd.startswith("bc "):
            _cmd_bp_conditional_add(engine, cmd)

        elif cmd.startswith("rb "):
            _cmd_bp_remove(engine, cmd)

        elif cmd.startswith("rbc "):
            _cmd_bp_conditional_remove(engine, cmd)

        elif cmd.startswith("p "):
            _cmd_eval(cmd, frame)

        elif cmd in ("v", "vars"):
            display.print_variables(frame.f_locals, engine._prev_vars, force_all=True)

        elif cmd in ("w", "where"):
            # Build display stack with current frame info
            import os as _os
            display_stack = list(engine._call_stack)
            display_stack.append({
                "func": frame.f_code.co_name,
                "file": _os.path.basename(frame.f_code.co_filename),
                "line": lineno,
            })
            display.print_call_stack(
                display_stack, engine._source_lines, context=engine._context_lines
            )

        elif cmd.startswith("watch "):
            _cmd_watch_add(engine, cmd, frame)

        elif cmd.startswith("unwatch "):
            _cmd_watch_remove(engine, cmd)

        elif cmd == "watches":
            display.print_watches(engine._watches, frame)

        elif cmd.startswith("context "):
            _cmd_set_context(engine, cmd)

        elif cmd.startswith("stack "):
            _cmd_set_stack_depth(engine, cmd)

        elif cmd in ("clear", "clear on"):
            engine._clear_screen = True
            print(f"  {C.GREEN}Screen clearing enabled{C.RESET}")

        elif cmd in ("clear off",):
            engine._clear_screen = False
            print(f"  {C.GREEN}Screen clearing disabled{C.RESET}")

        elif cmd.startswith("filter "):
            _cmd_set_filter(engine, cmd)

        elif cmd in ("filter off", "filter"):
            engine._var_filter = None
            print(f"  {C.GREEN}Variable filter cleared{C.RESET}")

        elif cmd in ("q", "quit"):
            engine.stop()
            return False

        elif cmd in ("h", "help"):
            _cmd_help()

        else:
            print(f"  {C.RED}Unknown command. Type 'h' for help.{C.RESET}")


# ── individual command implementations ───────────────────────────────────────

def _cmd_bp_add(engine, cmd: str):
    try:
        line = int(cmd.split()[1])
        engine._breakpoints.add(line)
        print(f"  {C.GREEN}Breakpoint set at line {line}{C.RESET}")
    except (IndexError, ValueError):
        print(f"  {C.RED}Usage: b <line_number>{C.RESET}")


def _cmd_bp_conditional_add(engine, cmd: str):
    """Add a conditional breakpoint: bc <line> <condition>"""
    try:
        parts = cmd.split(None, 2)  # Split into max 3 parts: bc, line, condition
        if len(parts) < 3:
            print(f"  {C.RED}Usage: bc <line_number> <condition>{C.RESET}")
            return
        line = int(parts[1])
        condition = parts[2]
        engine._conditional_breakpoints[line] = condition
        print(f"  {C.GREEN}Conditional breakpoint set at line {line}: {condition}{C.RESET}")
    except (IndexError, ValueError):
        print(f"  {C.RED}Usage: bc <line_number> <condition>{C.RESET}")


def _cmd_bp_remove(engine, cmd: str):
    try:
        line = int(cmd.split()[1])
        engine._breakpoints.discard(line)
        print(f"  {C.GREEN}Breakpoint removed at line {line}{C.RESET}")
    except (IndexError, ValueError):
        print(f"  {C.RED}Usage: rb <line_number>{C.RESET}")


def _cmd_bp_conditional_remove(engine, cmd: str):
    """Remove a conditional breakpoint: rbc <line>"""
    try:
        line = int(cmd.split()[1])
        if line in engine._conditional_breakpoints:
            del engine._conditional_breakpoints[line]
            print(f"  {C.GREEN}Conditional breakpoint removed at line {line}{C.RESET}")
        else:
            print(f"  {C.RED}No conditional breakpoint at line {line}{C.RESET}")
    except (IndexError, ValueError):
        print(f"  {C.RED}Usage: rbc <line_number>{C.RESET}")


def _cmd_watch_add(engine, cmd: str, frame):
    expr = cmd[len("watch "):].strip()
    if not expr:
        print(f"  {C.RED}Usage: watch <expression>{C.RESET}")
        return
    if expr in engine._watches:
        print(f"  {C.DIM}Already watching: {expr}{C.RESET}")
        return
    engine._watches.append(expr)
    try:
        result = eval(expr, frame.f_globals, frame.f_locals)
        print(f"  {C.GREEN}Watching:{C.RESET} {C.CYAN}{expr}{C.RESET} = {safe_repr(result)}")
    except Exception as exc:
        print(f"  {C.GREEN}Watching:{C.RESET} {C.CYAN}{expr}{C.RESET} = {C.RED}<error: {exc}>{C.RESET}")


def _cmd_watch_remove(engine, cmd: str):
    expr = cmd[len("unwatch "):].strip()
    if not expr:
        print(f"  {C.RED}Usage: unwatch <expression>{C.RESET}")
        return
    if expr in engine._watches:
        engine._watches.remove(expr)
        print(f"  {C.GREEN}Removed watch: {expr}{C.RESET}")
    else:
        print(f"  {C.RED}Not watching: {expr}{C.RESET}")
        if engine._watches:
            print(f"  {C.DIM}Current watches: {', '.join(engine._watches)}{C.RESET}")


def _cmd_set_context(engine, cmd: str):
    """Set the number of context lines around current line: context <n>"""
    try:
        n = int(cmd.split()[1])
        if n < 0:
            print(f"  {C.RED}Context must be non-negative{C.RESET}")
            return
        engine._context_lines = n
        print(f"  {C.GREEN}Context lines set to {n}{C.RESET}")
    except (IndexError, ValueError):
        print(f"  {C.RED}Usage: context <number>{C.RESET}")


def _cmd_set_stack_depth(engine, cmd: str):
    """Set the max number of stack frames to display: stack <n>"""
    try:
        n = int(cmd.split()[1])
        if n < 1:
            print(f"  {C.RED}Stack depth must be at least 1{C.RESET}")
            return
        engine._stack_depth = n
        print(f"  {C.GREEN}Stack depth set to {n}{C.RESET}")
    except (IndexError, ValueError):
        print(f"  {C.RED}Usage: stack <number>{C.RESET}")


def _cmd_set_filter(engine, cmd: str):
    """Set variable filter regex: filter <regex>"""
    import re
    try:
        pattern = cmd.split(None, 1)[1]
        if not pattern:
            print(f"  {C.RED}Usage: filter <regex>{C.RESET}")
            return
        try:
            engine._var_filter = re.compile(pattern)
            print(f"  {C.GREEN}Variable filter set to: {pattern}{C.RESET}")
        except re.error as e:
            print(f"  {C.RED}Invalid regex: {e}{C.RESET}")
    except (IndexError, ValueError):
        print(f"  {C.RED}Usage: filter <regex>{C.RESET}")


def _cmd_eval(cmd: str, frame):
    expr = cmd[2:].strip()
    try:
        result = eval(expr, frame.f_globals, frame.f_locals)
        print(f"  {C.CYAN}{expr}{C.RESET} = {safe_repr(result, 200)}")
    except Exception as exc:
        print(f"  {C.RED}Error: {exc}{C.RESET}")


def _cmd_help():
    print("""
  +------------------------------------------------+
  |  Inspector Commands                            |
  +------------------------------------------------+
  |  [Enter] / n      Step to next line            |
  |  c                Continue to next breakpoint  |
  |  b <line>         Set breakpoint at line       |
  |  bc <line> <cond> Set conditional breakpoint   |
  |  rb <line>        Remove breakpoint at line    |
  |  rbc <line>       Remove conditional bp        |
  |  p <expr>         Evaluate expression          |
  |  v                Show all variables           |
  |  filter <regex>   Filter variables by regex    |
  |  filter off       Clear variable filter        |
  |  watch <expr>     Add a watch expression       |
  |  unwatch <expr>   Remove a watch expression    |
  |  watches          Show all watches             |
  |  w                Show call stack              |
  |  context <n>      Set source context lines     |
  |  stack <n>        Set max stack frames         |
  |  clear / clear off Toggle screen clear        |
  |  q                Quit inspector               |
  |  h                Show this help               |
  +------------------------------------------------+""")
