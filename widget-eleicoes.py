#!/usr/bin/env python3
# Widget descartavel: apuracao ao vivo do 2o turno presidencial 2026 (dados oficiais do TSE).
# Arraste para mover, clique no x para fechar. Atualiza a cada 30 s.
import json
import os
import threading
import urllib.request

os.environ.setdefault("GDK_BACKEND", "x11")  # permite "sempre no topo" no GNOME/Wayland

import gi
gi.require_version("Gtk", "3.0")
gi.require_version("Gdk", "3.0")
from gi.repository import Gtk, Gdk, GLib

URL = "https://resultados.tse.jus.br/oficial/ele2026/6258/dados/br/br-c0001-e006258-u.json"
INTERVALO = 30
NOMES = {"13": "Lula", "22": "Flávio Bolsonaro"}
CORES = {"13": "lula", "22": "flavio"}

CSS = b"""
window { background-color: #16181d; border-radius: 12px; }
label { color: #e8e8ea; }
.titulo { font-size: 11px; color: #9aa0aa; }
.fechar { font-size: 11px; color: #9aa0aa; padding: 0 4px; min-height: 0; min-width: 0; background: none; border: none; box-shadow: none; }
.nome { font-size: 14px; font-weight: bold; }
.pct { font-size: 20px; font-weight: bold; }
.votos { font-size: 11px; color: #9aa0aa; }
.eleito { font-size: 10px; font-weight: bold; color: #16181d; background-color: #f2c94c;
          border-radius: 4px; padding: 1px 5px; }
.rodape { font-size: 11px; color: #9aa0aa; }
progressbar trough { min-height: 6px; border-radius: 3px; background-color: #2a2d35; }
progressbar progress { min-height: 6px; border-radius: 3px; }
.lula progress { background-color: #e0393e; }
.flavio progress { background-color: #2f6fdb; }
.apuracao progress { background-color: #7c8594; }
"""


def num(s):
    return f"{int(s):,}".replace(",", ".")


def pct(s):
    return float(s.replace(",", "."))


def candidatos(no, achados):
    if isinstance(no, dict):
        if "nmu" in no and "vap" in no:
            achados.append(no)
        for v in no.values():
            candidatos(v, achados)
    elif isinstance(no, list):
        for v in no:
            candidatos(v, achados)
    return achados


class Widget(Gtk.Window):
    def __init__(self):
        super().__init__(title="Apuração 2026")
        self.set_decorated(False)
        self.set_keep_above(True)
        self.set_resizable(False)
        self.set_default_size(300, -1)
        self.set_skip_taskbar_hint(True)
        tela = self.get_screen()
        visual = tela.get_rgba_visual()
        if visual:
            self.set_visual(visual)
            self.set_app_paintable(True)

        prov = Gtk.CssProvider()
        prov.load_from_data(CSS)
        Gtk.StyleContext.add_provider_for_screen(tela, prov, Gtk.STYLE_PROVIDER_PRIORITY_APPLICATION)

        caixa = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=8)
        caixa.set_margin_top(10)
        caixa.set_margin_bottom(12)
        caixa.set_margin_start(14)
        caixa.set_margin_end(10)

        topo = Gtk.Box(spacing=6)
        self.titulo = Gtk.Label(label="2º turno · Presidente · carregando…", xalign=0)
        self.titulo.get_style_context().add_class("titulo")
        topo.pack_start(self.titulo, True, True, 0)
        fechar = Gtk.Button(label="✕")
        fechar.get_style_context().add_class("fechar")
        fechar.connect("clicked", Gtk.main_quit)
        topo.pack_end(fechar, False, False, 0)
        caixa.pack_start(topo, False, False, 0)

        self.linhas = {}
        for n in ("13", "22"):
            self.linhas[n] = self._linha_candidato(caixa, n)

        self.apuracao = Gtk.ProgressBar()
        self.apuracao.get_style_context().add_class("apuracao")
        caixa.pack_start(self.apuracao, False, False, 2)
        self.rodape = Gtk.Label(label="", xalign=0)
        self.rodape.get_style_context().add_class("rodape")
        caixa.pack_start(self.rodape, False, False, 0)

        evento = Gtk.EventBox()
        evento.add(caixa)
        evento.connect("button-press-event", self._arrastar)
        self.add(evento)

        self.connect("destroy", Gtk.main_quit)
        self.show_all()
        for linha in self.linhas.values():
            linha["eleito"].hide()
        self.move(Gdk.Screen.width() - 330, 50)

        self._buscar()
        GLib.timeout_add_seconds(INTERVALO, self._buscar)

    def _linha_candidato(self, caixa, n):
        linha = Gtk.Box(spacing=8)
        esq = Gtk.Box(orientation=Gtk.Orientation.VERTICAL)
        cab = Gtk.Box(spacing=6)
        nome = Gtk.Label(label=NOMES[n], xalign=0)
        nome.get_style_context().add_class("nome")
        cab.pack_start(nome, False, False, 0)
        eleito = Gtk.Label(label="ELEITO")
        eleito.get_style_context().add_class("eleito")
        cab.pack_start(eleito, False, False, 0)
        esq.pack_start(cab, False, False, 0)
        votos = Gtk.Label(label="", xalign=0)
        votos.get_style_context().add_class("votos")
        esq.pack_start(votos, False, False, 0)
        linha.pack_start(esq, True, True, 0)
        p = Gtk.Label(label="–", xalign=1)
        p.get_style_context().add_class("pct")
        linha.pack_end(p, False, False, 0)
        caixa.pack_start(linha, False, False, 0)
        barra = Gtk.ProgressBar()
        barra.get_style_context().add_class(CORES[n])
        caixa.pack_start(barra, False, False, 0)
        return {"pct": p, "votos": votos, "barra": barra, "eleito": eleito}

    def _arrastar(self, _w, ev):
        if ev.button == 1:
            self.begin_move_drag(ev.button, int(ev.x_root), int(ev.y_root), ev.time)

    def _buscar(self):
        threading.Thread(target=self._baixar, daemon=True).start()
        return True

    def _baixar(self):
        try:
            req = urllib.request.Request(URL, headers={"User-Agent": "widget-eleicoes"})
            with urllib.request.urlopen(req, timeout=20) as r:
                dados = json.load(r)
            GLib.idle_add(self._mostrar, dados)
        except Exception as e:
            GLib.idle_add(self._erro, str(e))

    def _mostrar(self, d):
        cands = {c["n"]: c for c in candidatos(d.get("carg", []), [])}
        for n, linha in self.linhas.items():
            c = cands.get(n)
            if not c:
                continue
            linha["pct"].set_text(c["pvap"] + "%")
            linha["votos"].set_text(num(c["vap"]) + " votos")
            linha["barra"].set_fraction(pct(c["pvap"]) / 100)
            linha["eleito"].set_visible(False)
        s = d.get("s", {})
        if s:
            self.apuracao.set_fraction(pct(s["pst"]) / 100)
        dif = ""
        if "13" in cands and "22" in cands:
            a, b = int(cands["13"]["vap"]), int(cands["22"]["vap"])
            lider = NOMES["13"] if a >= b else NOMES["22"].split()[0]
            dif = f" · {lider} +{num(abs(a - b))}"
        self.rodape.set_text(f"Seções apuradas: {s.get('pst', '–')}%{dif}")
        # "e" = candidato eleito na totalizacao; md "e" = resultado matematicamente definido
        lider = max(cands.values(), key=lambda c: int(c["vap"]), default=None)
        if lider and lider["n"] in self.linhas:
            selo = self.linhas[lider["n"]]["eleito"]
            if lider.get("e") == "s":
                selo.set_text("ELEITO")
                selo.show()
            elif d.get("md") == "e":
                selo.set_text("DEFINIDO")
                selo.show()
        definido = " · resultado definido" if d.get("md") == "e" else ""
        self.titulo.set_text(f"2º turno · TSE {d.get('ht', '')}{definido}")
        return False

    def _erro(self, msg):
        self.titulo.set_text("2º turno · sem conexão, tentando de novo…")
        return False


if __name__ == "__main__":
    Widget()
    Gtk.main()
