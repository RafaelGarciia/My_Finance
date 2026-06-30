# prompt_ui.py
from prompt_toolkit.filters import is_done
from prompt_toolkit.formatted_text import HTML
from prompt_toolkit.shortcuts import choice as prompt_choice
from prompt_toolkit.styles import Style
from prompt_toolkit.key_binding import KeyBindings
from prompt_toolkit.input.vt100_parser import KeyPress
from prompt_toolkit.keys import Keys

def base_keybindings() -> KeyBindings:
    kb = KeyBindings()
    kb.add("c-c")  (lambda event: event.app.exit())
    kb.add("w")    (lambda event: event.app.key_processor.feed(KeyPress(Keys.Up)))
    kb.add("s")    (lambda event: event.app.key_processor.feed(KeyPress(Keys.Down)))
    kb.add("d")    (lambda event: event.app.key_processor.feed(KeyPress(Keys.Enter)))
    kb.add("a")    (lambda event: event.app.exit(result=0))
    return kb

class Menu:
    def __init__(
        self,
        title: str,
        options: list[str],
        keybindings: KeyBindings | None = None,
        style: Style | dict | None = None,
        back_option_str: str | None = "Sair"
    ):
        self.title = title
        opts = [(i + 1, text) for i, text in enumerate(options)]
        if back_option_str: opts.append((0, back_option_str))
        self.options = opts
        self.keybindings = keybindings or KeyBindings()
        self.style = style if isinstance(style, Style) else Style.from_dict(style or {})

    def run(self):
        return prompt_choice(
            message=self.title,
            options=self.options,
            style=self.style,
            key_bindings=self.keybindings,
            bottom_toolbar=HTML(
                " Press <b>[W]</b>/<b>[S]</b> or <b>[Up]</b>/<b>[Down]</b> to select,"
                " <b>[D]</b> to accept, <b>[A]</b> to go back."
            ),
            show_frame=~is_done,
        )

# prompt_ui.py  (adicione ao arquivo existente)
from datetime import datetime
from prompt_toolkit import prompt
from prompt_toolkit.validation import Validator, ValidationError
from prompt_toolkit.formatted_text import HTML


# ── Validadores ────────────────────────────────────────────────────────────────

class NaoVazioValidator(Validator):
    def validate(self, document):
        if not document.text.strip():
            raise ValidationError(message="Campo obrigatório, não pode ser vazio.")


class DataValidator(Validator):
    def validate(self, document):
        text = document.text.strip()
        if not text:
            raise ValidationError(message="Campo obrigatório.")
        try:
            datetime.strptime(text, "%d/%m/%Y")
        except ValueError:
            raise ValidationError(message="Data inválida. Use o formato DD/MM/AAAA.")


class ValorValidator(Validator):
    def validate(self, document):
        text = document.text.strip()
        if not text:
            raise ValidationError(message="Campo obrigatório.")
        try:
            valor = float(text.replace(",", "."))
            if valor <= 0:
                raise ValueError
        except ValueError:
            raise ValidationError(message="Valor inválido. Use o formato 12,50.")


# ── Mock de cartões ────────────────────────────────────────────────────────────

def fetch_cartoes() -> list[dict]:
    """Substitua pelo fetch real do banco de dados."""
    return [
        {"id": 1, "nome": "Nubank"},
        {"id": 2, "nome": "Inter"},
        {"id": 3, "nome": "C6 Bank"},
    ]


# ── Formulário ─────────────────────────────────────────────────────────────────

def cadastrar_transacao(keybindings=None, style=None) -> dict | None:
    _style = style if isinstance(style, Style) else Style.from_dict(style or {})
    hoje = datetime.today().strftime("%d/%m/%Y")

    print("\n── Nova Transação ──────────────────────────────\n")

    try:
        # Descrição
        descricao = prompt(
            "Descrição : ",
            validator=NaoVazioValidator(),
            validate_while_typing=False,
            style=_style,
        ).strip()

        # Data
        data_str = prompt(
            "Data       : ",
            default=hoje,
            validator=DataValidator(),
            validate_while_typing=False,
            style=_style,
        ).strip()
        data = datetime.strptime(data_str, "%d/%m/%Y").date()

        # Valor
        valor_str = prompt(
            "Valor (R$) : ",
            validator=ValorValidator(),
            validate_while_typing=False,
            style=_style,
        ).strip()
        valor = float(valor_str.replace(",", "."))

        # Carteira ou cartão
        meio = Menu(
            title="Pago com:",
            options=["Carteira", "Cartão"],
            keybindings=keybindings,
            style=style,
            back_option_str=None,
        ).run()

        cartao = None
        if meio == 2:  # Cartão
            cartoes = fetch_cartoes()
            if not cartoes:
                print("\nNenhum cartão cadastrado.")
                return None

            cartao_opcoes = [c["nome"] for c in cartoes]
            cartao_idx = Menu(
                title="Selecione o cartão:",
                options=cartao_opcoes,
                keybindings=keybindings,
                style=style,
                back_option_str=None,
            ).run()
            cartao = next((c for c in cartoes if c["id"] == cartao_idx), None)

    except (KeyboardInterrupt, EOFError):
        print("\nCadastro cancelado.")
        return None

    transacao = {
        "descricao": descricao,
        "data": data,
        "valor": valor,
        "meio": "carteira" if meio == 1 else "cartao",
        "cartao": cartao,
    }

    print("\n── Resumo ──────────────────────────────────────")
    print(f"  Descrição : {transacao['descricao']}")
    print(f"  Data      : {transacao['data'].strftime('%d/%m/%Y')}")
    print(f"  Valor     : R$ {transacao['valor']:.2f}")
    print(f"  Meio      : {transacao['meio']}")
    if cartao:
        print(f"  Cartão    : {cartao['nome']}")
    print("────────────────────────────────────────────────\n")

    return transacao