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

        elif cmd.startswith("rb "):
            _cmd_bp_remove(engine, cmd)

        elif cmd.startswith("p "):
            _cmd_eval(cmd, frame)

        elif cmd in ("v", "vars"):
            display.print_variables(frame.f_locals, engine._prev_vars, force_all=True)

        elif cmd in ("w", "where"):
            display.print_call_stack(engine._call_stack)

        elif cmd.startswith("watch "):
            _cmd_watch_add(engine, cmd, frame)

        elif cmd.startswith("unwatch "):
            _cmd_watch_remove(engine, cmd)

        elif cmd == "watches":
            display.print_watches(engine._watches, frame)

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


def _cmd_bp_remove(engine, cmd: str):
    try:
        line = int(cmd.split()[1])
        engine._breakpoints.discard(line)
        print(f"  {C.GREEN}Breakpoint removed at line {line}{C.RESET}")
    except (IndexError, ValueError):
        print(f"  {C.RED}Usage: rb <line_number>{C.RESET}")


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
  |  rb <line>        Remove breakpoint at line    |
  |  p <expr>         Evaluate expression          |
  |  v                Show all variables           |
  |  watch <expr>     Add a watch expression       |
  |  unwatch <expr>   Remove a watch expression    |
  |  watches          Show all watches             |
  |  w                Show call stack              |
  |  q                Quit inspector               |
  |  h                Show this help               |
  +------------------------------------------------+""")
