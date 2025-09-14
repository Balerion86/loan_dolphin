# Loan Dolphin 🐬

Interaktive Web‑App zur Analyse, Optimierung und zum Vergleich von Baufinanzierungs­szenarien.
Loan Dolphin hilft, die Effekte von Zinssätzen, Tilgung und Sondertilgungen auf Raten,
Restschulden und Zinskosten schnell zu verstehen.

## ✨ Features

- Interaktive Parameter: Alle Eingaben in der Sidebar mit Live‑Ergebnis.
- Szenario‑Vergleich A/B: Aktuelle Konfiguration als „Szenario A“ speichern und mit „Szenario B“ vergleichen.
- Detaillierte Tilgungspläne: Jahresweise Zinsen, Tilgung, Sondertilgung, Restschuld je Kredit.
- Sondertilgung: Automatische Verteilung auf die jeweils teuersten Kredite oder manuelle Eingabe pro Kredit/Jahr.
- Kennzahlen: Gesamtrate, Zinskosten gesamt und je Partei, Restschuld nach Zinsbindung.
- Visualisierung: Kosten‑Deckung (Eigenkapital/Zuschüsse/Kredite) und gestapelte Flächen je Produkt.

## 🧭 Projektstruktur

- `app.py`: Streamlit‑Einstiegspunkt der App (Loan Dolphin).
- `core/`
  - `calculations.py`: Zuteilung, Raten, Tilgungspläne, Sondertilgungen, Kennzahlen.
  - `helpers.py`: Konstanten und Hilfsfunktionen (Key‑Mapping, DataFrame‑Utils).
- `ui/`
  - `sidebar.py`: Alle Eingaben samt Tabellen für Sondertilgung (auto/manuell).
  - `layout.py`: Vergleichs‑ und Detail‑Tabs, KPIs und Charts.
- `charts/`
  - `pies.py`, `areas.py`, `colors.py`: Plotly‑Diagramme und Farbkonzept.
- `loan_dolphin.py`: Legacy‑Datei der früheren monolithischen Version (nur Referenz).
- `make_standalone.py`: Optionales Script zur Paketierung als Einzeldatei.

## 🚀 Installation & Start

Voraussetzungen: Python 3.10+ empfohlen.

```bash
# (optional) virtuelles Environment
python -m venv .venv && source .venv/bin/activate

# Abhängigkeiten
pip install streamlit pandas plotly

# App starten
streamlit run app.py
```

Die App öffnet sich im Browser. Titel im UI: „Loan Dolphin“.

## 🧪 Tests

Es gibt fokussierte Unit‑Tests für die Kernlogik (`core/*`).

```bash
pip install pytest pandas
pytest -q
```

Abgedeckt werden u. a.:

- Zuteilungslogik und KfW‑Kappungen; Rest an Hausbank.
- Monatsraten‑Formel: `rate = summe * ((zins + tilgung) / 12)`.
- Sondertilgung (automatisch): Fließt zu den jeweils höchsten Zinssätzen.
- Restschuld nach Jahren: Aggregation über Tilgungspläne.
- Hilfsfunktionen: Key‑Mapping, Prefix‑Filter, sicheres DataFrame‑Concat.

## 🧑‍💻 Nutzung

- Parameter in der Sidebar anpassen (Kosten, Eigenkapital, Zuschüsse, Zinsen, Tilgung, KfW‑Limits).
- Sondertilgungen je Partei: Automatische Verteilung oder manuelle Eingabe pro Kredit/Jahr.
- „Szenario A“ speichern und mit der aktuellen Konfiguration („B“) vergleichen.
- In „Detailanalyse“ die Tilgungsverläufe und Anteile je Produkt betrachten.

## ⚠️ Hinweis

Loan Dolphin ist ein Simulations‑ und Lern‑Tool und ersetzt keine individuelle
Finanzberatung. Ergebnisse bitte vor Entscheidungen professionell prüfen lassen.
