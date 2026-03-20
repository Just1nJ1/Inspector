"""Display helpers -- all terminal printing for the inspector."""

import os

from .colors import Colors as C
from .utils import safe_repr, is_user_variable


def print_header(target_file: str):
    """Print the inspector banner when tracing starts."""
    bar = "\u2550" * 70
    fname = os.path.basename(target_file) if target_file else "?"
    print(f"\n{C.CYAN}{C.BOLD}{bar}")
    print(f"  Python Inspector  -  {fname}")
    print(f"{bar}{C.RESET}")
    print(
        f"{C.DIM}  Commands: [Enter]/n=step  c=continue  "
        f"b/rb=breakpoint  v=vars  q=quit  h=help{C.RESET}\n"
    )


def print_footer(steps_taken: int):
    """Print the inspector banner when tracing stops."""
    bar = "\u2550" * 70
    print(f"\n{C.CYAN}{C.BOLD}{bar}")
    print(f"  Inspector stopped  ({steps_taken} steps traced)")
    print(f"{bar}{C.RESET}\n")


def print_location(frame, lineno: int):
    """Print the current file / function / line label."""
    func = frame.f_code.co_name
    fname = os.path.basename(frame.f_code.co_filename)
    label = "<module>" if func == "<module>" else f"{func}()"
    print(f"{C.BLUE}{C.BOLD}-- {fname}  >  {label}  line {lineno} --{C.RESET}")


def print_source_context(
    source_lines: list[str],
    lineno: int,
    breakpoints: set[int],
    context: int = 3,
):
    """Print source code around *lineno* with a pointer arrow."""
    total = len(source_lines)
    start = max(1, lineno - context)
    end = min(total, lineno + context)
    for i in range(start, end + 1):
        line = source_lines[i - 1].rstrip("\n") if 1 <= i <= total else ""
        bp = f"{C.RED}*{C.RESET} " if i in breakpoints else "  "
        if i == lineno:
            print(f"  {bp}{C.YELLOW}{C.BOLD}-> {i:>4} | {line}{C.RESET}")
        else:
            print(f"  {bp}{C.DIM}   {i:>4} | {line}{C.RESET}")
    print()


def print_variables(
    local_vars: dict,
    prev_vars: dict,
    force_all: bool = False,
):
    """Print user variables, highlighting new / changed ones."""
    filtered = {k: v for k, v in local_vars.items() if is_user_variable(k, v)}
    if not filtered:
        if force_all:
            print(f"  {C.DIM}(no user variables){C.RESET}")
        return

    print(f"  {C.GREEN}{C.BOLD}Variables:{C.RESET}")
    for name in sorted(filtered):
        value = filtered[name]
        vrepr = safe_repr(value)
        if name not in prev_vars:
            tag = f"{C.MAGENTA}[new]{C.RESET} "
        elif prev_vars.get(name) != value:
            tag = f"{C.YELLOW}[changed]{C.RESET} "
        else:
            tag = ""
        type_name = type(value).__name__
        print(
            f"    {tag}{C.CYAN}{name}{C.RESET}"
            f" {C.DIM}({type_name}){C.RESET} = {vrepr}"
        )
    print()


def print_call_stack(call_stack: list[dict]):
    """Print the current call stack."""
    print(f"\n  {C.GREEN}{C.BOLD}Call Stack (most recent last):{C.RESET}")
    if not call_stack:
        print(f"    {C.DIM}(top level){C.RESET}")
    for i, entry in enumerate(call_stack):
        indent = "    " * (i + 1)
        print(
            f"  {indent}-> {C.CYAN}{entry['func']}{C.RESET} "
            f"at {entry['file']}:{entry['line']}"
        )
    print()


def print_watches(watches: list[str], frame):
    """Evaluate and display all watched expressions."""
    if not watches:
        return
    print(f"  {C.YELLOW}{C.BOLD}Watches:{C.RESET}")
    for expr in watches:
        try:
            result = eval(expr, frame.f_globals, frame.f_locals)
            print(f"    {C.CYAN}{expr}{C.RESET} = {safe_repr(result)}")
        except Exception as exc:
            print(f"    {C.CYAN}{expr}{C.RESET} = {C.RED}<error: {exc}>{C.RESET}")
    print()
