# Finanzierungs-Optimierung Pro

Eine interaktive Web-Anwendung zur Analyse, Optimierung und zum Vergleich von Baufinanzierungsszenarien. Dieses Tool hilft Ihnen, die Auswirkungen verschiedener Parameter wie Zinssätze, Tilgungsraten und Sondertilgungen auf Ihre Finanzierung zu verstehen.

## ✨ Features

*   **Interaktive Parameter:** Passen Sie alle relevanten Variablen über Schieberegler und Eingabefelder an und sehen Sie die Ergebnisse in Echtzeit.
*   **Szenario-Vergleich:** Speichern Sie eine Konfiguration als "Szenario A" und vergleichen Sie sie direkt mit einer aktuellen "Szenario B", um die beste Strategie zu finden.
*   **Detaillierter Tilgungsplan:** Sehen Sie eine jahresweise Aufschlüsselung von Zinsen, Tilgung und Restschuld über die gesamte Laufzeit.
*   **Restschuldberechnung:** Ermitteln Sie die exakte Restschuld am Ende Ihrer Zinsbindungsfrist.
*   **Gesamtkostenanalyse:** Berechnen Sie die Summe aller Zinszahlungen, um die wahren Kosten Ihrer Finanzierung zu verstehen.
*   **Flexible Sondertilgungen:** Planen Sie jährliche Sondertilgungen über eine Tabelle. Wählen Sie zwischen einer automatischen Verteilung auf die teuersten Kredite oder einer manuellen Zuweisung pro Kredit und Jahr. Ein Standardwert kann für die automatische Verteilung gesetzt werden.
*   **Visuelle Auswertung:** Kreisdiagramme zeigen die Aufteilung der Finanzierungsbausteine pro Partei.

## 🚀 Setup & Start

Um die Anwendung lokal auszuführen, benötigen Sie Python 3.8+ und einige Bibliotheken.

1.  **Klonen oder Herunterladen**

    Laden Sie die Datei `finanzierungs_app_pro.py` herunter oder klonen Sie das Repository.

2.  **Abhängigkeiten installieren**

    Öffnen Sie ein Terminal oder eine Kommandozeile, navigieren Sie in das Verzeichnis, in dem Sie die Datei gespeichert haben, und installieren Sie die notwendigen Bibliotheken:

    ```bash
    pip install streamlit pandas plotly
    ```

3.  **Anwendung starten**

    Führen Sie im selben Terminal den folgenden Befehl aus:

    ```bash
    streamlit run finanzierungs_app_pro.py
    ```

    Die Anwendung sollte sich automatisch in Ihrem Webbrowser öffnen.

## 🛠️ Benutzung

*   **Parameter anpassen:** Verwenden Sie die Seitenleiste (links), um alle globalen Parameter wie Gesamtkosten, Zinssätze, Tilgung und die Aufteilung der Finanzierung anzupassen.
*   **Szenario speichern:** Wenn Sie eine interessante Konfiguration gefunden haben, klicken Sie auf "Aktuelle Konfiguration als 'Szenario A' speichern". Diese Konfiguration wird fixiert.
*   **Vergleichen:** Ändern Sie nun die Parameter weiter. Die Ansicht "Szenario B (Aktuell)" wird sich live aktualisieren und Ihnen die Unterschiede zu Szenario A anzeigen.
*   **Details analysieren:** Wechseln Sie zum Tab "Detailanalyse", um die Kreditaufteilung und den vollständigen Tilgungsplan für das aktuelle Szenario (B) zu sehen.
*   **Sondertilgungen planen:** Im Expander "Sondertilgungen" können Sie zwischen automatischer und manueller Verteilung wählen.
    *   **Automatische Verteilung:** Geben Sie einen jährlichen Sondertilgungsbetrag ein. Mit "Standardwert anwenden" können Sie die Tabelle mit einem Standardwert füllen.
    *   **Manuelle Eingabe:** Weisen Sie die Sondertilgungen pro Kredit und Jahr manuell in der Tabelle zu.

**Haftungsausschluss:** Dieses Tool dient ausschließlich zu Simulations- und Demonstrationszwecken. Es stellt keine Finanzberatung dar. Alle Berechnungen sollten vor einer finanziellen Entscheidung von einem qualifizierten Fachmann überprüft werden.
