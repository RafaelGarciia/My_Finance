from prompt_toolkit.layout.controls import FormattedTextControl
from prompt_toolkit.key_binding import KeyBindings
from prompt_toolkit.layout import Layout, Window
from prompt_toolkit.filters import is_done
from prompt_toolkit.styles import Style
from prompt_toolkit import Application

from typing import Callable, Any

from .utility import clear_screen





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

def run_application(content: Callable, key_bindings: KeyBindings, style: dict | Style | None):
    """
    Run a prompt_toolkit application with the given content, key bindings, and style.
    
    :param content: A :class:`~Callable` that returns the content to be displayed.
    :param key_bindings: A :class:`~KeyBindings` object containing the key bindings for the application.
    :param style: A :class:`~dict` or :class:`~Style` object defining the style for the application. If None, default style will be used.
    :return: The result of the application run - :class:`~None`.
    """

    _layout = Layout(Window(FormattedTextControl(content, focusable=True)))
    _style = style if isinstance(style, Style) else Style.from_dict(style or {})
    
    return Application(
        layout=_layout,
        key_bindings=key_bindings,
        style=_style,
        full_screen=False,
        refresh_interval=0.05,
        mouse_support=False
    ).run()


# Widgets V

class Menu:
    """
    Selection menu with keyboard navigation and custom bindings.

    
    :param str title: The title of the menu.
    :param list[str] options: A :class:`list` of option :class:`str` to display in the menu.
    :param str | None text_back_bnt: Optional :class:`str` for the back button text.
    :param dict | Style style: Optional :class:`dict` or :class:`Style` for custom styling. Defaults to BASE_STYLE.        

    :return: The index of the selected option or "cancel" if the back button is pressed.
    """

    def __init__(
            self,
            title: str,
            options: list[str],
            text_back_bnt: str | None = None,
            style: dict | Style = BASE_STYLE,
        ) -> None:
        
        self.title = title
        self.options = options
        self.text_back_bnt = text_back_bnt
        self.style = style

        self.selected_option = 0
        self.keybindings = KeyBindings()
        self._custom_bindings = {}
        self.hint = (
            f"  {'[ ↑↓ / W S ] - Navigate':<30}  \n"
            f"  {'[ Enter / D ] - Confirm':<30}  \n"
            f"  {('[ Esc / A ] - ' + self.back_option_str):<30}  "
        )

        self._setup_default_bindings()

    # V Internal Functions

    def _setup_default_bindings(self) -> None:
        """Setup default keyboard bindings."""

        @self.kb.add("up")
        @self.kb.add("w")
        def _(event): self.selected_option = (self.selected_option - 1) % len(self.options)

        @self.kb.add("down")
        @self.kb.add("s")
        def _(event): self.selected_option = (self.selected_option + 1) % len(self.options)

        @self.kb.add("enter")
        @self.kb.add("d")
        def _(event): event.app.exit(result=self.selected_option)

        @self.kb.add("escape")
        @self.kb.add("c-c")
        @self.kb.add("a")
        def _(event): event.app.exit(result="cancel")

    def _content(self):
        """Generate the menu display content."""
        
        lines = [("class:title", f"  {self.title}\n\n")]

        for index, label in enumerate(self.options):
            is_selected = (index == self.selected_option)
            if is_selected: style_class = "class:option.selected"
            else: style_class = "class:option"
            lines.append((style_class, f"  {label:<16}  \n"))
        
        lines.append(("", "\n"))
        lines.append(("class:hint", self.hint))

        return lines
        

    # V External Functions

    def add_binding(self, key: str, handler: Callable) -> None:
        """Add a custom key binding.
        
        Args:
            key (str): Key sequence ("c-x", "f1", "space")
            handler (Callable): Function with signature: handler(event, self)
        
        ------------------------------------------------------
            >>> menu.add_binding("c-x", lambda e, m: print("Custom action"))
        """

        @self.keybindings.add(key)
        def _(event): handler(event, self)
        self._custom_bindings[key] = handler

    def run(self) -> int | str:
        """Execute the menu.
        
        Returns:
            Integer | String (int | str): int for the selected option or str for the configured KeyBindings
        """

        return run_application(self._content, self.keybindings, self.style)


class Form:
    """
    Form with multiple fields and keyboard navigation.

    :param str title: The title of the form.
    :param list[dict] fields: A :class:`list` of field :class:`dict` to display in the form.
    :param dict | Style style: Optional :class:`dict` or :class:`Style` for custom styling. Defaults to BASE_STYLE.
    """
    
    def __init__(
            self,
            title: str,
            fields: list[dict],
            style: dict | Style = BASE_STYLE,
        ) -> None:
        
        self.title = title
        self.fields = fields
        self.style = style

        self.selected_field = 0
        self.keybindings = KeyBindings()
        self._custom_bindings = {}
        self.hint = (
            f"  {'[ ↑↓ / W S ] - Navigate':<30}  \n"
            f"  {'[ Enter / D ] - Edit':<30}  \n"
            f"  {'[ Esc / A ] - Cancel':<30}  "
        )

        self._setup_default_bindings()


