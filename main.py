# main.py
from prompt_ui import Menu, base_keybindings, cadastrar_transacao

STYLE = {
    "frame.border": "#ff4444",
    "selected-option": "bold",
    "bottom-toolbar": "#ffffff bg:#333333 noreverse",
}

def main():
    kb = base_keybindings()

    while True:
        result = Menu(
            title="Menu Principal:",
            options=["Nova transação", "Listar transações", "Configurações"],
            keybindings=kb,
            style=STYLE,
            back_option_str="Sair",
        ).run()

        if result == 0:
            break
        elif result == 1:
            transacao = cadastrar_transacao(keybindings=kb, style=STYLE)
            if transacao:
                print("Transação salva!")  # substitua pelo save real
        # elif result == 2: listar...
        # elif result == 3: configurações...

if __name__ == "__main__":
    main()