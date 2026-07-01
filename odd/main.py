# main.py
from datetime import datetime

import ppt_ui_classes as ppt
from database import db


def br_to_iso(date_str: str) -> str:
    """Convert DD/MM/YYYY -> YYYY-MM-DD. Raises ValueError if invalid."""
    return datetime.strptime(date_str.strip(), "%d/%m/%Y").strftime("%Y-%m-%d")


def iso_to_br(date_str: str) -> str:
    """Convert YYYY-MM-DD -> DD/MM/YYYY for display."""
    try:
        return datetime.strptime(date_str, "%Y-%m-%d").strftime("%d/%m/%Y")
    except ValueError:
        return date_str


def pick_id_via_menu(title: str, items: list[dict], label_fn) -> int | None:
    """Show a Menu of items and return the chosen item's id, or None."""
    if not items:
        return None
    options = [label_fn(item) for item in items]
    opt = ppt.Menu(title, options, "Cancel").run()
    if opt is None:
        return None
    return items[opt - 1]["id"]


# ==================== BANKS ====================

def banks():
    while True:
        ppt.clear()

        bank_list = db.get_all_banks()
        _table = ppt.Table("Bancos", [("name", "BANCO")], bank_list)
        _table.add_binding("n", lambda event, t: event.app.exit(result="add"))
        _table.hint = f"{_table.hint}\n  {'[ N ] - Add Bank':<30}  "

        info = _table.run()

        if info is None:
            return
        elif info == "add":
            add_bank()
            continue
        elif info == "cancel":
            break

        ppt.clear()
        opt = ppt.Menu(f"{info['name']}", ["Edit", "Delete"], "Back").run()

        match opt:
            case 1:
                result = ppt.Form("Edit Bank", [("name", "Name")], default=info).run()
                if result:
                    db.update_bank(info["id"], result["name"])

            case 2:
                ppt.clear()
                confirm = ppt.Menu(
                    f"Delete {info['name']}? (accounts/cards linked to it will be removed too)",
                    ["Yes", "No"],
                    "Cancel",
                ).run()
                if confirm == 1:
                    db.delete_bank(info["id"])


def add_bank():
    ppt.clear()
    result = ppt.Form("New Bank", [("name", "Name")]).run()
    if result:
        try:
            db.add_bank(result["name"])
        except Exception:
            ppt.clear()
            ppt.Menu("Invalid or duplicate bank name!", ["OK"], "Exit").run()


def require_bank_id(action_label: str) -> int | None:
    """Make the user pick an existing bank, creating one first if none exist."""
    bank_list = db.get_all_banks()
    if not bank_list:
        ppt.clear()
        choice = ppt.Menu(
            "No banks found. Create one first.", ["Create Bank"], "Cancel"
        ).run()
        if choice != 1:
            return None
        add_bank()
        bank_list = db.get_all_banks()
        if not bank_list:
            return None

    ppt.clear()
    return pick_id_via_menu(action_label, bank_list, lambda b: f"{b['name']}")


# ==================== ACCOUNTS ====================

def accounts():
    while True:
        ppt.clear()

        account_list = db.get_all_accounts()
        _table = ppt.Table(
            "Contas",
            [("name", "NOME"), ("bank", "BANCO"), ("value", "VALOR")],
            account_list,
        )
        _table.add_binding("n", lambda event, t: event.app.exit(result="add"))
        _table.hint = f"{_table.hint}\n  {'[ N ] - Add Account':<30}  "

        info = _table.run()

        if info is None:
            return
        elif info == "add":
            add_account()
            continue
        elif info == "cancel":
            break
        else:
            ppt.clear()
            opt = ppt.Menu(
                f"{info['name']} - {info['bank']} (${info['value']})",
                ["Edit", "Delete"],
                "Back",
            ).run()

            match opt:
                case None:
                    pass

                case 1:
                    new_bank_id = require_bank_id("Choose the new Bank")
                    result = ppt.Form(
                        "Edit Account",
                        [("name", "Name")],
                        default=info,
                    ).run()

                    if result:
                        db.update_account(
                            info["id"],
                            name=result["name"],
                            bank_id=new_bank_id if new_bank_id is not None else None,
                        )

                case 2:
                    ppt.clear()
                    confirm = ppt.Menu(
                        f"Delete {info['name']} - {info['bank']}?",
                        ["Yes", "No"],
                        "Cancel",
                    ).run()

                    if confirm == 1:
                        db.delete_account(info["id"])


def add_account():
    bank_id = require_bank_id("Select the Account's Bank")
    if bank_id is None:
        return

    ppt.clear()
    result = ppt.Form("New Account", [("name", "Name")]).run()

    if result:
        try:
            db.add_account(result["name"], bank_id, 0.0)
        except ValueError:
            ppt.clear()
            ppt.Menu("Invalid value!", ["OK"], "Exit").run()


# ==================== CARDS ====================

def cards():
    while True:
        ppt.clear()

        card_list = db.get_all_cards()
        _table = ppt.Table(
            "Cards",
            [("name", "CARD"), ("bank", "BANK")],
            card_list,
        )
        _table.add_binding("n", lambda event, t: event.app.exit(result="add"))
        _table.hint = f"{_table.hint}\n  {'[ N ] - Add Card':<30}  "

        info = _table.run()

        if info is None:
            return
        elif info == "add":
            add_card()
            continue
        elif info == "cancel":
            break

        ppt.clear()
        opt = ppt.Menu(f"{info['name']} - {info['bank']}", ["Edit", "Delete"], "Back").run()

        match opt:
            case 1:
                new_bank_id = require_bank_id("Choose the new Bank")
                result = ppt.Form(
                    "Edit Card",
                    [("name", "Card Name")],
                    default={"name": info["name"]},
                ).run()
                if result:
                    try:
                        db.update_card(
                            info["id"],
                            name=result["name"],
                            bank_id=new_bank_id if new_bank_id is not None else None,
                        )
                    except ValueError:
                        ppt.clear()
                        ppt.Menu("Invalid bank", ["OK"], "Back").run()

            case 2:
                ppt.clear()
                confirm = ppt.Menu(
                    f"Delete card {info['name']}?",
                    ["Yes", "No"],
                    "Cancel",
                ).run()
                if confirm == 1:
                    db.delete_card(info["id"])


def add_card():
    bank_id = require_bank_id("Select the Card's Bank")
    if bank_id is None:
        return

    ppt.clear()
    result = ppt.Form("New Card", [("name", "Card Name")]).run()
    if result:
        try:
            db.add_card(result["name"], bank_id)
        except ValueError:
            ppt.clear()
            ppt.Menu("Invalid bank.", ["OK"], "Back").run()


# ==================== TRANSACTIONS ====================
# A transaction can be in the past/today ("Pago") or scheduled for the
# future ("Pendente") -- e.g.:
#   15/06/2026 - compra de baterias - $500,00 - cartão do nubank
#   31/07/2026 - pagamento da prestação casa - $558,00 - pix
# The transactions screen is always filtered to one month at a time, with
# left/right navigating to the previous/next month.

MONTH_NAMES_PT = [
    "", "Janeiro", "Fevereiro", "Março", "Abril", "Maio", "Junho",
    "Julho", "Agosto", "Setembro", "Outubro", "Novembro", "Dezembro",
]


def _shift_month(year: int, month: int, delta: int) -> tuple[int, int]:
    """Move (year, month) by `delta` months (can be negative)."""
    index = (year * 12 + (month - 1)) + delta
    return index // 12, index % 12 + 1


def transactions():
    today = datetime.today()
    year, month = today.year, today.month

    while True:
        ppt.clear()

        tx_list = db.get_transactions_by_month(year, month)
        display_rows = [
            {
                **tx,
                "date": iso_to_br(tx["date"]),
                "card_name": tx["card_name"] or "-",
            }
            for tx in tx_list
        ]

        _table = ppt.Table(
            f"Transações - {MONTH_NAMES_PT[month]}/{year}",
            [
                ("date", "DATA"),
                ("description", "DESCRIÇÃO"),
                ("amount", "VALOR"),
                ("bank", "BANCO"),
                ("payment_method", "PAGAMENTO"),
                ("card_name", "CARTÃO"),
                ("status", "STATUS"),
            ],
            display_rows,
        )
        _table.add_binding("n", lambda event, t: event.app.exit(result="add"))
        _table.add_binding("left", lambda event, t: event.app.exit(result="prev_month"))
        _table.add_binding("right", lambda event, t: event.app.exit(result="next_month"))
        _table.hint = (
            f"{_table.hint}\n"
            f"  {'[ N ] - Add Transaction':<30}  \n"
            f"  {'[ ←/→ ] - Mês anterior/próximo':<30}  "
        )

        info = _table.run()

        if info is None:
            return
        elif info == "add":
            add_transaction()
            continue
        elif info == "prev_month":
            year, month = _shift_month(year, month, -1)
            continue
        elif info == "next_month":
            year, month = _shift_month(year, month, 1)
            continue
        elif info == "cancel":
            break

        ppt.clear()
        is_pending = info["status"] == "Pendente"
        toggle_label = "Aprovar Pagamento" if is_pending else "Marcar como Pendente"
        opt = ppt.Menu(
            f"{info['date']} - {info['description']} (${info['amount']}) [{info['status']}]",
            [toggle_label, "Edit", "Delete"],
            "Back",
        ).run()

        match opt:
            case 1:
                db.set_transaction_status(info["id"], "Pago" if is_pending else "Pendente")

            case 2:
                edit_transaction(info["id"])

            case 3:
                ppt.clear()
                confirm = ppt.Menu(
                    f"Delete transaction {info['description']}?",
                    ["Yes", "No"],
                    "Cancel",
                ).run()
                if confirm == 1:
                    db.delete_transaction(info["id"])


def choose_payment_method() -> str | None:
    options = ["Cartão", "Pix", "Boleto", "Transferência", "Outro"]
    opt = ppt.Menu("Forma de pagamento", options, "Cancel").run()
    if opt is None:
        return None
    return options[opt - 1]


def add_transaction():
    account_list = db.get_all_accounts()
    if not account_list:
        ppt.clear()
        ppt.Menu("No accounts found. Create one first.", ["OK"], "Back").run()
        return

    ppt.clear()
    account_id = pick_id_via_menu(
        "Select the Account", account_list, lambda a: f"{a['name']} ({a['bank']})"
    )
    if account_id is None:
        return

    payment_method = choose_payment_method()
    if payment_method is None:
        return

    card_id = None
    if payment_method == "Cartão":
        card_list = db.get_all_cards()
        if not card_list:
            ppt.clear()
            ppt.Menu("No cards found. Add a card or pick another method.", ["OK"], "Back").run()
            return
        ppt.clear()
        card_id = pick_id_via_menu(
            "Select the Card", card_list, lambda c: f"{c['name']} ({c['bank']})"
        )
        if card_id is None:
            return

    ppt.clear()
    result = ppt.Form(
        "New Transaction",
        [
            ("description", "Description"),
            ("amount", "Amount"),
            ("date", "Date (DD/MM/AAAA)"),
        ],
    ).run()

    if result:
        try:
            date_iso = br_to_iso(result["date"])
            db.add_transaction(
                result["description"],
                float(result["amount"].replace(",", ".")),
                date_iso,
                payment_method,
                account_id,
                card_id=card_id,
            )
        except ValueError:
            ppt.clear()
            ppt.Menu("Invalid transaction data (check amount/date).", ["OK"], "Back").run()


def edit_transaction(transaction_id: int):
    tx = db.get_transaction_by_id(transaction_id)
    if tx is None:
        return

    ppt.clear()
    result = ppt.Form(
        "Edit Transaction",
        [
            ("description", "Description"),
            ("amount", "Amount"),
            ("date", "Date (DD/MM/AAAA)"),
        ],
        default={
            "description": tx["description"],
            "amount": str(tx["amount"]),
            "date": iso_to_br(tx["date"]),
        },
    ).run()

    if result:
        try:
            date_iso = br_to_iso(result["date"])
            db.update_transaction(
                tx["id"],
                description=result["description"],
                amount=float(result["amount"].replace(",", ".")),
                date_str=date_iso,
            )
        except ValueError:
            ppt.clear()
            ppt.Menu("Invalid transaction data (check amount/date).", ["OK"], "Back").run()


# MAIN
while True:
    ppt.clear()
    opt = ppt.Menu(
        "Main Menu",
        ["Dashboard", "Bancos", "Contas", "Cartões", "Transações"],
        "Exit",
    ).run()

    match opt:
        case None:
            break

        case 1:
            ppt.clear()
            ppt.Menu("Dashboard - Coming Soon", ["OK"], "Back").run()

        case 2:
            banks()

        case 3:
            accounts()

        case 4:
            cards()

        case 5:
            transactions()