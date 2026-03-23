"""Tkinter GUI for the Python Inspector."""

import tkinter as tk
from tkinter import ttk, scrolledtext, messagebox
from typing import Optional, Callable


class InspectorGUI:
    """Tkinter-based GUI for the Python Inspector."""

    def __init__(self):
        self.root: Optional[tk.Tk] = None
        self.result: Optional[str] = None  # User's action: 'step', 'continue', 'quit'
        
        # UI components
        self.current_frame_text: Optional[scrolledtext.ScrolledText] = None
        self.call_stack_text: Optional[scrolledtext.ScrolledText] = None
        self.variables_text: Optional[scrolledtext.ScrolledText] = None
        self.watches_text: Optional[scrolledtext.ScrolledText] = None
        self.location_label: Optional[tk.Label] = None
        self.command_entry: Optional[tk.Entry] = None
        self.context_spinbox: Optional[tk.Spinbox] = None
        self.stack_spinbox: Optional[tk.Spinbox] = None
        self.output_text: Optional[scrolledtext.ScrolledText] = None
        
        # Current state
        self.current_frame = None
        self.current_lineno = 0
        self.source_lines: list[str] = []
        self.breakpoints: set[int] = set()
        self.conditional_breakpoints: dict[int, str] = {}
        self.variables: dict = {}
        self.prev_variables: dict = {}
        self.watches: list[str] = []
        self.call_stack: list[dict] = []
        self.context_lines: int = 3
        self.stack_depth: int = 10
        
        # Expanded frame index in call stack (-1 means none, -2 means most recent caller)
        self.expanded_frame_index: int = -2
        
        # Track which line in call_stack_text corresponds to which frame index
        # Maps frame index -> list of line numbers in the text widget
        self._frame_line_ranges: dict[int, tuple[int, int]] = {}
        
        # Variables for each frame (stored by frame index)
        self._frame_variables: dict[int, dict] = {}
        
        # Which frame's variables are currently displayed (-1 = current frame)
        self._displayed_variables_frame: int = -1
        
        # Variable filter regex pattern (None means no filter)
        self._var_filter = None
        
        # Callbacks for engine actions
        self.on_add_breakpoint: Optional[Callable] = None
        self.on_remove_breakpoint: Optional[Callable] = None
        self.on_add_conditional_breakpoint: Optional[Callable] = None
        self.on_remove_conditional_breakpoint: Optional[Callable] = None
        self.on_add_watch: Optional[Callable] = None
        self.on_remove_watch: Optional[Callable] = None
        self.on_set_context: Optional[Callable] = None
        self.on_set_stack_depth: Optional[Callable] = None

    def _create_window(self):
        """Create the main window and all UI components."""
        self.root = tk.Tk()
        self.root.title("Python Inspector")
        self.root.geometry("1400x900")
        
        # Top frame: Location label
        top_frame = ttk.Frame(self.root)
        top_frame.pack(fill=tk.X, padx=5, pady=5)
        
        self.location_label = ttk.Label(
            top_frame, text="-- Location --", font=("Arial", 12, "bold")
        )
        self.location_label.pack(anchor=tk.W)
        
        # Upper frame: Two panels side by side - Current Frame and Call Stack
        upper_frame = ttk.Frame(self.root)
        upper_frame.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)
        
        # Left: Current Frame (source context for current line)
        current_frame = ttk.LabelFrame(upper_frame, text="Current Frame (click to show current vars)")
        current_frame.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=(0, 2))
        
        self.current_frame_text = scrolledtext.ScrolledText(
            current_frame, wrap=tk.NONE, font=("Courier", 10), height=25
        )
        self.current_frame_text.pack(fill=tk.BOTH, expand=True)
        self.current_frame_text.config(state=tk.DISABLED)
        
        # Configure text tags for current frame
        self.current_frame_text.tag_configure("current", background="yellow", foreground="black")
        self.current_frame_text.tag_configure("header", font=("Courier", 10, "bold"))
        self.current_frame_text.tag_configure("dim", foreground="gray")
        
        # Bind click on current frame to show current variables
        self.current_frame_text.bind("<Button-1>", self._on_current_frame_click)
        
        # Right: Call Stack (clickable, expandable frames)
        call_stack_frame = ttk.LabelFrame(upper_frame, text="Call Stack (click to expand)")
        call_stack_frame.pack(side=tk.RIGHT, fill=tk.BOTH, expand=True, padx=(2, 0))
        
        self.call_stack_text = scrolledtext.ScrolledText(
            call_stack_frame, wrap=tk.NONE, font=("Courier", 10), height=25
        )
        self.call_stack_text.pack(fill=tk.BOTH, expand=True)
        self.call_stack_text.config(state=tk.DISABLED)
        
        # Configure text tags for call stack
        self.call_stack_text.tag_configure("expanded_header", font=("Courier", 10, "bold"), foreground="cyan")
        self.call_stack_text.tag_configure("collapsed_header", font=("Courier", 10, "underline"), foreground="blue")
        self.call_stack_text.tag_configure("dim", foreground="gray")
        self.call_stack_text.tag_configure("highlight", background="lightcyan", foreground="black")
        
        # Bind click event for call stack
        self.call_stack_text.bind("<Button-1>", self._on_call_stack_click)
        
        # Middle frame: Variables and Watches
        middle_frame = ttk.Frame(self.root)
        middle_frame.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)
        
        # Variables panel
        var_frame = ttk.LabelFrame(middle_frame, text="Variables")
        var_frame.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=(0, 2))
        
        # Filter row
        filter_row = ttk.Frame(var_frame)
        filter_row.pack(fill=tk.X, padx=2, pady=2)
        ttk.Label(filter_row, text="Filter:").pack(side=tk.LEFT)
        self.var_filter_entry = ttk.Entry(filter_row, width=20)
        self.var_filter_entry.pack(side=tk.LEFT, padx=2, fill=tk.X, expand=True)
        self.var_filter_entry.bind("<Return>", self._on_var_filter_apply)
        ttk.Button(filter_row, text="Apply", command=self._on_var_filter_apply, width=6).pack(side=tk.LEFT, padx=2)
        ttk.Button(filter_row, text="Clear", command=self._on_var_filter_clear, width=6).pack(side=tk.LEFT)
        
        self.variables_text = scrolledtext.ScrolledText(
            var_frame, wrap=tk.WORD, font=("Courier", 10), height=10
        )
        self.variables_text.pack(fill=tk.BOTH, expand=True)
        self.variables_text.config(state=tk.DISABLED)
        
        self.variables_text.tag_configure("new", foreground="magenta")
        self.variables_text.tag_configure("changed", foreground="orange")
        
        # Watches panel
        watch_frame = ttk.LabelFrame(middle_frame, text="Watches")
        watch_frame.pack(side=tk.RIGHT, fill=tk.BOTH, expand=True, padx=(2, 0))
        
        self.watches_text = scrolledtext.ScrolledText(
            watch_frame, wrap=tk.WORD, font=("Courier", 10), height=10
        )
        self.watches_text.pack(fill=tk.BOTH, expand=True)
        self.watches_text.config(state=tk.DISABLED)
        
        # Lower frame: Config and Command
        lower_frame = ttk.Frame(self.root)
        lower_frame.pack(fill=tk.X, padx=5, pady=5)
        
        # Config frame
        config_frame = ttk.LabelFrame(lower_frame, text="Configuration")
        config_frame.pack(side=tk.LEFT, fill=tk.X, padx=(0, 5))
        
        # Context lines
        ctx_frame = ttk.Frame(config_frame)
        ctx_frame.pack(side=tk.LEFT, padx=5, pady=5)
        ttk.Label(ctx_frame, text="Context lines:").pack(side=tk.LEFT)
        self.context_spinbox = ttk.Spinbox(ctx_frame, from_=0, to=20, width=5)
        self.context_spinbox.pack(side=tk.LEFT, padx=2)
        self.context_spinbox.delete(0, tk.END)
        self.context_spinbox.insert(0, str(self.context_lines))
        ttk.Button(ctx_frame, text="Set", command=self._on_set_context, width=5).pack(side=tk.LEFT, padx=2)
        
        # Stack depth
        stack_frame = ttk.Frame(config_frame)
        stack_frame.pack(side=tk.LEFT, padx=5, pady=5)
        ttk.Label(stack_frame, text="Stack depth:").pack(side=tk.LEFT)
        self.stack_spinbox = ttk.Spinbox(stack_frame, from_=1, to=50, width=5)
        self.stack_spinbox.pack(side=tk.LEFT, padx=2)
        self.stack_spinbox.delete(0, tk.END)
        self.stack_spinbox.insert(0, str(self.stack_depth))
        ttk.Button(stack_frame, text="Set", command=self._on_set_stack_depth, width=5).pack(side=tk.LEFT, padx=2)
        
        # Command frame
        cmd_frame = ttk.LabelFrame(lower_frame, text="Command")
        cmd_frame.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=5)
        
        cmd_inner = ttk.Frame(cmd_frame)
        cmd_inner.pack(fill=tk.X, padx=5, pady=5)
        
        ttk.Label(cmd_inner, text="Command:").pack(side=tk.LEFT)
        self.command_entry = ttk.Entry(cmd_inner, width=50)
        self.command_entry.pack(side=tk.LEFT, padx=5, fill=tk.X, expand=True)
        self.command_entry.bind("<Return>", self._on_execute_command)
        ttk.Button(cmd_inner, text="Execute", command=self._on_execute_command, width=8).pack(side=tk.LEFT, padx=2)
        
        # Output area for command results
        output_frame = ttk.Frame(cmd_frame)
        output_frame.pack(fill=tk.X, padx=5, pady=(0, 5))
        
        self.output_text = scrolledtext.ScrolledText(
            output_frame, wrap=tk.WORD, font=("Courier", 9), height=3
        )
        self.output_text.pack(fill=tk.X)
        self.output_text.config(state=tk.DISABLED)
        
        # Bottom frame: Control buttons
        controls_frame = ttk.Frame(self.root)
        controls_frame.pack(fill=tk.X, padx=5, pady=5)
        
        # Buttons
        self.step_btn = ttk.Button(
            controls_frame, text="Step (n)", command=self._on_step, width=12
        )
        self.step_btn.pack(side=tk.LEFT, padx=2)
        
        self.continue_btn = ttk.Button(
            controls_frame, text="Continue (c)", command=self._on_continue, width=12
        )
        self.continue_btn.pack(side=tk.LEFT, padx=2)
        
        self.quit_btn = ttk.Button(
            controls_frame, text="Quit (q)", command=self._on_quit, width=12
        )
        self.quit_btn.pack(side=tk.LEFT, padx=2)
        
        # Help label
        help_text = "Commands: b <line> | bc <line> <cond> | rb <line> | rbc <line> | watch <expr> | unwatch <expr> | p <expr>"
        ttk.Label(controls_frame, text=help_text, foreground="gray").pack(side=tk.RIGHT, padx=5)
        
        # Keyboard shortcuts (only when not in entry field)
        self.root.bind("<n>", self._on_key_step)
        self.root.bind("<c>", self._on_key_continue)
        self.root.bind("<q>", self._on_key_quit)
        self.root.bind("<Escape>", lambda e: self.command_entry.focus_set())
        
        # Protocol for window close
        self.root.protocol("WM_DELETE_WINDOW", self._on_quit)
        
        # Focus on command entry
        self.command_entry.focus_set()

    def _on_current_frame_click(self, event):
        """Handle click on current frame to show current frame variables."""
        self._displayed_variables_frame = -1
        self._update_variables()
        self._output("Showing current frame variables\n")

    def _on_call_stack_click(self, event):
        """Handle click on call stack to expand/collapse frames."""
        if not self.call_stack_text or not self.call_stack:
            return
        
        # Get the line number clicked (1-indexed in Tkinter text widget)
        try:
            click_index = self.call_stack_text.index(f"@{event.x},{event.y}")
            click_line = int(float(click_index.split('.')[0]))
        except:
            return
        
        # Find which frame this click corresponds to
        for frame_idx, (start_line, end_line) in self._frame_line_ranges.items():
            if start_line <= click_line <= end_line:
                # Found the frame - toggle expansion
                if self.expanded_frame_index == frame_idx:
                    # Already expanded, collapse it
                    self.expanded_frame_index = -2
                else:
                    # Expand this frame and show its variables
                    self.expanded_frame_index = frame_idx
                    self._displayed_variables_frame = frame_idx
                    self._update_variables()
                self._update_call_stack()
                return

    def _on_key_step(self, event):
        """Handle 'n' key for step."""
        if self.root.focus_get() != self.command_entry:
            self._on_step()

    def _on_key_continue(self, event):
        """Handle 'c' key for continue."""
        if self.root.focus_get() != self.command_entry:
            self._on_continue()

    def _on_key_quit(self, event):
        """Handle 'q' key for quit."""
        if self.root.focus_get() != self.command_entry:
            self._on_quit()

    def _on_step(self):
        """Handle Step button click."""
        self.result = "step"
        self.root.quit()

    def _on_continue(self):
        """Handle Continue button click."""
        self.result = "continue"
        self.root.quit()

    def _on_quit(self):
        """Handle Quit button click."""
        self.result = "quit"
        self.root.quit()

    def _on_set_context(self):
        """Handle Set context button."""
        try:
            value = int(self.context_spinbox.get())
            if value < 0:
                self._output("Error: Context must be non-negative\n")
                return
            self.context_lines = value
            if self.on_set_context:
                self.on_set_context(value)
            self._output(f"Context lines set to {value}\n")
            self._update_current_frame()
            self._update_call_stack()
        except ValueError:
            self._output("Error: Invalid number\n")

    def _on_set_stack_depth(self):
        """Handle Set stack depth button."""
        try:
            value = int(self.stack_spinbox.get())
            if value < 1:
                self._output("Error: Stack depth must be at least 1\n")
                return
            self.stack_depth = value
            if self.on_set_stack_depth:
                self.on_set_stack_depth(value)
            self._output(f"Stack depth set to {value}\n")
            self._update_call_stack()
        except ValueError:
            self._output("Error: Invalid number\n")

    def _on_var_filter_apply(self, event=None):
        """Handle Apply filter button."""
        import re
        pattern = self.var_filter_entry.get().strip()
        if not pattern:
            self._on_var_filter_clear()
            return
        try:
            self._var_filter = re.compile(pattern)
            self._output(f"Variable filter set to: {pattern}\n")
            self._update_variables()
        except re.error as e:
            self._output(f"Invalid regex: {e}\n")

    def _on_var_filter_clear(self):
        """Handle Clear filter button."""
        self.var_filter_entry.delete(0, tk.END)
        self._var_filter = None
        self._output("Variable filter cleared\n")
        self._update_variables()

    def _on_execute_command(self, event=None):
        """Execute command from entry field."""
        cmd = self.command_entry.get().strip()
        if not cmd:
            return
        
        self.command_entry.delete(0, tk.END)
        self._output(f"> {cmd}\n")
        
        try:
            if cmd.startswith("b "):
                # Add breakpoint
                line = int(cmd[2:].strip())
                self.breakpoints.add(line)
                if self.on_add_breakpoint:
                    self.on_add_breakpoint(line)
                self._output(f"Breakpoint set at line {line}\n")
                self._update_current_frame()
                self._update_call_stack()
            
            elif cmd.startswith("bc "):
                # Add conditional breakpoint
                parts = cmd[3:].strip().split(None, 1)
                if len(parts) < 2:
                    self._output("Usage: bc <line> <condition>\n")
                    return
                line = int(parts[0])
                condition = parts[1]
                self.conditional_breakpoints[line] = condition
                if self.on_add_conditional_breakpoint:
                    self.on_add_conditional_breakpoint(line, condition)
                self._output(f"Conditional breakpoint set at line {line}: {condition}\n")
                self._update_current_frame()
                self._update_call_stack()
            
            elif cmd.startswith("rb "):
                # Remove breakpoint
                line = int(cmd[3:].strip())
                self.breakpoints.discard(line)
                if self.on_remove_breakpoint:
                    self.on_remove_breakpoint(line)
                self._output(f"Breakpoint removed at line {line}\n")
                self._update_current_frame()
                self._update_call_stack()
            
            elif cmd.startswith("rbc "):
                # Remove conditional breakpoint
                line = int(cmd[4:].strip())
                if line in self.conditional_breakpoints:
                    del self.conditional_breakpoints[line]
                    if self.on_remove_conditional_breakpoint:
                        self.on_remove_conditional_breakpoint(line)
                    self._output(f"Conditional breakpoint removed at line {line}\n")
                    self._update_current_frame()
                    self._update_call_stack()
                else:
                    self._output(f"No conditional breakpoint at line {line}\n")
            
            elif cmd.startswith("watch "):
                # Add watch
                expr = cmd[6:].strip()
                if expr and expr not in self.watches:
                    self.watches.append(expr)
                    if self.on_add_watch:
                        self.on_add_watch(expr)
                    self._output(f"Watching: {expr}\n")
                    self._update_watches()
                elif expr in self.watches:
                    self._output(f"Already watching: {expr}\n")
            
            elif cmd.startswith("unwatch "):
                # Remove watch
                expr = cmd[8:].strip()
                if expr in self.watches:
                    self.watches.remove(expr)
                    if self.on_remove_watch:
                        self.on_remove_watch(expr)
                    self._output(f"Removed watch: {expr}\n")
                    self._update_watches()
                else:
                    self._output(f"Not watching: {expr}\n")
            
            elif cmd.startswith("p "):
                # Evaluate expression
                expr = cmd[2:].strip()
                try:
                    result = eval(expr, self.current_frame.f_globals, self.current_frame.f_locals)
                    self._output(f"{expr} = {repr(result)}\n")
                except Exception as exc:
                    self._output(f"Error: {exc}\n")
            
            elif cmd in ("h", "help"):
                self._output("""Commands:
  b <line>         - Set breakpoint at line
  bc <line> <cond> - Set conditional breakpoint
  rb <line>        - Remove breakpoint at line
  rbc <line>       - Remove conditional breakpoint
  watch <expr>     - Add watch expression
  unwatch <expr>   - Remove watch expression
  p <expr>         - Evaluate and print expression
  h                - Show this help
""")
            
            else:
                self._output(f"Unknown command: {cmd}. Type 'h' for help.\n")
        
        except Exception as exc:
            self._output(f"Error: {exc}\n")

    def _output(self, text: str):
        """Append text to output area."""
        if not self.output_text:
            return
        self.output_text.config(state=tk.NORMAL)
        self.output_text.delete(1.0, tk.END)
        self.output_text.insert(tk.END, text)
        self.output_text.config(state=tk.DISABLED)

    def _update_current_frame(self):
        """Update the current frame display with source context."""
        if not self.current_frame_text:
            return
            
        self.current_frame_text.config(state=tk.NORMAL)
        self.current_frame_text.delete(1.0, tk.END)
        
        if not self.call_stack:
            self.current_frame_text.insert(tk.END, "  (no current frame)\n")
        else:
            # Get the current frame (last in call_stack)
            current_entry = self.call_stack[-1]
            func_name = current_entry['func']
            if func_name == "<module>":
                func_name = "<module>"
            else:
                func_name = f"{func_name}()"
            
            lineno = current_entry['line']
            fname = current_entry['file']
            
            # Print frame header
            self.current_frame_text.insert(tk.END, f"  {func_name}", "header")
            self.current_frame_text.insert(tk.END, f" ({fname}:{lineno})\n\n", "dim")
            
            # Print source context around current line
            total = len(self.source_lines)
            start = max(1, lineno - self.context_lines)
            end = min(total, lineno + self.context_lines)
            
            for j in range(start, end + 1):
                line = self.source_lines[j - 1].rstrip("\n") if 1 <= j <= total else ""
                
                # Determine marker
                if j in self.conditional_breakpoints:
                    marker = "C "
                elif j in self.breakpoints:
                    marker = "* "
                else:
                    marker = "  "
                
                if j == lineno:
                    # Current line - highlight
                    self.current_frame_text.insert(tk.END, f"  {marker}-> {j:>4} | {line}\n", "current")
                else:
                    self.current_frame_text.insert(tk.END, f"  {marker}   {j:>4} | {line}\n", "dim")
        
        self.current_frame_text.config(state=tk.DISABLED)

    def _update_call_stack(self):
        """Update the call stack display with expandable frames."""
        if not self.call_stack_text:
            return
            
        self.call_stack_text.config(state=tk.NORMAL)
        self.call_stack_text.delete(1.0, tk.END)
        
        # Clear line ranges
        self._frame_line_ranges = {}
        
        # Only show caller frames (exclude current frame which is last)
        caller_frames = self.call_stack[:-1] if len(self.call_stack) > 1 else []
        
        if not caller_frames:
            self.call_stack_text.insert(tk.END, "  (no caller frames)\n")
        else:
            total = len(self.source_lines)
            
            # Determine which frame is expanded
            # -2 means the most recent caller (second to last in call_stack)
            expanded_idx = self.expanded_frame_index
            if expanded_idx == -2 or expanded_idx >= len(caller_frames):
                expanded_idx = len(caller_frames) - 1  # Most recent caller
            
            for i, entry in enumerate(caller_frames):
                # Track the starting line of this frame in the text widget
                start_line = int(float(self.call_stack_text.index(tk.END + "-1c linestart").split('.')[0]))
                if start_line == 1 and self.call_stack_text.get("1.0", "1.1") == "\n":
                    start_line = 1
                
                func_name = entry['func']
                if func_name == "<module>":
                    func_name = "<module>"
                else:
                    func_name = f"{func_name}()"
                
                lineno = entry['line']
                fname = entry['file']
                
                is_expanded = (i == expanded_idx)
                
                # Print frame header (clickable)
                if is_expanded:
                    self.call_stack_text.insert(tk.END, f"▸ {func_name}", "expanded_header")
                    self.call_stack_text.insert(tk.END, f" at {fname}:{lineno}\n", "dim")
                else:
                    self.call_stack_text.insert(tk.END, f"  {func_name}", "collapsed_header")
                    self.call_stack_text.insert(tk.END, f" at {fname}:{lineno}\n", "dim")
                
                # If expanded, show source context
                if is_expanded:
                    start = max(1, lineno - self.context_lines)
                    end = min(total, lineno + self.context_lines)
                    
                    for j in range(start, end + 1):
                        line = self.source_lines[j - 1].rstrip("\n") if 1 <= j <= total else ""
                        
                        # Determine marker
                        if j in self.conditional_breakpoints:
                            marker = "C "
                        elif j in self.breakpoints:
                            marker = "* "
                        else:
                            marker = "  "
                        
                        if j == lineno:
                            # Highlight the relevant line
                            self.call_stack_text.insert(tk.END, f"    {marker}-> {j:>4} | {line}\n", "highlight")
                        else:
                            self.call_stack_text.insert(tk.END, f"    {marker}   {j:>4} | {line}\n", "dim")
                    
                    self.call_stack_text.insert(tk.END, "\n")
                
                # Track the ending line of this frame
                end_line = int(float(self.call_stack_text.index(tk.END + "-1c linestart").split('.')[0]))
                self._frame_line_ranges[i] = (start_line, end_line)
        
        self.call_stack_text.config(state=tk.DISABLED)

    def _update_location(self):
        """Update the location label."""
        if not self.location_label:
            return
            
        if self.current_frame:
            func = self.current_frame.f_code.co_name
            fname = self.current_frame.f_code.co_filename.split("/")[-1]
            label = "<module>" if func == "<module>" else f"{func}()"
            self.location_label.config(text=f"-- {fname} > {label} line {self.current_lineno} --")

    def _update_variables(self):
        """Update the variables display for the selected frame."""
        if not self.variables_text:
            return
            
        self.variables_text.config(state=tk.NORMAL)
        self.variables_text.delete(1.0, tk.END)
        
        # Determine which variables to show
        if self._displayed_variables_frame == -1 or self._displayed_variables_frame not in self._frame_variables:
            # Show current frame variables
            vars_to_show = self.variables
            prev_vars = self.prev_variables
            frame_label = "current frame"
        else:
            # Show caller frame variables
            vars_to_show = self._frame_variables.get(self._displayed_variables_frame, {})
            prev_vars = {}  # No change tracking for caller frames
            frame_label = f"frame #{self._displayed_variables_frame}"
        
        import types
        import re
        
        filtered = {k: v for k, v in vars_to_show.items() 
                    if not (k.startswith("__") and k.endswith("__")) and 
                       not isinstance(v, (types.ModuleType, types.FunctionType, type))}
        
        # Apply variable filter if set
        if self._var_filter is not None:
            filtered = {k: v for k, v in filtered.items() if self._var_filter.search(k)}
        
        # Show which frame's variables with filter indicator
        if self._var_filter is not None:
            filter_str = self._var_filter.pattern
            self.variables_text.insert(tk.END, f"  [{frame_label}] (filter: {filter_str})\n", "new")
        else:
            self.variables_text.insert(tk.END, f"  [{frame_label}]\n", "new")
        
        if not filtered:
            if self._var_filter is not None:
                self.variables_text.insert(tk.END, "  (no variables match filter)\n")
            else:
                self.variables_text.insert(tk.END, "  (no user variables)\n")
        else:
            for name in sorted(filtered):
                value = filtered[name]
                try:
                    vrepr = repr(value)
                    if len(vrepr) > 80:
                        vrepr = vrepr[:77] + "..."
                except:
                    vrepr = "<unrepresentable>"
                
                type_name = type(value).__name__
                
                if prev_vars and name not in prev_vars:
                    self.variables_text.insert(tk.END, f"  [new] {name} ({type_name}) = {vrepr}\n", "new")
                elif prev_vars and prev_vars.get(name) != value:
                    self.variables_text.insert(tk.END, f"  [changed] {name} ({type_name}) = {vrepr}\n", "changed")
                else:
                    self.variables_text.insert(tk.END, f"  {name} ({type_name}) = {vrepr}\n")
        
        self.variables_text.config(state=tk.DISABLED)

    def _update_watches(self):
        """Update the watches display."""
        if not self.watches_text:
            return
            
        self.watches_text.config(state=tk.NORMAL)
        self.watches_text.delete(1.0, tk.END)
        
        if not self.watches:
            self.watches_text.insert(tk.END, "  (no watches)\n")
        else:
            for expr in self.watches:
                try:
                    result = eval(expr, self.current_frame.f_globals, self.current_frame.f_locals)
                    try:
                        vrepr = repr(result)
                        if len(vrepr) > 60:
                            vrepr = vrepr[:57] + "..."
                    except:
                        vrepr = "<unrepresentable>"
                    self.watches_text.insert(tk.END, f"  {expr} = {vrepr}\n")
                except Exception as exc:
                    self.watches_text.insert(tk.END, f"  {expr} = <error: {exc}>\n")
        
        self.watches_text.config(state=tk.DISABLED)

    def show_step(
        self,
        frame,
        lineno: int,
        source_lines: list[str],
        breakpoints: set[int],
        conditional_breakpoints: dict[int, str],
        variables: dict,
        prev_variables: dict,
        watches: list[str],
        call_stack: list[dict],
        context_lines: int = 3,
        stack_depth: int = 10,
        frame_variables: dict[int, dict] = None,
    ) -> str:
        """Display the current step and wait for user action.
        
        Args:
            frame_variables: Optional dict mapping frame index to variables dict
                            for caller frames.
        
        Returns: 'step', 'continue', or 'quit'
        """
        self.current_frame = frame
        self.current_lineno = lineno
        self.source_lines = source_lines
        self.breakpoints = breakpoints
        self.conditional_breakpoints = conditional_breakpoints
        self.variables = variables
        self.prev_variables = prev_variables
        self.watches = watches
        self.call_stack = call_stack
        self.context_lines = context_lines
        self.stack_depth = stack_depth
        self.result = None
        
        # Store frame variables
        self._frame_variables = frame_variables or {}
        
        # Reset to show current frame variables
        self._displayed_variables_frame = -1
        
        # Reset expanded frame to most recent caller
        self.expanded_frame_index = -2
        
        # Create window if not exists
        if self.root is None:
            self._create_window()
        
        # Update spinboxes with current values
        self.context_spinbox.delete(0, tk.END)
        self.context_spinbox.insert(0, str(context_lines))
        self.stack_spinbox.delete(0, tk.END)
        self.stack_spinbox.insert(0, str(stack_depth))
        
        # Update all panels
        self._update_location()
        self._update_current_frame()
        self._update_call_stack()
        self._update_variables()
        self._update_watches()
        
        # Show window and wait for user action
        self.root.deiconify()
        self.root.update()
        
        # Run mainloop until user action
        self.root.mainloop()
        
        return self.result or "quit"

    def close(self):
        """Close the GUI window."""
        if self.root:
            self.root.destroy()
            self.root = None

    def hide(self):
        """Hide the GUI window."""
        if self.root:
            self.root.withdraw()
