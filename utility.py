from os import system, name

def clear_screen() -> None:
    """
    Clear the terminal screen.\n
    Works on both, Windows (cls) and Unix-like systems (clear).
    """
    system('cls' if name == 'nt' else 'clear')