# Kish Eureka Autoclicker

Kish Eureka Autoclicker è uno strumento di automazione scritto in Python pensato per creare facilmente sequenze di input su Windows, macOS, Linux e distribuzioni similari. Offre un'interfaccia grafica moderna per comporre scenari complessi con il mouse e la tastiera, mantenendo al contempo una CLI minimale per gli utilizzi più rapidi o gli script personalizzati.

## Funzionalità principali

- **Interfaccia moderna**: una dashboard scura e appagante, con componenti ottimizzati per schermi ad alta densità, per organizzare e riordinare le azioni con semplicità.
- **Sequenze ricche**: supporto a click singoli o ripetuti, spostamenti del cursore, trascinamenti, pressioni di tasti (anche in combinazione), digitazione di testo, pause temporizzate e scroll verticale/orizzontale.
- **Motore riutilizzabile**: le azioni sono modellate come oggetti importabili; puoi orchestrare le stesse sequenze dalla tua applicazione Python senza utilizzare la GUI.
- **Compatibilità multipiattaforma**: utilizza `pyautogui` come backend principale e `pynput` come fallback per garantire l'esecuzione sui principali sistemi operativi desktop.
- **Modalità CLI classica**: per scenari veloci resta disponibile l'autoclicker tradizionale parametrizzabile da terminale.
- **Countdown programmabile**: imposta un ritardo iniziale per preparare l'ambiente prima dell'avvio, sia in GUI sia con il flag `--countdown` da terminale.
- **Libreria di sequenze**: salva e ricarica le automazioni in formato JSON per riutilizzarle e condividerle rapidamente.
- **Cattura rapida delle coordinate**: popola i campi di click, spostamento e trascinamento con la posizione corrente del cursore in un solo gesto.

## Requisiti

- Python 3.9 o superiore.
- [pyautogui](https://pyautogui.readthedocs.io/en/latest/) (consigliata).
- [pynput](https://pynput.readthedocs.io/en/latest/) come alternativa quando `pyautogui` non è presente.

Installa le dipendenze tramite:

```bash
pip install -r requirements.txt
```

## Avvio rapido

### Interfaccia grafica

Avvia la GUI moderna con:

```bash
python -m autoclicker --gui
```

Dalla finestra principale puoi:

1. Scegliere il tipo di azione (click, spostamento, trascinamento, tasti, digitazione, attesa, scroll).
2. Compilare i parametri dedicati (coordinate, pulsante, durata, testo, ecc.) o catturarli in tempo reale con i nuovi pulsanti di acquisizione.
3. Salvare e caricare sequenze JSON per creare una piccola libreria di automazioni.
4. Aggiungere la voce alla sequenza, riordinare l'elenco e salvare eventuali modifiche.
5. Avviare la riproduzione scegliendo intervallo fra le azioni, modalità loop e countdown iniziale.

### Linea di comando

Per i casi in cui basta un autoclicker tradizionale è possibile usare la CLI:

```bash
python -m autoclicker --interval 0.1 --button left --count 100
```

Parametri disponibili:

- `--interval`: intervallo tra i click (secondi, default `0.1`).
- `--button`: pulsante del mouse (`left`, `right`, `middle`).
- `--count`: numero massimo di click da eseguire.
- `--duration`: durata massima in secondi.
- `--countdown`: ritardo iniziale in secondi prima di iniziare a cliccare.
- `--gui`: apre l'interfaccia grafica invece della modalità CLI.

Premi `Ctrl+C` per interrompere la modalità a tempo indeterminato.

## Sviluppo e integrazione

Puoi importare le azioni per riutilizzarle in altri script Python:

```python
from autoclicker import ActionEngine, ClickAction, KeyPressAction, WaitAction

engine = ActionEngine(interval=0.2)
actions = [
    ClickAction(x=400, y=420, clicks=2),
    WaitAction(seconds=0.5),
    KeyPressAction(keys=("ctrl", "s")),
]
engine.start(actions)
```

Il motore accetterà automaticamente l'hardware disponibile (`pyautogui` oppure `pynput`).

## Stato del progetto

La versione corrente include l'interfaccia grafica completa, la CLI e il motore riutilizzabile. Sono benvenuti feedback, suggerimenti per nuove azioni e contributi di design o codice.

## Idee implementate

- Countdown iniziale per prepararsi all'avvio della sequenza senza correre.
- Salvataggio e caricamento di sequenze in JSON per costruire una libreria personale.
- Pulsanti di cattura rapida per riempire le coordinate direttamente dal cursore.
