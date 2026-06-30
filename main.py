import ppt_ui as ppt


def add_conta():
    info = ppt.formulario(
        '1 Formulario',
        [   ("nome", "Nome"),
            ("teste", "Teste")
        ]
    )

    print(info)


while True:
    opt = ppt.menu(
        "Main Menu",
        ['opt1', 'opt2', 'opt3'],
        'Sair',
    )
    
    match int(opt):
        case 0: break

        case 1: add_conta()
            


