# Weryfikacja programowa — 2026-11-16

**Nie są to wyniki pomiaru na stanowisku.** Wszystkie przebiegi w tej sesji
pochodzą z symulatorów albo lokalnych serwerów SCPI na 127.0.0.1.
Weryfikację wykonał agent OpenAI Codex. Autor powinien osobno odnotować
swój przegląd kodu i testy laboratoryjne.

## Środowisko laboratoryjne odtworzone lokalnie

| Element | Wersja |
|---|---|
| System | Windows x64 |
| Python | 3.12.10, osobne `.venv312` |
| QCoDeS | 0.63.0 |
| PySide6 | 6.12.0 |
| pyqtgraph | 0.14.0 |
| PyVISA | 1.16.2 |
| PyVISA-py | 0.8.1 |
| pulsestreamer | 2.1.2 |

Instalacja `pip install -e ".[gui,hardware]"` zakończyła się powodzeniem.
`pip check`: **No broken requirements found**.

## Zestaw automatyczny

```powershell
.\.venv312\Scripts\python.exe -X faulthandler -m unittest discover -s tests -v
```

**66 testów — OK** (uzupełnienie prac 2026-11-16/17). Zakres:

- walidacja jednostek, ograniczeń toru i rozmiaru danych;
- sekwencje offline T1 i aktywny niski poziom lasera;
- powtarzalność i zależność sygnału symulatora od lasera, RF, I/Q i mocy;
- parowane RF OFF/ON, powtórzenia, kontrast, surowe próbki;
- konfiguracja bez referencji, błędne/obcięte dane i referencja bliska zeru;
- STOP przed połączeniem i w trakcie, błąd częściowego połączenia, awaria odczytu,
  niezależne próby wyłączenia wyjść mimo błędu innego urządzenia;
- skalowanie unsigned BYTE z preambuły, rozpoznawanie dziur i obcięcia;
- **rzeczywisty sterownik SG386/QCoDeS i adapter DSO-X/PyVISA przez lokalne
  serwery TCP**: FREQ/AMPR/ENBR, zewnętrzne I/Q, bloki IEEE 488.2 i cleanup;
  klient Pulse Streamera w tym teście jest atrapą, nie urządzeniem;
- niewłaściwy model oscyloskopu — odrzucenie bez dalszego programowania;
- GUI: sweep, surowe przebiegi, postęp, zatrzymanie, restart i zamknięcie okna;
- rozdzielenie symulacji od sprzętu oraz blokada zmiany środowiska w trakcie testu;
- zapis JSON/CSV/JSONL, odczyt metadanych i danych częściowych;
- awaria eksportu CSV: surowy JSON nadal zapisywany, błąd nie jest ukrywany;
- niepoprawna lokalna konfiguracja nie nadpisuje prawidłowych ustawień;
- starszy tryb DEMO pozostaje jawnie syntetyczny i nie uruchamia VISA.
- T1, impulsowe ODMR i T2 echo: pary, okna, fizycznie jawna definicja osi,
  equal-length referencje, zanik modelu T1/T2 i rezonans modelu ODMR;
- echo: trzy impulsy π/2–π–π/2, równe przerwy, fazy końcowe I=±0,5 V,
  analogowa siatka 8 ns oraz identyczne cyfrowe czasy obu faz;
- rzeczywiste adaptery PyVISA i vendor Sequence przez lokalny serwer WORD:
  T1 i T2, liczba powtórzeń, fazy I/Q, final OFF oraz niezależne cleanup;
- oscyloskop: skalowanie unsigned WORD, blok IEEE, AER/TER i WAV:COUN,
  odrzucenie starego triggera, niepełnego uśredniania, dziur i obcięcia;
- porównanie WORD/ASCII dla tego samego rekordu na atrapach; nie test fizycznego ADC;
- GUI: wszystkie cztery tryby, surowe pary, eksport oraz zerowanie potwierdzenia
  kalibracji; kontrola widocznej szerokości pól liczbowych przy 1000×700.
- EXE: przekazywanie argumentów diagnostyki do własnego procesu, raportowanie
  błędów bez konsoli Pythona i odrzucenie nieznanego trybu procesu pomocniczego;
- Autoscale: przywrócenie całego harmonogramu po przybliżeniu wykresu;
- Help: kontrolki po sukcesie/błędzie, oznaczenia SIM, brak telemetrii lasera,
  otwieranie i zamykanie dużego schematu oraz ponowne użycie diagramu.

Wcześniejsze testy wykonywano również w Pythonie 3.14.4 z pyqtgraph 0.13.7;
to dodatkowe sprawdzenie, nie zamiennik końcowej weryfikacji na Pythonie 3.12.

## Uruchomienia i inspekcja GUI

- Ukończono 101-punktowy sweep symulatora z rzeczywistą pętlą zdarzeń Qt,
  wyświetleniem wykresu i automatycznym zapisem.
- Obejrzano zrzuty okna pomiaru i ustawień, sprawdzono układ przy 1360×900
  i 1000×700, widoczność konsoli i brak przewijania poziomego panelu parametrów.
- CLI ukończyło krótki sweep i zapisało dane z oznaczeniem SIMULATED.
- Sprawdzono składnię skryptu PowerShell i kompilację modułów Pythona.
- `git diff --check` nie zgłosił błędów białych znaków.

Podgląd: [rzeczywisty zrzut GUI symulatora](images/cw-odmr-simulator.png).

Ukończono również 31-punktowe serie T1 i T2 w pętli Qt i obejrzano zrzuty:
[T1](images/t1-simulator.png), [T2 echo](images/t2-echo-simulator.png),
[surowe przebiegi](images/pulsed-scope-simulator.png), [harmonogram echa](images/t2-sequence.png).
Inspekcja ujawniła błąd stylu Qt: custom border/padding przy NoButtons zwężał
QLineEdit wewnątrz spinboxa do 1 px. Poprawiono styl, powtórzono inspekcję
i dodano regresję. Do renderowania offscreen jawnie załadowano lokalne fonty Windows;
platforma offscreen nie wykrywała ich automatycznie.

## Jutrzejsza walidacja fizyczna — nadal otwarta

1. Identyfikacja urządzeń, firmware i rzeczywiste adresy VISA/IP.
2. Potwierdzenie CH2 fotodetektora, laser D3 ON=LOW i toru MW/IQ.
3. Sprawdzenie skali, offsetu, sondy i podstawy czasu oscyloskopu.
4. Odczyty częstotliwości/mocy oraz rzeczywisty stan RF/bramki lasera po STOP.
5. Krótki sweep, kontrola surowych napięć i powtarzalność widma.
6. Porównanie WORD/ASCII i odczytu z panelu, sprawdzenie triggerów oraz
   niezależności uśrednień kolejnych faz na rzeczywistym firmware.
7. Kalibracja π/π/2, faz I/Q, opóźnienia lasera i okien integracji;
   porównanie T1/echo z zaufanym starym programem dla tej samej definicji czasu.

Procedura: [URUCHOMIENIE_ODMR.md](URUCHOMIENIE_ODMR.md).
