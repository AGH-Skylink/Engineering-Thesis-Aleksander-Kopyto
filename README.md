# NV Lab Automation — pakiet roboczy inżynierki

**Status: propozycja architektury i kod edukacyjny wygenerowany przy wsparciu ChatGPT (GPT-6), 2026-11-02.**
Nie jest to ukończona implementacja, ani oprogramowanie zweryfikowane na sprzęcie.

## Cel
Budowa modułowego programu do automatyzacji eksperymentów NV: CW ODMR, pulsed ODMR i T1, z QCoDeS, Pulse Streamer 8/2, SRS SG386, oscyloskopem oraz GUI PySide6.

## Co działa w tym pakiecie
- Bezsprzętowy generator harmonogramu **ideowej** sekwencji T1 i kontrola nieujemnych czasów.
- Eksport sekwencji do reprezentacji wzorców kanałów (bez przesyłania do sprzętu).
- Testy jednostkowe standardowym `unittest`.
- Demo CLI pokazujące czasy impulsów; **brak pomiarów rzeczywistych i brak symulowanych odczytów udających aparaturę**.

## Co jeszcze nie działa
- Faktyczne połączenia QCoDeS / VISA / Pulse Streamer, synchronizacja oscyloskopu, CW ODMR, detekcja, dopasowanie T1, GUI. W repozytorium są kontrakty i TODO, nie gotowe sterowniki.
- Parametry lasera, polaryzacja bramkowania, opóźnienia torów, rzeczywiste okna detekcji i dopasowanie muszą zostać ustalone w laboratorium.

## Pierwsze kroki
```bash
python -m unittest discover -s tests -v
PYTHONPATH=src python -m nv_lab.demo
```
W Windows PowerShell: `$env:PYTHONPATH='src'; python -m nv_lab.demo`.

## Zasady bezpieczeństwa
Uruchomienie w trybie sprzętowym wymaga zatwierdzonych limitów, weryfikacji okablowania i polaryzacji wejść oraz zgody opiekuna stanowiska. W projekcie **nie ma żadnego automatycznego połączenia z aparaturą**.

## Geneza
Materiały źródłowe: dwa pliki `NV-Mariusz*.py` udostępnione przez użytkownika; przeglądane jako kod referencyjny. Nie są dołączone do paczki z uwagi na potencjalne prawa i poufność; wykorzystanie lub publikację kodu historycznego uzgodnij z promotorem.

Spis plików: `docs/PRACA_INZYNIERSKA.md`, `docs/ARCHITEKTURA.md`, `docs/WYMAGANIA_I_TESTY.md`, `docs/LITERATURA.md`, `docs/ETYKA_AI.md`, `docs/GUI_SPEC.md`, `docs/SPOTKANIE_Z_PROMOTOREM.md`.
