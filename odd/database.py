# database.py
"""
Database module for My_Finance application.
Handles SQLite database operations for banks, accounts, cards, and transactions.
"""

import sqlite3
from pathlib import Path
from datetime import date

DATABASE_PATH = Path(__file__).parent / "finance.db"


class Database:
    """SQLite database manager for the application."""

    def __init__(self, db_path: str | Path = DATABASE_PATH):
        self.db_path = db_path
        self._init_db()

    def _get_connection(self) -> sqlite3.Connection:
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        conn.execute("PRAGMA foreign_keys = ON")
        return conn

    def _init_db(self):
        with self._get_connection() as conn:
            cursor = conn.cursor()

            cursor.execute("""
                CREATE TABLE IF NOT EXISTS banks (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    name TEXT NOT NULL UNIQUE
                )
            """)

            cursor.execute("""
                CREATE TABLE IF NOT EXISTS accounts (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    name TEXT NOT NULL,
                    bank_id INTEGER NOT NULL,
                    value REAL NOT NULL DEFAULT 0,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (bank_id) REFERENCES banks(id) ON DELETE CASCADE
                )
            """)

            cursor.execute("""
                CREATE TABLE IF NOT EXISTS cards (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    name TEXT NOT NULL,
                    bank_id INTEGER NOT NULL,
                    FOREIGN KEY (bank_id) REFERENCES banks(id) ON DELETE CASCADE
                )
            """)

            # "transactions" replaces the old "expenses" table. It supports
            # transactions on any date, including future ("pending") ones.
            # Unlike before, `status` is a real stored column (not derived
            # from the date) so the user can manually approve a pending
            # payment, or revert a paid one back to pending.
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS transactions (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    description TEXT NOT NULL,
                    amount REAL NOT NULL,
                    date TEXT NOT NULL,
                    payment_method TEXT NOT NULL,
                    status TEXT NOT NULL DEFAULT 'Pendente' CHECK (status IN ('Pago', 'Pendente')),
                    account_id INTEGER NOT NULL,
                    card_id INTEGER,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (account_id) REFERENCES accounts(id) ON DELETE CASCADE,
                    FOREIGN KEY (card_id) REFERENCES cards(id) ON DELETE SET NULL
                )
            """)

    def _apply_account_balance(self, account_id: int, amount_delta: float) -> bool:
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                "UPDATE accounts SET value = value + ?, updated_at = CURRENT_TIMESTAMP WHERE id = ?",
                (amount_delta, account_id),
            )
            return cursor.rowcount > 0

    # ==================== BANKS ====================

    def get_all_banks(self) -> list[dict]:
        """Get all banks from the database."""
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT id, name FROM banks ORDER BY name ASC")
            return [dict(row) for row in cursor.fetchall()]

    def add_bank(self, name: str) -> dict:
        """Add a new bank."""
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("INSERT INTO banks (name) VALUES (?)", (name,))
            return {"id": cursor.lastrowid, "name": name}

    def update_bank(self, bank_id: int, name: str) -> bool:
        """Rename an existing bank."""
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("UPDATE banks SET name = ? WHERE id = ?", (name, bank_id))
            return cursor.rowcount > 0

    def delete_bank(self, bank_id: int) -> bool:
        """Delete a bank (cascades to its accounts and cards)."""
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("DELETE FROM banks WHERE id = ?", (bank_id,))
            return cursor.rowcount > 0

    def get_bank_by_id(self, bank_id: int) -> dict | None:
        """Get a specific bank by ID."""
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT id, name FROM banks WHERE id = ?", (bank_id,))
            row = cursor.fetchone()
            return dict(row) if row else None

    # ==================== ACCOUNTS ====================

    def get_all_accounts(self) -> list[dict]:
        """Get all accounts, with the linked bank's name (not just its id)."""
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                "SELECT accounts.id, accounts.name, accounts.bank_id, accounts.value, "
                "banks.name AS bank "
                "FROM accounts JOIN banks ON accounts.bank_id = banks.id "
                "ORDER BY accounts.name ASC"
            )
            return [dict(row) for row in cursor.fetchall()]

    def add_account(self, name: str, bank_id: int, value: float = 0.0) -> dict:
        """Add a new account, linked to a bank."""
        if self.get_bank_by_id(bank_id) is None:
            raise ValueError(f"Bank with id={bank_id} not found")

        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                "INSERT INTO accounts (name, bank_id, value) VALUES (?, ?, ?)",
                (name, bank_id, value),
            )
            return {"id": cursor.lastrowid, "name": name, "bank_id": bank_id, "value": value}

    def update_account(self, account_id: int, name: str = None, bank_id: int = None, value: float = None) -> bool:
        """Update an existing account."""
        fields = []
        values = []

        if name is not None:
            fields.append("name = ?")
            values.append(name)
        if bank_id is not None:
            if self.get_bank_by_id(bank_id) is None:
                raise ValueError(f"Bank with id={bank_id} not found")
            fields.append("bank_id = ?")
            values.append(bank_id)
        if value is not None:
            fields.append("value = ?")
            values.append(value)

        if not fields:
            return False

        fields.append("updated_at = CURRENT_TIMESTAMP")
        query = f"UPDATE accounts SET {', '.join(fields)} WHERE id = ?"
        values.append(account_id)

        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(query, values)
            return cursor.rowcount > 0

    def delete_account(self, account_id: int) -> bool:
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("DELETE FROM accounts WHERE id = ?", (account_id,))
            return cursor.rowcount > 0

    def get_account_by_id(self, account_id: int) -> dict | None:
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                "SELECT accounts.id, accounts.name, accounts.bank_id, accounts.value, banks.name AS bank "
                "FROM accounts JOIN banks ON accounts.bank_id = banks.id "
                "WHERE accounts.id = ?",
                (account_id,),
            )
            row = cursor.fetchone()
            return dict(row) if row else None

    # ==================== CARDS ====================

    def get_all_cards(self) -> list[dict]:
        """Get all cards, with the linked bank's name (not just its id)."""
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                "SELECT cards.id, cards.name, cards.bank_id, banks.name AS bank "
                "FROM cards JOIN banks ON cards.bank_id = banks.id "
                "ORDER BY cards.name ASC"
            )
            return [dict(row) for row in cursor.fetchall()]

    def add_card(self, name: str, bank_id: int) -> dict:
        """Create a new card linked to a single bank."""
        if self.get_bank_by_id(bank_id) is None:
            raise ValueError(f"Bank with id={bank_id} not found")

        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                "INSERT INTO cards (name, bank_id) VALUES (?, ?)",
                (name, bank_id),
            )
            return {"id": cursor.lastrowid, "name": name, "bank_id": bank_id}

    def update_card(self, card_id: int, name: str = None, bank_id: int = None) -> bool:
        fields = []
        values = []

        if name is not None:
            fields.append("name = ?")
            values.append(name)
        if bank_id is not None:
            if self.get_bank_by_id(bank_id) is None:
                raise ValueError(f"Bank with id={bank_id} not found")
            fields.append("bank_id = ?")
            values.append(bank_id)

        if not fields:
            return False

        query = f"UPDATE cards SET {', '.join(fields)} WHERE id = ?"
        values.append(card_id)

        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(query, values)
            return cursor.rowcount > 0

    def delete_card(self, card_id: int) -> bool:
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("DELETE FROM cards WHERE id = ?", (card_id,))
            return cursor.rowcount > 0

    def get_card_by_id(self, card_id: int) -> dict | None:
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                "SELECT cards.id, cards.name, cards.bank_id, banks.name AS bank "
                "FROM cards JOIN banks ON cards.bank_id = banks.id "
                "WHERE cards.id = ?",
                (card_id,),
            )
            row = cursor.fetchone()
            return dict(row) if row else None

    # ==================== TRANSACTIONS ====================
    # Replaces the old "expenses" concept. A transaction can be dated in the
    # past/today or in the future. Its `status` ("Pago" / "Pendente") is a
    # real stored column the user controls explicitly via approve/un-approve
    # actions -- it is only *defaulted* from the date when the transaction
    # is created (future date => starts Pendente, otherwise => Pago).
    # Balance is only applied to the account while status == 'Pago'.

    _TX_SELECT = (
        "SELECT transactions.id, transactions.description, transactions.amount, "
        "transactions.date, transactions.payment_method, transactions.status, "
        "transactions.account_id, transactions.card_id, "
        "accounts.name AS account_name, banks.name AS bank, "
        "cards.name AS card_name "
        "FROM transactions "
        "JOIN accounts ON transactions.account_id = accounts.id "
        "JOIN banks ON accounts.bank_id = banks.id "
        "LEFT JOIN cards ON transactions.card_id = cards.id "
    )

    def get_all_transactions(self) -> list[dict]:
        """Get all transactions, newest date first."""
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(self._TX_SELECT + "ORDER BY transactions.date DESC, transactions.id DESC")
            return [dict(row) for row in cursor.fetchall()]

    def get_transactions_by_month(self, year: int, month: int) -> list[dict]:
        """Get transactions whose date falls within the given year/month."""
        month_prefix = f"{year:04d}-{month:02d}"
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                self._TX_SELECT
                + "WHERE transactions.date LIKE ? "
                + "ORDER BY transactions.date ASC, transactions.id ASC",
                (f"{month_prefix}-%",),
            )
            return [dict(row) for row in cursor.fetchall()]

    def add_transaction(
        self,
        description: str,
        amount: float,
        date_str: str,
        payment_method: str,
        account_id: int,
        card_id: int | None = None,
        status: str | None = None,
    ) -> dict:
        """Add a new transaction (works for both past and future dates).

        `date_str` must be in ISO format (YYYY-MM-DD). If `status` isn't
        given explicitly, it defaults to 'Pago' for past/today dates and
        'Pendente' for future dates. The account balance is only debited
        when the resulting status is 'Pago'.
        """
        if amount < 0:
            raise ValueError("Transaction amount must be positive")
        if self.get_account_by_id(account_id) is None:
            raise ValueError(f"Account with id={account_id} not found")
        if card_id is not None and self.get_card_by_id(card_id) is None:
            raise ValueError(f"Card with id={card_id} not found")
        try:
            tx_date = date.fromisoformat(date_str)
        except ValueError:
            raise ValueError("Date must be in YYYY-MM-DD format")

        if status is None:
            status = "Pendente" if tx_date > date.today() else "Pago"
        elif status not in ("Pago", "Pendente"):
            raise ValueError("Status must be 'Pago' or 'Pendente'")

        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                "INSERT INTO transactions (description, amount, date, payment_method, status, account_id, card_id) "
                "VALUES (?, ?, ?, ?, ?, ?, ?)",
                (description, amount, date_str, payment_method, status, account_id, card_id),
            )
            transaction_id = cursor.lastrowid
            if status == "Pago":
                cursor.execute(
                    "UPDATE accounts SET value = value - ?, updated_at = CURRENT_TIMESTAMP WHERE id = ?",
                    (amount, account_id),
                )
            return {
                "id": transaction_id,
                "description": description,
                "amount": amount,
                "date": date_str,
                "payment_method": payment_method,
                "status": status,
                "account_id": account_id,
                "card_id": card_id,
            }

    def set_transaction_status(self, transaction_id: int, status: str) -> bool:
        """Approve ('Pago') or un-approve ('Pendente') a transaction.

        Applies or reverses the balance impact on the linked account as
        needed, so calling this is the only safe way to flip status.
        """
        if status not in ("Pago", "Pendente"):
            raise ValueError("Status must be 'Pago' or 'Pendente'")

        old = self.get_transaction_by_id(transaction_id)
        if old is None:
            return False
        if old["status"] == status:
            return True

        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                "UPDATE transactions SET status = ? WHERE id = ?",
                (status, transaction_id),
            )
            if cursor.rowcount == 0:
                return False

        if status == "Pago":
            self._apply_account_balance(old["account_id"], -old["amount"])
        else:
            self._apply_account_balance(old["account_id"], old["amount"])

        return True

    def update_transaction(
        self,
        transaction_id: int,
        description: str | None = None,
        amount: float | None = None,
        date_str: str | None = None,
        payment_method: str | None = None,
        account_id: int | None = None,
        card_id: int | None = None,
    ) -> bool:
        """Update an existing transaction's data and re-balance accounts.

        Does not change `status` -- use `set_transaction_status` for that.
        """
        old = self.get_transaction_by_id(transaction_id)
        if old is None:
            return False

        new_account_id = account_id if account_id is not None else old["account_id"]
        new_amount = amount if amount is not None else old["amount"]
        new_card_id = card_id if card_id is not None else old["card_id"]
        new_date = date_str if date_str is not None else old["date"]
        new_description = description if description is not None else old["description"]
        new_payment_method = payment_method if payment_method is not None else old["payment_method"]

        if new_amount < 0:
            raise ValueError("Transaction amount must be positive")
        if self.get_account_by_id(new_account_id) is None:
            raise ValueError(f"Account with id={new_account_id} not found")
        if new_card_id is not None and self.get_card_by_id(new_card_id) is None:
            raise ValueError(f"Card with id={new_card_id} not found")
        try:
            date.fromisoformat(new_date)
        except ValueError:
            raise ValueError("Date must be in YYYY-MM-DD format")

        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                "UPDATE transactions SET description = ?, amount = ?, date = ?, "
                "payment_method = ?, account_id = ?, card_id = ? WHERE id = ?",
                (new_description, new_amount, new_date, new_payment_method, new_account_id, new_card_id, transaction_id),
            )
            if cursor.rowcount == 0:
                return False

        # Only paid transactions affect account balances.
        if old["status"] == "Pago" and (old["account_id"] != new_account_id or old["amount"] != new_amount):
            self._apply_account_balance(old["account_id"], old["amount"])
            self._apply_account_balance(new_account_id, -new_amount)

        return True

    def delete_transaction(self, transaction_id: int) -> bool:
        """Delete a transaction and restore the linked account balance if it was paid."""
        old = self.get_transaction_by_id(transaction_id)
        if old is None:
            return False

        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("DELETE FROM transactions WHERE id = ?", (transaction_id,))
            if cursor.rowcount == 0:
                return False
            if old["status"] == "Pago":
                cursor.execute(
                    "UPDATE accounts SET value = value + ?, updated_at = CURRENT_TIMESTAMP WHERE id = ?",
                    (old["amount"], old["account_id"]),
                )
            return True

    def get_transaction_by_id(self, transaction_id: int) -> dict | None:
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                "SELECT id, description, amount, date, payment_method, status, account_id, card_id "
                "FROM transactions WHERE id = ?",
                (transaction_id,),
            )
            row = cursor.fetchone()
            return dict(row) if row else None

    def search_transactions(self, query: str) -> list[dict]:
        """Search transactions by description, account name, or card name."""
        search_term = f"%{query}%"
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                self._TX_SELECT
                + "WHERE transactions.description LIKE ? OR accounts.name LIKE ? OR cards.name LIKE ? "
                + "ORDER BY transactions.date DESC",
                (search_term, search_term, search_term),
            )
            return [dict(row) for row in cursor.fetchall()]


# Global database instance
db = Database()