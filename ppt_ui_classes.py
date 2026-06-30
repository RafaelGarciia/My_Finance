# ppt_ui_classes.py
"""
TUI Component Classes for prompt_toolkit.

Provides customizable UI components with support for custom key bindings:
- Menu: Selection menu with custom bindings
- Form: Text input form with validators and custom bindings  
- Table: Paginated table with custom bindings

Each component supports adding/removing custom key bindings via:
    component.add_binding(key, handler)
    component.remove_binding(key)
"""

from prompt_toolkit.filters import is_done
from prompt_toolkit import Application
from prompt_toolkit.layout import Layout, Window
from prompt_toolkit.layout.controls import FormattedTextControl
from prompt_toolkit.key_binding import KeyBindings
from prompt_toolkit.styles import Style
from typing import Callable, Any
import os

def clear():
    """Clear the terminal screen.
    
    Works on both Windows (cls) and Unix-like systems (clear).
    """
    os.system('cls' if os.name == 'nt' else 'clear')


BASE_STYLE = {
    "title"                 : f"{'#ffffff'}",
    "field.selected"        : f"{'#ffffff'} bg:{'#444444'}",
    "option.selected"       : f"{'#ffffff'} bg:{'#444444'}",
    "option"                : f"{'#888888'}",
    "option.alt"            : f"{'#888888'} bg:{'#1a1a1a'}",
    "field.label"           : f"{'#888888'}",
    "field.header"          : f"{'#ffffff'} bg:{'#333333'} bold",
    "field.value"           : f"{'#ffffff'}",
    "hint"                  : f"{'#000000'} bg:{'#888888'}",
    "status.err"            : f"{'#ff0000'}",
    "save_button.selected"  : f"{'#27da03'} bg:{'#444444'}",
    "save_button"           : f"{'#1ba300'}"
}


def run_app(get_content, kb: KeyBindings, style: dict | Style | None = None):
    """Run a prompt_toolkit application with the given configuration.
    
    Args:
        get_content (Callable): Function that returns FormattedText content
        kb (KeyBindings): Key bindings for the application
        style (dict | Style, optional): Style configuration
    
    Returns:
        Any: Result returned by the application exit handler
    """
    return Application(
        layout=Layout(Window(FormattedTextControl(get_content, focusable=True))),
        key_bindings=kb,
        style=style if isinstance(style, Style) else Style.from_dict(style or {}),
        full_screen=False,
        refresh_interval=0.05,
        mouse_support=False,
    ).run()


class Menu:
    """Selection menu with keyboard navigation and custom bindings.
    
    Attributes:
        title (str): Menu title
        options (list[str]): List of option labels
        back_option_str (str): Label for back/exit option
        style (dict | Style): Style configuration
        kb (KeyBindings): Key bindings object
    
    Methods:
        add_binding(key, handler): Add custom key binding
        remove_binding(key): Remove key binding
        run(): Execute the menu and return selected option
    
    Example:
        >>> menu = Menu("Main", ["Option 1", "Option 2"])
        >>> menu.add_binding("ctrl-q", lambda e, m: e.app.exit(result="quit"))
        >>> result = menu.run()
    """
    
    def __init__(
        self,
        title: str,
        options: list[str],
        back_option_str: str | None = None,
        style: dict | Style = BASE_STYLE,
        validators: dict[int, Callable[[Any], bool]] | None = None
    ):
        self.title = title
        self.options = options
        self.back_option_str = back_option_str or "Exit"
        self.style = style
        self.validators = validators or {}
        
        self.selected_option = [0]
        self.kb = KeyBindings()
        self._custom_bindings = {}
        self._setup_default_bindings()
    
    def _setup_default_bindings(self):
        """Setup default keyboard bindings."""
        @self.kb.add("up")
        @self.kb.add("w")
        def _(event):
            self.selected_option[0] = (self.selected_option[0] - 1) % len(self.options)

        @self.kb.add("down")
        @self.kb.add("s")
        def _(event):
            self.selected_option[0] = (self.selected_option[0] + 1) % len(self.options)

        @self.kb.add("enter")
        @self.kb.add("d")
        def _(event):
            event.app.exit(result=self.selected_option)

        @self.kb.add("escape")
        @self.kb.add("c-c")
        @self.kb.add("a")
        def _(event):
            event.app.exit(result="cancel")
    
    def add_binding(self, key: str, handler: Callable):
        """Add a custom key binding.
        
        Args:
            key (str): Key sequence (e.g., "ctrl-x", "f1")
            handler (Callable): Function with signature: handler(event, self)
        
        Example:
            >>> menu.add_binding("ctrl-x", lambda e, m: print("Custom action"))
        """
        @self.kb.add(key)
        def _(event):
            handler(event, self)
        self._custom_bindings[key] = handler
    
    def remove_binding(self, key: str) -> bool:
        """Remove a custom key binding.
        
        Args:
            key (str): Key sequence to remove
        
        Returns:
            bool: True if binding was removed, False if not found
        """
        if key in self._custom_bindings:
            del self._custom_bindings[key]
            # Note: prompt_toolkit doesn't support removing bindings from KeyBindings
            # This is a limitation of the library
            return True
        return False
    
    def _content(self):
        """Generate the menu display content."""
        lines = [("class:title", f"  {self.title}\n\n")]
        
        for index, label in enumerate(self.options):
            active = (index == self.selected_option[0])
            style_class = "class:option.selected" if active else "class:option"
            lines.append((style_class, f"  {label:<16}  \n"))
        
        lines.append(("", "\n"))
        
        hint = (
            f"  {'[ ↑↓ / W S ] - Navigate':<30}  \n"
            f"  {'[ Enter / D ] - Confirm':<30}  \n"
            f"  {('[ Esc / A ] - ' + self.back_option_str):<30}  "
        )
        lines.append(("class:hint", hint))
        
        return lines
    
    def run(self) -> int | None:
        """Execute the menu.
        
        Returns:
            int | None: 1-based index of selected option, or None if cancelled
        """
        result = run_app(self._content, self.kb, self.style)
        if result == "cancel":
            return None
        return result[0] + 1


class Form:
    """Text input form with field validation and custom bindings.
    
    Attributes:
        title (str): Form title
        fields (list[tuple[str, str]]): List of (key, label) tuples
        default (dict): Default field values
        validators (dict): Field validators
        style (dict | Style): Style configuration
        kb (KeyBindings): Key bindings object
    
    Methods:
        add_binding(key, handler): Add custom key binding
        remove_binding(key): Remove key binding
        run(): Execute the form and return field values
    
    Example:
        >>> form = Form("Login", [("user", "Username"), ("pass", "Password")])
        >>> form.add_binding("ctrl-q", lambda e, f: e.app.exit(result="cancel"))
        >>> result = form.run()
    """
    
    def __init__(
        self,
        title: str,
        fields: list[tuple[str, str]],
        default: dict = {},
        style: dict | Style = BASE_STYLE,
        save_button_str: str | None = None,
        validators: dict[str, Callable[[str], tuple[bool, str]]] | None = None
    ):
        self.title = title
        self.fields = fields
        self.default = default
        self.style = style
        self.save_button_str = save_button_str or "SAVE"
        self.validators = validators or {}
        
        self.save_button = len(fields)
        self.values = {k: str(default.get(k) or "") for k, _ in fields}
        self.selected_option = [0]
        self.error_messages = {}
        
        self.kb = KeyBindings()
        self._custom_bindings = {}
        self._setup_default_bindings()
    
    def _setup_default_bindings(self):
        """Setup default keyboard bindings."""
        @self.kb.add("up")
        def _(event):
            self.selected_option[0] = (self.selected_option[0] - 1) % (self.save_button + 1)

        @self.kb.add("down")
        def _(event):
            self.selected_option[0] = (self.selected_option[0] + 1) % (self.save_button + 1)

        @self.kb.add("enter")
        def _(event):
            if self.selected_option[0] == self.save_button:
                all_valid = all(
                    self._validate_field(k, self.values[k]) for k, _ in self.fields
                )
                if all_valid:
                    event.app.exit(result="ok")
            else:
                self.selected_option[0] = (self.selected_option[0] + 1) % (self.save_button + 1)

        @self.kb.add("space")
        def _(event):
            if self.selected_option[0] == self.save_button:
                event.app.exit(result="ok")
            else:
                key, _ = self.fields[self.selected_option[0]]
                self.values[key] += " "
                self._validate_field(key, self.values[key])

        @self.kb.add("backspace")
        def _(event):
            if self.selected_option[0] == self.save_button:
                return
            key, _ = self.fields[self.selected_option[0]]
            self.values[key] = self.values[key][:-1]
            self._validate_field(key, self.values[key])

        @self.kb.add("<any>")
        def _(event):
            if self.selected_option[0] == self.save_button:
                return
            k = event.key_sequence[0].key
            if len(k) != 1 or ord(k) < 32:
                return
            key, _ = self.fields[self.selected_option[0]]
            self.values[key] += k
            self._validate_field(key, self.values[key])

        @self.kb.add("escape")
        @self.kb.add("c-c")
        def _(event):
            event.app.exit(result="cancel")
    
    def add_binding(self, key: str, handler: Callable):
        """Add a custom key binding.
        
        Args:
            key (str): Key sequence (e.g., "ctrl-x")
            handler (Callable): Function with signature: handler(event, self)
        """
        @self.kb.add(key)
        def _(event):
            handler(event, self)
        self._custom_bindings[key] = handler
    
    def remove_binding(self, key: str) -> bool:
        """Remove a custom key binding.
        
        Args:
            key (str): Key sequence to remove
        
        Returns:
            bool: True if binding was removed, False if not found
        """
        if key in self._custom_bindings:
            del self._custom_bindings[key]
            return True
        return False
    
    def _validate_field(self, key: str, value: str) -> bool:
        """Validate a field value."""
        if key in self.validators:
            is_valid, msg = self.validators[key](value)
            self.error_messages[key] = msg if not is_valid else ""
            return is_valid
        return True
    
    def _content(self):
        """Generate the form display content."""
        lines = [("class:title", f"  {self.title}\n\n")]
        
        for index, (key, label) in enumerate(self.fields):
            active = (index == self.selected_option[0])
            label_style = "class:field.selected" if active else "class:field.label"
            value_style = "class:field.selected" if active else "class:field.value"
            
            lines.append((label_style, f"  {label:<16}  "))
            cursor = "|" if active else ""
            lines.append((value_style, f"{self.values[key]}{cursor}\n"))
            
            if key in self.error_messages and self.error_messages[key]:
                lines.append(("class:status.err", f"    ⚠ {self.error_messages[key]}\n"))
        
        lines.append(("", "\n"))
        
        if self.selected_option[0] == self.save_button:
            lines.append(("class:save_button.selected", f"  {'❯ [ ' + self.save_button_str + ' ]':^30}  \n"))
        else:
            lines.append(("class:save_button", f"  {'  [ ' + self.save_button_str + ' ]':^30}  \n"))
        
        hint = (
            f"\n  {'[ ↑↓ ] - Navigate':<30}  \n"
            f"  {'[ Enter ] - Next/Save':<30}  \n"
            f"  {'[ Esc ] - Cancel':<30}  "
        )
        lines.append(("class:hint", hint))

        return lines
    
    def run(self) -> dict | None:
        """Execute the form.
        
        Returns:
            dict | None: Dictionary with field values plus 'id' if present, or None if cancelled
        """
        result = run_app(self._content, self.kb, self.style)
        if result == "ok":
            return {**self.values, "id": self.default.get("id")}
        return None


class Table:
    """Paginated table with keyboard navigation and custom bindings.
    
    Attributes:
        title (str): Table title
        columns (list[tuple[str, str]]): List of (key, header) tuples
        rows (list[dict]): Row data
        page_size (int): Rows per page
        style (dict | Style): Style configuration
        kb (KeyBindings): Key bindings object
    
    Methods:
        add_binding(key, handler): Add custom key binding
        remove_binding(key): Remove key binding
        run(): Execute the table and return selected row
    
    Example:
        >>> table = Table("Users", [("name", "Name")], [{"name": "Alice"}])
        >>> table.add_binding("ctrl-x", lambda e, t: e.app.exit(result="quit"))
        >>> result = table.run()
    """
    
    def __init__(
        self,
        title: str,
        columns: list[tuple[str, str]],
        rows: list[dict],
        style: dict | Style = BASE_STYLE,
        back_option_str: str | None = None,
        page_size: int = 10,
    ):
        self.title = title
        self.columns = columns
        self.rows = rows
        self.style = style
        self.back_option_str = back_option_str or "Back"
        self.page_size = page_size
        
        self.selected_row = [0]
        self.scroll = [0]
        self.kb = KeyBindings()
        self._custom_bindings = {}

        self.hint = (
            f"  {'[ ↑↓ / W S ] - Navigate':<30}  \n"
            f"  {'[ Enter / D ] - Select':<30}  \n"
            f"  {('[ Esc / A ] - ' + self.back_option_str):<30}  "
        )
        
        # Calculate column widths
        if not rows:
            self.widths = [max(len(h), 4) for _, h in columns]
        else:
            self.widths = [
                max(len(header), *(len(str(row.get(key, ""))) for row in rows))
                for key, header in columns
            ]
        
        self._setup_default_bindings()
    
    def _setup_default_bindings(self):
        """Setup default keyboard bindings."""
        @self.kb.add("up")
        @self.kb.add("w")
        def _(event):
            if self.rows:
                self.selected_row[0] = (self.selected_row[0] - 1) % len(self.rows)
                self._clamp_scroll()

        @self.kb.add("down")
        @self.kb.add("s")
        def _(event):
            if self.rows:
                self.selected_row[0] = (self.selected_row[0] + 1) % len(self.rows)
                self._clamp_scroll()

        @self.kb.add("enter")
        @self.kb.add("d")
        def _(event):
            if self.rows:
                event.app.exit(result=self.selected_row[0])

        @self.kb.add("escape")
        @self.kb.add("c-c")
        @self.kb.add("a")
        def _(event):
            event.app.exit(result="cancel")
    
    def add_binding(self, key: str, handler: Callable):
        """Add a custom key binding.
        
        Args:
            key (str): Key sequence (e.g., "ctrl-x")
            handler (Callable): Function with signature: handler(event, self)
        """
        @self.kb.add(key)
        def _(event):
            handler(event, self)
        self._custom_bindings[key] = handler
    
    def remove_binding(self, key: str) -> bool:
        """Remove a custom key binding.
        
        Args:
            key (str): Key sequence to remove
        
        Returns:
            bool: True if binding was removed, False if not found
        """
        if key in self._custom_bindings:
            del self._custom_bindings[key]
            return True
        return False
    
    def _clamp_scroll(self):
        """Ensure the selected row is visible in the current page."""
        if self.selected_row[0] < self.scroll[0]:
            self.scroll[0] = self.selected_row[0]
        elif self.selected_row[0] >= self.scroll[0] + self.page_size:
            self.scroll[0] = self.selected_row[0] - self.page_size + 1
    
    def _format_row(self, row: dict | None) -> str:
        """Format a row for display."""
        cells = []
        for (key, header), w in zip(self.columns, self.widths):
            text = header if row is None else str(row.get(key, ""))
            cells.append(f"{text:<{w}}")
        return "  ".join(cells)
    
    def _content(self):
        """Generate the table display content."""
        lines = [("class:title", f"  {self.title}\n\n")]
        
        lines.append(("class:field.header", f"  {self._format_row(None)}  \n"))
        
        if not self.rows:
            lines.append(("class:status.err", "  (no data)\n"))
        else:
            visible = self.rows[self.scroll[0]: self.scroll[0] + self.page_size]
            for index, row in enumerate(visible):
                idx = self.scroll[0] + index
                active = (idx == self.selected_row[0])
                
                if active:
                    label_style = "class:option.selected"
                else:
                    label_style = "class:option" if idx % 2 == 0 else "class:option.alt"
                
                lines.append((label_style, f"  {self._format_row(row)}  \n"))
        
        lines.append(("", "\n"))
        lines.append(("class:hint", self.hint))
        
        return lines
    
    def run(self) -> dict | None:
        """Execute the table.
        
        Returns:
            dict | None: The selected row as a dictionary, or None if cancelled
        """
        result = run_app(self._content, self.kb, self.style)
        if isinstance(result, int):
            return self.rows[result]
        else: return result

        
