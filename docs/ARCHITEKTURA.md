# Architektura referencyjna

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
