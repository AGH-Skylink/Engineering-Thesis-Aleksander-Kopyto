# Architektura referencyjna

## Stan implementacji CW ODMR — 2026-11-16

`ui/main_window.py` → `ui/acquisition.py` (wątek Qt) → `experiments/cw_odmr.py`
→ adaptery urządzeń albo `hardware/simulators.py`. Ten sam `run_cw()` realizuje
obie ścieżki. `core/odmr.py` zawiera konfigurację i rekordy pomiarowe;
`experiments/storage.py` zapisuje dziennik, surowe JSON i podsumowanie CSV.
GUI nie zawiera komend SCPI. Połączenia i pomiary są uruchamiane wyłącznie na żądanie.

CW używa lasera ciągłego i programowo parowanych RF OFF/ON, z AUTO trigger
oscyloskopu. Jest niezależne od demonstratora impulsów T1. QCoDeS obsługuje
generator, ale QCoDeS Measurement/Dataset nie jest jeszcze warstwą zapisu
(używamy jawnego JSON/CSV). Oprogramowanie nie wyznacza jeszcze pola B.

Bezpieczeństwo: `finally` zawsze próbuje wyłączyć RF oraz bramkę lasera/MW
niezależnie od błędów pozostałych urządzeń. Brak potwierdzenia jest błędem,
nie stanem READY. Realne sterowniki wymagają weryfikacji na stanowisku.

Impulsowe ODMR, T1 i T2 echo używają `experiments/pulsed.py` i wspólnego
`core/pulsed.py` do konfiguracji, kompilowania oraz okien integracji.
Ten sam silnik wywołuje symulatory albo adaptery. GUI renderuje wynik tego
samego kompilatora; starsze `core/sequences.py` pozostaje edukacyjnym wariantem
używanym przez stare `--demo`, z odmienną historyczną definicją τ.
T2 przełącza fazę ostatniego π/2 poprzez znak I; T1/Pulsed ODMR rezerwują
stały slot π w referencji. Oscyloskop: AER → RUN/seria → TER/COUN → WORD/preambuła.
Szczegóły i ograniczenia: [CZASY_I_WALIDACJA.md](CZASY_I_WALIDACJA.md).

Poniższy diagram pozostaje projektem docelowej architektury dla wszystkich eksperymentów.

```text
PySide6 GUI (plan) ──▶ Experiment Service (plan) ──▶ Device adapters
                         │                              ├── SRS SG386 / VISA
                         │                              ├── DSO-X-2014A / VISA
                         │                              ├── Pulse Streamer 8/2
                         │                              └── Thorlabs / external gate (verify)
                         ▼
                   Sequence compiler (offline demo exists)
                         │
                         ▼
                   Acquisition + processing (TODO)
                         │
                         ▼
                   QCoDeS Measurement/Dataset (TODO)
```

**Dlaczego**: eksperymenty i GUI nie powinny znać komend SCPI; sterowniki nie powinny znać semantyki T1. Kompilator sekwencji musi dać się testować bez aparatury.

## Kontrakty warstw
- `ExperimentConfig` — walidowane, jawne jednostki nanosekund i megaherców.
- `PulsePattern` — lista `(czas_ns, poziom)` oraz globalny czas trwania; osobne znaczenie poziomu logicznego i fizycznego lasera.
- `PulseBackend` — `upload(sequence)`, `start(repetitions)`, `status()`, `safe_stop()` po weryfikacji API.
- `MicrowaveSource` — `frequency_hz`, `power_dbm`, `output_enabled`, bez sekwencji operacji wpisanych na stałe w GUI.
- `Acquirer` — `arm()`, `fetch_waveform()` zwraca próbki, krok czasowy i kalibrację napięcia.
- `DatasetWriter` — zapis surowych danych, metadanych, parametry analizy.

## Schemat T1 i pomiar różnicowy
A: laser initialization → bez π → zmienne τ → readout.
B: laser initialization → π → zmienne τ → readout.
Po każdym punkcie zapisz A i B osobno, dopiero potem ich różnicę. Trzeba uzgodnić z promotorem definicję t=0 i pozycję π wobec τ; przykładowy kompilator umieszcza π na początku τ, a bez-π używa identycznego okna czasowego.

## Zatrzymanie
Zatrzymanie sprzętu nie może być wyłącznie flagą GUI. Projekt wymaga stanu bezpiecznego potwierdzonego dla laserowego TTL i mikrofal, a także `finally` przy przerwaniu / błędzie.
