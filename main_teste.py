from prompt_toolkit.filters import is_done
from prompt_toolkit import Application
from prompt_toolkit.layout import Layout, Window
from prompt_toolkit.layout.controls import FormattedTextControl
from prompt_toolkit.key_binding import KeyBindings
from prompt_toolkit.styles import Style
import os

def clear():
    os.system('cls' if os.name == 'nt' else 'clear')

STYLE = {
    "title"                 : f"{'#ffffff'}",
    "field.selected"        : f"{'#ffffff'} bg:{'#444444'}",
    "option.selected"       : f"{'#ffffff'} bg:{'#444444'}",
    "field.label"           : f"{'#888888'}",
    "option"                : f"{'#888888'}",
    "field.value"           : f"{'#ffffff'}",
    "hint"                  : f"{'#000000'} bg:{'#888888'}",
    "status.err"            : f"{'#ff0000'}",
    "save_button.selected"  : f"{'#27da03'} bg:{'#444444'}",
    "save_button"           : f"{'#1ba300'}"
}

def run_app(get_content, kb: KeyBindings, style: dict | Style | None = None):
    return Application(
        layout=Layout(Window(FormattedTextControl(get_content, focusable=True))),
        key_bindings=kb,
        style=style if isinstance(style, Style) else Style.from_dict(style or {}),
        full_screen=False,
        refresh_interval=0.05,
        mouse_support=False,
    ).run()


def menu(
        title:str,
        options:list[tuple[str,str]],
        back_option_str: str | None = "Exit",
        style: dict | Style | None = None
    ):
    

    selected_option = [0] # Índice do campo ativo
    kb = KeyBindings()

    def set_keybindings():
        @kb.add("up")
        @kb.add("w")
        def _(event): selected_option[0] = (selected_option[0] - 1)

        @kb.add("down")
        @kb.add("s")
        def _(event): selected_option[0] = (selected_option[0] + 1)

        @kb.add("enter")
        @kb.add("space")
        def _(event): event.app.exit(result=selected_option)

        @kb.add("escape")
        @kb.add("c-c")
        def _(event): event.app.exit(result="cancel")

    def content():
        opts = [(i + 1, text) for i, text in enumerate(options)]
        if back_option_str: opts.append((0, back_option_str))

        lines = [("class:title", f"  {title}\n\n")]
        for i, (key, label) in enumerate(opts):
            active = (i == selected_option[0])
            ls = "class:option.selected" if active else "class:option"
            lines.append((ls, f"  {label:<16}  "))
        lines.append(("", "\n"))
        lines.append(("class:hint",
            f"\n  [ ↑↓ / W S ] - Navegar    [ Enter / Space ] - Confirmar    [ Esc ] - {back_option_str}  "
        ))
        
        return lines

    set_keybindings()
    result = run_app(content, kb, style)
    
    input(result)


def formulario(
        title: str,
        fields: list[tuple[str,str]],
        default: dict,
        style: dict | Style | None = None
    ) -> dict | None:
    """
    Exibe um formulário com os campos fornecidos.\n
    Retorna dict com valores ou None se cancelado.\n
    `title`: str\n
    `fields`: list [ tuple [ str , str ] ] = [ ( key , label ), ... ]\n
    `default`: dict = { "key" : "value", ... }\n
    `style`: dict\n
    -------------------------------------------------------------------
    `style class`:\n
        "field.selected"
        "field.label"
        "field.value"
        "hint"
        "status.error"
        "save_button.selected"
        "save_button"
    """

    save_button    = len(fields) # Índice do botão de salvar
    values         = {k: str(default.get(k) or "") for k, _ in fields} # Valores atuais
    selected_option = [0] # Índice do campo ativo
    kb = KeyBindings()

    def set_keybindings():
        @kb.add("up")
        def _(event): selected_option[0] = (selected_option[0] - 1) % (save_button + 1)

        @kb.add("down")
        def _(event): selected_option[0] = (selected_option[0] + 1) % (save_button + 1)

        @kb.add("enter")
        def _(event):
            if selected_option[0] == save_button:
                event.app.exit(result="ok")
            else:
                selected_option[0] = (selected_option[0] + 1) % (save_button + 1)

        @kb.add("space")
        def _(event):
            if selected_option[0] == save_button:
                event.app.exit(result="ok")
            else:
                key, _ = fields[selected_option[0]]
                values[key] += " "

        @kb.add("backspace")
        def _(event):
            if selected_option[0] == save_button: return
            key, _ = fields[selected_option[0]]
            values[key] = values[key][:-1]

        @kb.add("<any>")
        def _(event):
            if selected_option[0] == save_button: return
            k = event.key_sequence[0].key
            if len(k) != 1 or ord(k) < 32: return
            key, _ = fields[selected_option[0]]
            values[key] += k

        @kb.add("escape")
        @kb.add("c-c")
        def _(event): event.app.exit(result="cancel")

    def content():
        lines = [("class:title", f"  {title}\n\n")]
        for i, (key, label) in enumerate(fields):
            active = (i == selected_option[0])
            ls = "class:field.selected" if active else "class:field.label"
            vs = "class:field.selected" if active else "class:field.value"
            lines.append((ls, f"  {label:<16}  "))
            lines.append((vs, f"{values[key]}{'|' if active else ''}\n"))
        lines.append(("", "\n"))
        if selected_option[0] == save_button:
            lines.append(("class:save_button.selected",  "      ❯ [ SALVAR ]\n"))
        else:
            lines.append(("class:save_button", "        [ SALVAR ]\n"))
        
        lines.append(("class:hint",
            "\n  [ ↑↓ ] - Navegar    [ Enter ] - Próximo/Salvar    [ Esc ] - Cancelar  "
        ))
        
        return lines

    set_keybindings()
    result = run_app(content, kb, style)
    if result == "ok":
        return {**values, "id": default.get("id")}
    return None


clear()
#print(formulario("Formulário de Teste", [("nome", "Nome"), ("idade", "Idade"), ("data", "Data")], {"nome": "Rafa", "idade":"26", "data": "01/01/2023"}, STYLE))
menu('teste', [("nome", "Nome"), ("idade", "Idade"), ("data", "Data")], style=STYLE)