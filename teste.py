#!/usr/bin/env python3
"""
💰 Gestor de Finanças Pessoais
Aplicativo TUI completo usando prompt_toolkit
"""

import json
import os
import sys
from datetime import datetime, date
from pathlib import Path

from prompt_toolkit import Application
from prompt_toolkit.buffer import Buffer
from prompt_toolkit.document import Document
from prompt_toolkit.filters import Condition
from prompt_toolkit.formatted_text import HTML, to_formatted_text
from prompt_toolkit.key_binding import KeyBindings
from prompt_toolkit.layout import HSplit, VSplit, Layout, Window, FloatContainer, Float
from prompt_toolkit.layout.controls import BufferControl, FormattedTextControl
from prompt_toolkit.layout.dimension import Dimension as D
from prompt_toolkit.layout.margins import ScrollbarMargin
from prompt_toolkit.styles import Style
from prompt_toolkit.widgets import (
    Box, Button, Checkbox, Dialog, Frame, Label,
    MenuContainer, MenuItem, RadioList, TextArea, VerticalLine, HorizontalLine
)

# ─── Data Storage ───────────────────────────────────────────────────────────────

DATA_FILE = Path.home() / ".finance_app_data.json"

def load_data():
    if DATA_FILE.exists():
        with open(DATA_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    return {
        "contas": [],
        "cartoes": [],
        "transacoes": [],
        "patrimonio": []
    }

def save_data(data):
    with open(DATA_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)

# ─── App State ──────────────────────────────────────────────────────────────────

class AppState:
    def __init__(self):
        self.data = load_data()
        self.current_screen = "dashboard"
        self.selected_card = None
        self.selected_month = datetime.now().strftime("%Y-%m")
        self.status_msg = ""
        self.dialog_open = False
        self.form_data = {}

state = AppState()

# ─── Helpers ────────────────────────────────────────────────────────────────────

def fmt_money(value):
    return f"R$ {value:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")

def month_label(ym):
    months = ["Jan","Fev","Mar","Abr","Mai","Jun","Jul","Ago","Set","Out","Nov","Dez"]
    y, m = ym.split("-")
    return f"{months[int(m)-1]}/{y}"

def get_months():
    now = datetime.now()
    months = []
    for i in range(5, -1, -1):
        m = now.month - i
        y = now.year
        while m <= 0:
            m += 12
            y -= 1
        months.append(f"{y}-{m:02d}")
    return months

def get_fatura(cartao_id, mes):
    total = 0.0
    items = []
    for t in state.data["transacoes"]:
        if t.get("cartao_id") == cartao_id and t.get("mes_fatura") == mes:
            total += t["valor"]
            items.append(t)
    return items, total

def get_despesas_mes(mes):
    total = 0.0
    for t in state.data["transacoes"]:
        if t.get("data", "").startswith(mes) and t["tipo"] == "despesa":
            total += t["valor"]
    return total

def get_receitas_mes(mes):
    total = 0.0
    for t in state.data["transacoes"]:
        if t.get("data", "").startswith(mes) and t["tipo"] == "receita":
            total += t["valor"]
    return total

def get_saldo_total():
    total = sum(c.get("saldo", 0) for c in state.data["contas"])
    return total

def next_id(lista):
    if not lista:
        return 1
    return max(x.get("id", 0) for x in lista) + 1

# ─── ASCII Charts ────────────────────────────────────────────────────────────────

def bar_chart(values, labels, width=50, title=""):
    if not values or max(values) == 0:
        return f"  {title}\n  (sem dados)\n"
    max_val = max(values)
    lines = [f"  {title}"]
    for i, (v, lbl) in enumerate(zip(values, labels)):
        bar_len = int((v / max_val) * width) if max_val > 0 else 0
        bar = "█" * bar_len
        lines.append(f"  {lbl:>8} │{bar:<{width}} {fmt_money(v)}")
    lines.append(f"  {'':>8} └{'─'*width}")
    return "\n".join(lines)

def sparkline(values, width=40):
    chars = " ▁▂▃▄▅▆▇█"
    if not values or max(values) == 0:
        return "─" * width
    max_v = max(values)
    result = ""
    for v in values[-width:]:
        idx = int((v / max_v) * (len(chars) - 1))
        result += chars[idx]
    return result

# ─── Screen Renderers ────────────────────────────────────────────────────────────

def render_dashboard():
    months = get_months()
    saldo = get_saldo_total()
    despesas_mes = get_despesas_mes(state.selected_month)
    receitas_mes = get_receitas_mes(state.selected_month)
    saldo_mes = receitas_mes - despesas_mes

    # Patrimônio por mês
    pat_values = []
    pat_labels = []
    for m in months:
        receitas = get_receitas_mes(m)
        despesas = get_despesas_mes(m)
        pat_values.append(max(0, receitas - despesas))
        pat_labels.append(month_label(m))

    desp_values = [get_despesas_mes(m) for m in months]
    desp_labels = [month_label(m) for m in months]

    lines = []
    lines.append("╔══════════════════════════════════════════════════════════════╗")
    lines.append("║              💰  DASHBOARD FINANCEIRO                        ║")
    lines.append("╠══════════════════════════════════════════════════════════════╣")
    lines.append(f"║  💳 Saldo Total:     {fmt_money(saldo):<41}║")
    lines.append(f"║  📅 Mês:             {month_label(state.selected_month):<41}║")
    lines.append(f"║  ✅ Receitas:        {fmt_money(receitas_mes):<41}║")
    lines.append(f"║  ❌ Despesas:        {fmt_money(despesas_mes):<41}║")
    balance_color = "+" if saldo_mes >= 0 else ""
    lines.append(f"║  📊 Saldo do Mês:    {fmt_money(saldo_mes):<41}║")
    lines.append("╚══════════════════════════════════════════════════════════════╝")
    lines.append("")
    lines.append("  ┌─ EVOLUÇÃO PATRIMONIAL (Receitas - Despesas) ────────────────")
    lines.append("")
    lines.append(bar_chart(pat_values, pat_labels, width=35, title=""))
    lines.append("")
    lines.append("  ┌─ DESPESAS MENSAIS ──────────────────────────────────────────")
    lines.append("")
    lines.append(bar_chart(desp_values, desp_labels, width=35, title=""))
    lines.append("")

    # Sparkline
    lines.append(f"  Tendência receitas: [{sparkline([get_receitas_mes(m) for m in months])}]")
    lines.append(f"  Tendência despesas: [{sparkline(desp_values)}]")
    lines.append("")

    # Contas
    if state.data["contas"]:
        lines.append("  ┌─ CONTAS ────────────────────────────────────────────────────")
        for c in state.data["contas"]:
            bar = "█" * min(20, int(c.get("saldo", 0) / 100))
            lines.append(f"  │  {c['nome']:<20} {fmt_money(c.get('saldo',0)):<15} {bar}")
        lines.append("")

    lines.append("  [1] Dashboard  [2] Contas  [3] Cartões  [4] Transações  [5] Relatórios")
    lines.append("  [A] Add Conta  [T] Add Transação  [Q] Sair")
    return "\n".join(lines)


def render_contas():
    lines = []
    lines.append("╔══════════════════════════════════════════════════════════════╗")
    lines.append("║                    🏦  CONTAS BANCÁRIAS                      ║")
    lines.append("╠══════════════════════════════════════════════════════════════╣")

    if not state.data["contas"]:
        lines.append("║  Nenhuma conta cadastrada.                                   ║")
        lines.append("║  Pressione [A] para adicionar uma conta.                     ║")
    else:
        lines.append(f"║  {'#':<4} {'Nome':<20} {'Banco':<15} {'Saldo':>12}          ║")
        lines.append("║  " + "─"*58 + "  ║")
        total = 0
        for c in state.data["contas"]:
            saldo = c.get("saldo", 0)
            total += saldo
            lines.append(f"║  {c['id']:<4} {c['nome']:<20} {c.get('banco',''):<15} {fmt_money(saldo):>12}          ║")
        lines.append("║  " + "─"*58 + "  ║")
        lines.append(f"║  {'TOTAL':<40} {fmt_money(total):>12}          ║")

    lines.append("╚══════════════════════════════════════════════════════════════╝")
    lines.append("")
    lines.append("  [A] Adicionar Conta  [E] Editar Saldo  [D] Deletar  [1] Dashboard")
    return "\n".join(lines)


def render_cartoes():
    lines = []
    lines.append("╔══════════════════════════════════════════════════════════════╗")
    lines.append("║                   💳  CARTÕES DE CRÉDITO                     ║")
    lines.append("╠══════════════════════════════════════════════════════════════╣")

    if not state.data["cartoes"]:
        lines.append("║  Nenhum cartão cadastrado.                                   ║")
        lines.append("║  Pressione [A] para adicionar um cartão.                     ║")
    else:
        for c in state.data["cartoes"]:
            items, total_fatura = get_fatura(c["id"], state.selected_month)
            limite = c.get("limite", 0)
            usado_pct = (total_fatura / limite * 100) if limite > 0 else 0
            bar_len = int(usado_pct / 5)
            bar = "█" * bar_len + "░" * (20 - bar_len)
            lines.append(f"║  💳 {c['nome']:<20} Bandeira: {c.get('bandeira',''):<12}        ║")
            lines.append(f"║     Limite: {fmt_money(limite):<12} Vencimento: dia {c.get('vencimento','?'):<4}          ║")
            lines.append(f"║     Fatura {month_label(state.selected_month)}: {fmt_money(total_fatura):<10}                       ║")
            lines.append(f"║     [{bar}] {usado_pct:.1f}%                    ║")
            lines.append("║  " + "─"*58 + "  ║")

    lines.append("╚══════════════════════════════════════════════════════════════╝")
    lines.append("")
    lines.append("  [A] Adicionar Cartão  [F] Ver Fatura  [D] Deletar")
    lines.append(f"  [<] Mês anterior  Mês atual: {month_label(state.selected_month)}  [>] Próximo mês")
    lines.append("  [1] Dashboard  [2] Contas  [4] Transações")
    return "\n".join(lines)


def render_fatura():
    if state.selected_card is None:
        return render_cartoes()

    cartao = next((c for c in state.data["cartoes"] if c["id"] == state.selected_card), None)
    if not cartao:
        return render_cartoes()

    items, total = get_fatura(state.selected_card, state.selected_month)

    lines = []
    lines.append("╔══════════════════════════════════════════════════════════════╗")
    lines.append(f"║  💳 FATURA: {cartao['nome']:<20} {month_label(state.selected_month):<10}          ║")
    lines.append("╠══════════════════════════════════════════════════════════════╣")
    lines.append(f"║  {'Data':<12} {'Descrição':<28} {'Categoria':<12} {'Valor':>8}  ║")
    lines.append("║  " + "─"*58 + "  ║")

    if not items:
        lines.append("║  Nenhum lançamento neste mês.                                ║")
    else:
        # Agrupar por categoria
        cats = {}
        for t in sorted(items, key=lambda x: x.get("data", "")):
            d = t.get("data", "")[:10]
            desc = t.get("descricao", "")[:27]
            cat = t.get("categoria", "Outros")[:11]
            val = t.get("valor", 0)
            cats[cat] = cats.get(cat, 0) + val
            lines.append(f"║  {d:<12} {desc:<28} {cat:<12} {fmt_money(val):>8}  ║")

        lines.append("║  " + "─"*58 + "  ║")
        lines.append(f"║  {'TOTAL DA FATURA':<52} {fmt_money(total):>8}  ║")
        lines.append("║                                                              ║")
        lines.append("║  Por categoria:                                              ║")
        for cat, val in sorted(cats.items(), key=lambda x: -x[1]):
            pct = val / total * 100 if total > 0 else 0
            bar = "█" * int(pct / 5)
            lines.append(f"║    {cat:<15} {fmt_money(val):>10}  {bar:<20} {pct:.0f}%      ║")

    lines.append("╚══════════════════════════════════════════════════════════════╝")
    lines.append("")
    lines.append("  [P] Adicionar pagamento  [<] Mês anterior  [>] Próximo mês")
    lines.append("  [B] Voltar aos cartões  [1] Dashboard")
    return "\n".join(lines)


def render_transacoes():
    lines = []
    lines.append("╔══════════════════════════════════════════════════════════════╗")
    lines.append("║                    📋  TRANSAÇÕES                            ║")
    lines.append(f"║  Mês: {month_label(state.selected_month):<54}║")
    lines.append("╠══════════════════════════════════════════════════════════════╣")
    lines.append(f"║  {'Data':<12} {'Tipo':<8} {'Descrição':<22} {'Categoria':<10} {'Valor':>8}  ║")
    lines.append("║  " + "─"*58 + "  ║")

    trans = [t for t in state.data["transacoes"]
             if t.get("data", "").startswith(state.selected_month) and not t.get("cartao_id")]

    if not trans:
        lines.append("║  Nenhuma transação neste mês.                                ║")
    else:
        total_rec = total_desp = 0
        for t in sorted(trans, key=lambda x: x.get("data", "")):
            d = t.get("data", "")[:10]
            tipo = "✅ REC" if t["tipo"] == "receita" else "❌ DES"
            desc = t.get("descricao", "")[:21]
            cat = t.get("categoria", "")[:9]
            val = t.get("valor", 0)
            if t["tipo"] == "receita":
                total_rec += val
            else:
                total_desp += val
            lines.append(f"║  {d:<12} {tipo:<8} {desc:<22} {cat:<10} {fmt_money(val):>8}  ║")
        lines.append("║  " + "─"*58 + "  ║")
        lines.append(f"║  {'Total Receitas':<50} {fmt_money(total_rec):>8}  ║")
        lines.append(f"║  {'Total Despesas':<50} {fmt_money(total_desp):>8}  ║")
        lines.append(f"║  {'Saldo':<50} {fmt_money(total_rec-total_desp):>8}  ║")

    lines.append("╚══════════════════════════════════════════════════════════════╝")
    lines.append("")
    lines.append("  [T] Add Transação  [<] Mês anterior  [>] Próximo mês  [1] Dashboard")
    return "\n".join(lines)


def render_relatorios():
    months = get_months()
    lines = []
    lines.append("╔══════════════════════════════════════════════════════════════╗")
    lines.append("║                    📊  RELATÓRIOS                            ║")
    lines.append("╠══════════════════════════════════════════════════════════════╣")
    lines.append("")

    # Tabela mensal
    lines.append("  RESUMO MENSAL:")
    lines.append(f"  {'Mês':<10} {'Receitas':>12} {'Despesas':>12} {'Saldo':>12} {'Tendência':>10}")
    lines.append("  " + "─"*56)

    saldos = []
    for m in months:
        rec = get_receitas_mes(m)
        desp = get_despesas_mes(m)
        saldo = rec - desp
        saldos.append(saldo)
        trend = "▲" if saldo > 0 else "▼"
        lines.append(f"  {month_label(m):<10} {fmt_money(rec):>12} {fmt_money(desp):>12} {fmt_money(saldo):>12} {trend:>10}")

    lines.append("")

    # Categorias de despesas no mês atual
    cats = {}
    for t in state.data["transacoes"]:
        if t.get("data", "").startswith(state.selected_month) and t["tipo"] == "despesa":
            cat = t.get("categoria", "Outros")
            cats[cat] = cats.get(cat, 0) + t["valor"]

    if cats:
        total_cat = sum(cats.values())
        lines.append(f"  DESPESAS POR CATEGORIA - {month_label(state.selected_month)}:")
        lines.append("")
        for cat, val in sorted(cats.items(), key=lambda x: -x[1]):
            pct = val / total_cat * 100
            bar = "█" * int(pct / 3)
            lines.append(f"  {cat:<18} {fmt_money(val):>10}  [{bar:<33}] {pct:.1f}%")

    lines.append("")
    lines.append("  CARTÕES - FATURAS DO MÊS:")
    for card in state.data["cartoes"]:
        _, fat = get_fatura(card["id"], state.selected_month)
        lim = card.get("limite", 0)
        pct = (fat / lim * 100) if lim > 0 else 0
        bar = "█" * int(pct / 5) + "░" * (20 - int(pct / 5))
        lines.append(f"  {card['nome']:<20} {fmt_money(fat):>10} / {fmt_money(lim):<10} [{bar}] {pct:.0f}%")

    lines.append("")
    lines.append("╚══════════════════════════════════════════════════════════════╝")
    lines.append("")
    lines.append("  [<] Mês anterior  [>] Próximo mês  [1] Dashboard")
    return "\n".join(lines)


def render_help():
    return """
╔══════════════════════════════════════════════════════════════╗
║                    ❓  AJUDA / ATALHOS                        ║
╠══════════════════════════════════════════════════════════════╣
║  NAVEGAÇÃO:                                                  ║
║    [1]  Dashboard (visão geral)                              ║
║    [2]  Contas bancárias                                     ║
║    [3]  Cartões de crédito                                   ║
║    [4]  Transações do mês                                    ║
║    [5]  Relatórios e gráficos                                ║
║    [?]  Esta ajuda                                           ║
║    [Q]  Sair do aplicativo                                   ║
║                                                              ║
║  AÇÕES:                                                      ║
║    [A]  Adicionar (conta, cartão, conforme a tela)           ║
║    [T]  Nova transação (receita ou despesa)                  ║
║    [P]  Novo pagamento na fatura (na tela de fatura)         ║
║    [F]  Ver fatura do cartão (na tela de cartões)            ║
║    [B]  Voltar                                               ║
║    [D]  Deletar item selecionado                             ║
║    [E]  Editar item                                          ║
║                                                              ║
║  MESES:                                                      ║
║    [<]  Mês anterior                                         ║
║    [>]  Próximo mês                                          ║
║                                                              ║
║  DADOS salvos em: ~/.finance_app_data.json                   ║
╚══════════════════════════════════════════════════════════════╝

  [1] Dashboard  [Q] Sair
"""


def get_screen_content():
    s = state.current_screen
    if s == "dashboard":
        return render_dashboard()
    elif s == "contas":
        return render_contas()
    elif s == "cartoes":
        return render_cartoes()
    elif s == "fatura":
        return render_fatura()
    elif s == "transacoes":
        return render_transacoes()
    elif s == "relatorios":
        return render_relatorios()
    elif s == "help":
        return render_help()
    return render_dashboard()


# ─── Input Dialog ────────────────────────────────────────────────────────────────

class SimpleInput:
    """Simple line-by-line input collector"""

    def __init__(self):
        self.active = False
        self.fields = []
        self.field_idx = 0
        self.values = {}
        self.title = ""
        self.callback = None
        self.buffer_text = ""

    def start(self, title, fields, callback):
        self.active = True
        self.fields = fields
        self.field_idx = 0
        self.values = {}
        self.title = title
        self.callback = callback
        self.buffer_text = ""

    def render(self):
        if not self.active:
            return ""
        field = self.fields[self.field_idx]
        lines = [
            "",
            f"  ┌─ {self.title} ({'campo ' + str(self.field_idx+1) + ' de ' + str(len(self.fields))})",
        ]
        for i, f in enumerate(self.fields):
            if i < self.field_idx:
                lines.append(f"  │  ✅ {f}: {self.values.get(f, '')}")
            elif i == self.field_idx:
                lines.append(f"  │  ▶ {f}: {self.buffer_text}█")
            else:
                lines.append(f"  │    {f}: ")
        lines.append("  │")
        lines.append("  │  [Enter] Próximo campo  [Esc] Cancelar  [Backspace] Apagar")
        lines.append("  └" + "─"*50)
        return "\n".join(lines)

    def handle_key(self, key):
        if not self.active:
            return False
        if key == "escape":
            self.active = False
            state.status_msg = "Operação cancelada."
            return True
        elif key == "enter":
            self.values[self.fields[self.field_idx]] = self.buffer_text
            self.buffer_text = ""
            self.field_idx += 1
            if self.field_idx >= len(self.fields):
                self.active = False
                if self.callback:
                    self.callback(self.values)
            return True
        elif key == "backspace":
            self.buffer_text = self.buffer_text[:-1]
            return True
        elif len(key) == 1:
            self.buffer_text += key
            return True
        return True


inp = SimpleInput()

# ─── Actions ─────────────────────────────────────────────────────────────────────

def action_add_conta(values):
    try:
        saldo = float(values.get("Saldo inicial", "0").replace(",", "."))
    except:
        saldo = 0.0
    conta = {
        "id": next_id(state.data["contas"]),
        "nome": values.get("Nome", "Conta"),
        "banco": values.get("Banco", ""),
        "saldo": saldo
    }
    state.data["contas"].append(conta)
    save_data(state.data)
    state.status_msg = f"✅ Conta '{conta['nome']}' adicionada!"


def action_add_cartao(values):
    try:
        limite = float(values.get("Limite (R$)", "0").replace(",", "."))
    except:
        limite = 0.0
    cartao = {
        "id": next_id(state.data["cartoes"]),
        "nome": values.get("Nome", "Cartão"),
        "bandeira": values.get("Bandeira", ""),
        "limite": limite,
        "vencimento": values.get("Dia vencimento", "10")
    }
    state.data["cartoes"].append(cartao)
    save_data(state.data)
    state.status_msg = f"✅ Cartão '{cartao['nome']}' adicionado!"


def action_add_transacao(values):
    tipo = values.get("Tipo (r=receita/d=despesa)", "d").lower()
    tipo = "receita" if tipo.startswith("r") else "despesa"
    try:
        valor = float(values.get("Valor (R$)", "0").replace(",", "."))
    except:
        valor = 0.0
    data_str = values.get("Data (AAAA-MM-DD)", datetime.now().strftime("%Y-%m-%d"))
    t = {
        "id": next_id(state.data["transacoes"]),
        "tipo": tipo,
        "descricao": values.get("Descrição", ""),
        "categoria": values.get("Categoria", "Outros"),
        "valor": valor,
        "data": data_str
    }
    state.data["transacoes"].append(t)
    save_data(state.data)
    state.status_msg = f"✅ Transação '{t['descricao']}' adicionada!"


def action_add_pagamento_fatura(values):
    if state.selected_card is None:
        state.status_msg = "Selecione um cartão primeiro."
        return
    try:
        valor = float(values.get("Valor (R$)", "0").replace(",", "."))
    except:
        valor = 0.0
    data_str = values.get("Data (AAAA-MM-DD)", datetime.now().strftime("%Y-%m-%d"))
    mes = data_str[:7] if len(data_str) >= 7 else state.selected_month
    t = {
        "id": next_id(state.data["transacoes"]),
        "tipo": "despesa",
        "descricao": values.get("Descrição", ""),
        "categoria": values.get("Categoria", "Cartão"),
        "valor": valor,
        "data": data_str,
        "cartao_id": state.selected_card,
        "mes_fatura": state.selected_month
    }
    state.data["transacoes"].append(t)
    save_data(state.data)
    state.status_msg = f"✅ Lançamento '{t['descricao']}' adicionado na fatura!"


def action_update_saldo(values):
    nome = values.get("Nome da conta", "")
    try:
        saldo = float(values.get("Novo saldo (R$)", "0").replace(",", "."))
    except:
        saldo = 0.0
    for c in state.data["contas"]:
        if c["nome"].lower() == nome.lower():
            c["saldo"] = saldo
            save_data(state.data)
            state.status_msg = f"✅ Saldo de '{nome}' atualizado!"
            return
    state.status_msg = f"❌ Conta '{nome}' não encontrada."


def change_month(delta):
    y, m = map(int, state.selected_month.split("-"))
    m += delta
    while m > 12:
        m -= 12
        y += 1
    while m < 1:
        m += 12
        y -= 1
    state.selected_month = f"{y}-{m:02d}"
    state.status_msg = f"Mês: {month_label(state.selected_month)}"


# ─── Key Bindings ────────────────────────────────────────────────────────────────

main_content = FormattedTextControl(text="", focusable=True)
status_bar = FormattedTextControl(text="")

def refresh_display():
    content = get_screen_content()
    if inp.active:
        content += inp.render()
    main_content.text = content
    status_text = f" {state.status_msg}" if state.status_msg else " Pronto"
    status_bar.text = f" 💰 FinanceApp | Tela: {state.current_screen.upper()} |{status_text} "

kb = KeyBindings()

@kb.add("q", filter=Condition(lambda: not inp.active))
@kb.add("Q", filter=Condition(lambda: not inp.active))
def exit_app(event):
    event.app.exit()

@kb.add("1", filter=Condition(lambda: not inp.active))
def go_dashboard(event):
    state.current_screen = "dashboard"
    state.status_msg = ""
    refresh_display()

@kb.add("2", filter=Condition(lambda: not inp.active))
def go_contas(event):
    state.current_screen = "contas"
    state.status_msg = ""
    refresh_display()

@kb.add("3", filter=Condition(lambda: not inp.active))
def go_cartoes(event):
    state.current_screen = "cartoes"
    state.selected_card = None
    state.status_msg = ""
    refresh_display()

@kb.add("4", filter=Condition(lambda: not inp.active))
def go_transacoes(event):
    state.current_screen = "transacoes"
    state.status_msg = ""
    refresh_display()

@kb.add("5", filter=Condition(lambda: not inp.active))
def go_relatorios(event):
    state.current_screen = "relatorios"
    state.status_msg = ""
    refresh_display()

@kb.add("?", filter=Condition(lambda: not inp.active))
def go_help(event):
    state.current_screen = "help"
    state.status_msg = ""
    refresh_display()

@kb.add("<", filter=Condition(lambda: not inp.active))
def prev_month(event):
    change_month(-1)
    refresh_display()

@kb.add(">", filter=Condition(lambda: not inp.active))
def next_month(event):
    change_month(1)
    refresh_display()

@kb.add("a", filter=Condition(lambda: not inp.active))
@kb.add("A", filter=Condition(lambda: not inp.active))
def action_add(event):
    if state.current_screen == "contas":
        inp.start("NOVA CONTA", ["Nome", "Banco", "Saldo inicial"],
                  lambda v: (action_add_conta(v), refresh_display()))
    elif state.current_screen == "cartoes":
        inp.start("NOVO CARTÃO", ["Nome", "Bandeira", "Limite (R$)", "Dia vencimento"],
                  lambda v: (action_add_cartao(v), refresh_display()))
    elif state.current_screen in ("dashboard", "transacoes"):
        inp.start("NOVA TRANSAÇÃO",
                  ["Tipo (r=receita/d=despesa)", "Descrição", "Valor (R$)", "Categoria",
                   "Data (AAAA-MM-DD)"],
                  lambda v: (action_add_transacao(v), refresh_display()))
    refresh_display()

@kb.add("t", filter=Condition(lambda: not inp.active))
@kb.add("T", filter=Condition(lambda: not inp.active))
def action_transacao(event):
    inp.start("NOVA TRANSAÇÃO",
              ["Tipo (r=receita/d=despesa)", "Descrição", "Valor (R$)", "Categoria",
               "Data (AAAA-MM-DD)"],
              lambda v: (action_add_transacao(v), refresh_display()))
    refresh_display()

@kb.add("e", filter=Condition(lambda: not inp.active))
@kb.add("E", filter=Condition(lambda: not inp.active))
def action_edit(event):
    if state.current_screen == "contas":
        inp.start("EDITAR SALDO", ["Nome da conta", "Novo saldo (R$)"],
                  lambda v: (action_update_saldo(v), refresh_display()))
        refresh_display()

@kb.add("f", filter=Condition(lambda: not inp.active))
@kb.add("F", filter=Condition(lambda: not inp.active))
def action_fatura(event):
    if state.current_screen == "cartoes" and state.data["cartoes"]:
        if state.selected_card is None:
            state.selected_card = state.data["cartoes"][0]["id"]
        state.current_screen = "fatura"
        state.status_msg = ""
        refresh_display()

@kb.add("p", filter=Condition(lambda: not inp.active))
@kb.add("P", filter=Condition(lambda: not inp.active))
def action_pagamento(event):
    if state.current_screen == "fatura":
        inp.start("NOVO LANÇAMENTO NA FATURA",
                  ["Descrição", "Valor (R$)", "Categoria", "Data (AAAA-MM-DD)"],
                  lambda v: (action_add_pagamento_fatura(v), refresh_display()))
        refresh_display()

@kb.add("b", filter=Condition(lambda: not inp.active))
@kb.add("B", filter=Condition(lambda: not inp.active))
def action_back(event):
    if state.current_screen == "fatura":
        state.current_screen = "cartoes"
    else:
        state.current_screen = "dashboard"
    state.status_msg = ""
    refresh_display()

@kb.add("d", filter=Condition(lambda: not inp.active))
@kb.add("D", filter=Condition(lambda: not inp.active))
def action_delete(event):
    if state.current_screen == "contas" and state.data["contas"]:
        removed = state.data["contas"].pop()
        save_data(state.data)
        state.status_msg = f"🗑️  Conta '{removed['nome']}' removida."
        refresh_display()
    elif state.current_screen == "cartoes" and state.data["cartoes"]:
        removed = state.data["cartoes"].pop()
        save_data(state.data)
        state.status_msg = f"🗑️  Cartão '{removed['nome']}' removido."
        refresh_display()

# ─── Input keys when dialog is active ────────────────────────────────────────────

for char in "abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789 .,/-_()@#$%&*+!?:":
    @kb.add(char, filter=Condition(lambda: inp.active))
    def _type(event, c=char):
        inp.handle_key(c)
        refresh_display()

@kb.add("enter", filter=Condition(lambda: inp.active))
def inp_enter(event):
    inp.handle_key("enter")
    refresh_display()

@kb.add("escape", filter=Condition(lambda: inp.active))
def inp_escape(event):
    inp.handle_key("escape")
    refresh_display()

@kb.add("c-h", filter=Condition(lambda: inp.active))  # backspace
def inp_backspace(event):
    inp.handle_key("backspace")
    refresh_display()

@kb.add("backspace", filter=Condition(lambda: inp.active))
def inp_backspace2(event):
    inp.handle_key("backspace")
    refresh_display()

# ─── Layout ──────────────────────────────────────────────────────────────────────

style = Style.from_dict({
    "frame.border": "#00aa00",
    "status": "bg:#1a472a #00ff88 bold",
    "title": "#00ff88 bold",
    "": "bg:#0d1117 #c9d1d9",
})

main_window = Window(
    content=main_content,
    wrap_lines=False,
    right_margins=[ScrollbarMargin()],
)

status_window = Window(
    content=status_bar,
    height=1,
    style="class:status",
)

layout = Layout(
    HSplit([
        main_window,
        status_window,
    ])
)

# ─── Bootstrap sample data ───────────────────────────────────────────────────────

def bootstrap_sample():
    """Add sample data if database is empty"""
    if state.data["contas"] or state.data["cartoes"]:
        return
    now = datetime.now()
    mes = now.strftime("%Y-%m")
    mes_ant = f"{now.year}-{now.month-1:02d}" if now.month > 1 else f"{now.year-1}-12"

    state.data["contas"] = [
        {"id": 1, "nome": "Conta Corrente", "banco": "Nubank", "saldo": 3500.00},
        {"id": 2, "nome": "Poupança", "banco": "Caixa", "saldo": 12000.00},
    ]
    state.data["cartoes"] = [
        {"id": 1, "nome": "Nubank Roxinho", "bandeira": "Mastercard", "limite": 5000.00, "vencimento": "10"},
        {"id": 2, "nome": "Inter Gold", "bandeira": "Visa", "limite": 3000.00, "vencimento": "15"},
    ]
    state.data["transacoes"] = [
        {"id": 1, "tipo": "receita", "descricao": "Salário", "categoria": "Trabalho", "valor": 5000.00, "data": f"{mes}-05"},
        {"id": 2, "tipo": "despesa", "descricao": "Aluguel", "categoria": "Moradia", "valor": 1200.00, "data": f"{mes}-10"},
        {"id": 3, "tipo": "despesa", "descricao": "Supermercado", "categoria": "Alimentação", "valor": 450.00, "data": f"{mes}-12"},
        {"id": 4, "tipo": "despesa", "descricao": "Internet", "categoria": "Serviços", "valor": 99.90, "data": f"{mes}-15"},
        {"id": 5, "tipo": "receita", "descricao": "Freelance", "categoria": "Trabalho", "valor": 800.00, "data": f"{mes}-18"},
        {"id": 6, "tipo": "despesa", "descricao": "Academia", "categoria": "Saúde", "valor": 89.90, "data": f"{mes}-01"},
        # Fatura cartão 1
        {"id": 7, "tipo": "despesa", "descricao": "iFood", "categoria": "Alimentação", "valor": 85.00, "data": f"{mes}-08", "cartao_id": 1, "mes_fatura": mes},
        {"id": 8, "tipo": "despesa", "descricao": "Netflix", "categoria": "Lazer", "valor": 39.90, "data": f"{mes}-10", "cartao_id": 1, "mes_fatura": mes},
        {"id": 9, "tipo": "despesa", "descricao": "Uber", "categoria": "Transporte", "valor": 45.00, "data": f"{mes}-14", "cartao_id": 1, "mes_fatura": mes},
        {"id": 10, "tipo": "despesa", "descricao": "Farmácia", "categoria": "Saúde", "valor": 120.00, "data": f"{mes}-16", "cartao_id": 1, "mes_fatura": mes},
        # Mês anterior
        {"id": 11, "tipo": "receita", "descricao": "Salário", "categoria": "Trabalho", "valor": 5000.00, "data": f"{mes_ant}-05"},
        {"id": 12, "tipo": "despesa", "descricao": "Aluguel", "categoria": "Moradia", "valor": 1200.00, "data": f"{mes_ant}-10"},
        {"id": 13, "tipo": "despesa", "descricao": "Supermercado", "categoria": "Alimentação", "valor": 380.00, "data": f"{mes_ant}-12"},
        {"id": 14, "tipo": "receita", "descricao": "Bônus", "categoria": "Trabalho", "valor": 1500.00, "data": f"{mes_ant}-20"},
    ]
    save_data(state.data)


# ─── Main ────────────────────────────────────────────────────────────────────────

def main():
    bootstrap_sample()
    refresh_display()

    app = Application(
        layout=layout,
        key_bindings=kb,
        style=style,
        full_screen=True,
        mouse_support=False,
        color_depth=None,
    )

    app.run()
    print("\n💰 FinanceApp encerrado. Até logo!\n")


if __name__ == "__main__":
    main()