# Wymagania, testy i kryteria odbioru (PROPOZYCJE — do uzgodnienia)

## Aktualizacja CW ODMR — 2026-11-16

| Element | Weryfikacja w repozytorium | Stan |
|---|---|---|
| Sweep CW z parą RF OFF/ON i surowymi przebiegami | `tests/test_odmr.py` | działa w symulatorze |
| Sterowniki SG386, Pulse Streamer, DSO-X 2014A | `tests/test_hardware_integration.py`, lokalne serwery SCPI | brak walidacji fizycznej |
| Active-low laser, I/Q i limity toru | testy stanów, readback i konfiguracji | potwierdzić oscyloskopem na stanowisku |
| STOP, awaria, błąd połączenia i cleanup | fault injection + GUI worker | testy programowe; fizyczny STOP do sprawdzenia |
| JSON/CSV/JSONL i metadane symulacji | test odczytu plików i GUI | zaimplementowane |
| Responsywne GUI, postęp i surowy przebieg | `tests/test_ui.py`, uruchomienie okna | zaimplementowane |
| T1 / Pulsed ODMR / T2 echo | `tests/test_pulsed.py`, GUI i lokalny serwer WORD | implementacja; brak walidacji fizycznej |
| Kontrola skali WORD/ASCII, AER/TER/COUN | testy adaptera | test na egzemplarzu do wykonania |

Instrukcja testu stanowiskowego: [URUCHOMIENIE_ODMR.md](URUCHOMIENIE_ODMR.md).
Poniżej zachowano pierwotny katalog wymagań docelowych; wpisy „plan” nie oznaczają
ukończenia funkcji impulsowych ani potwierdzenia pracy na aparaturze.

| ID | Wymaganie | Weryfikacja | Stan |
|---|---|---|---|
| FR-01 | Wybór CW ODMR / Pulsed ODMR / T1 / T2 | Test GUI | zaimplementowane |
| FR-02 | Konfiguracja częstotliwości i mocy MW z limitami | Testy granic + sprzęt | plan |
| FR-03 | Generator wzorców laser, MW, trigger | Testy jednostkowe | demonstrator offline |
| FR-04 | T1: pomiary referencja/π, sweep τ | Testy sekwencji + lab | działa w symulatorze; lab otwarty |
| FR-05 | Podgląd *tej samej* sekwencji co wysyłana | Porównanie danych renderera i adaptera | plan |
| FR-06 | Zapis surowych przebiegów, ratio, kontrastu i metadanych | Test odczytu datasetu | plan |
| FR-07 | Diagnostyka urządzeń i czytelny stan połączeń | Fake adapters | plan |
| FR-08 | Stop powodujący bezpieczny stan | Test fault-injection i pomiar stanów | plan |
| NFR-01 | GUI responsywne podczas pomiaru | Test uruchomienia w wątku roboczym | plan |
| NFR-02 | Deterministyczne, kwantowane czasy | Test kompilatora i limity sprzętu | plan |
| NFR-03 | Powtarzalne metadane i identyfikator pomiaru | Odtworzenie konfiguracji | plan |
| NFR-04 | Nie logować IP publicznego, haseł, informacji poufnych | Przegląd repozytorium | plan |

## Protokół testu laboratoryjnego — do wypełnienia
Data: [ ] / Operator: [ ] / Wersje software/firmware: [ ] / Stanowisko: [ ]
Połączenie D0/D1/D3/A0/A1: [ ] / Stan logiczny laser ON/OFF: [ ]
Limit RF: [ ] / Limit lasera: [ ] / Trigger oscyloskopu: [ ]
Test triggera: oczekiwane [ ], zaobserwowane [ ], dowód [ ]
Test czasu pulse: oczekiwane [ ], zaobserwowane [ ], przyrząd [ ]
Test STOP i awarii: oczekiwane [ ], zaobserwowane [ ]
T1: zakres τ [ ], punkty [ ], powtórzenia [ ], dataset [ ], rezultat [ ]
Wniosek: [ ] / Podpis opiekuna stanowiska, jeśli wymagany: [ ]

## Ryzyka z analizy wersji v6
- `preview_sequence`: laser_on=1, ale `run`: laser_on=0 (niezgodność podglądu).
- `dark_time` w T1 to nie samo τ po π; w kompilatorze używaj jawnego τ.
- `pulse.stream()` jest oczekiwany czasowo przez `sleep`, a nie monitorowany sprzętowo.
- Prosty odczyt SCPI binarnego może błędnie traktować nagłówek, signed/unsigned i scaling.
- `PARAMETERS.txt` i wiele parametrów globalnych utrudniają odtwarzalność.
- Flaga STOP nie jest natychmiastowym awaryjnym wyłączeniem.
