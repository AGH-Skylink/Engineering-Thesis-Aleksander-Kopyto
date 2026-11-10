# Specyfikacja interfejsu operatora

Pierwsza implementacja offline na podstawie eksportów z Figmy jest dostępna
w `src/nv_lab/ui`. Uruchomienie: `python -m nv_lab.ui` po instalacji zależności
`.[gui]`. Zakres, ograniczenia i instrukcja: [UI_IMPLEMENTACJA.md](UI_IMPLEMENTACJA.md).
Poniższe wymagania opisują docelowy interfejs, a nie pełny stan implementacji.

```text
● SYSTEM: OFFLINE | ○ Pulse Streamer: unknown | ○ SG386: unknown | ○ Scope: USB/VISA | ○ Laser: via PS D3 (unverified)
┌─────────────────────────────────────────┬───────────────────────┐
│             Plot: T1 signal + fit       │ Mode: [CW] [Pulse] [T1]│
│                                         │ MW freq MHz [       ] │
│                                         │ RF power dBm [       ]│
├─────────────────────────────────────────┤ τ min µs [           ]│
│  Laser   ─██───────██────────────────── │ τ max µs [           ]│
│  MW π    ───██───────────────────────── │ π pulse ns [         ]│
│  Trigger ──────────█─────────────────── │ Points [ ] Repeats [ ]│
│  Readout ───────────██───────────────── │ Reference subtraction │
└─────────────────────────────────────────┴───────────────────────┘
[PREVIEW] [VALIDATE] [START] [STOP] [SAVE]     0/50 points | T1: —
```

Wymagania: wizualizacja generowana z dokładnie tego samego planu sekwencji, który trafia do kontrolera; jawne jednostki; stany disconnected/ready/running/error; wyłączony START przy niepoprawnych parametrach; statusy wynikają z sondowania urządzeń, nie z wartości na sztywno.

Dopasowanie danych i wymiana informacji przez worker thread. Propozycja: PySide6 + pyqtgraph, nie GUI mieszane bezpośrednio z pętlą instrumentów.
