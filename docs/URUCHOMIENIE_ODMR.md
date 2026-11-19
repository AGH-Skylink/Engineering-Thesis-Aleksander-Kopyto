# ODMR, T1 i T2 — uruchomienie i test stanowiskowy

Stan implementacji: 2026-11-16. Program jest przygotowany do testów stanowiskowych,
ale nie został w tej sesji sprawdzony na fizycznej aparaturze.

Aktualizacja 2026-11-17: użytkownik zgłosił IDN **DSO-X 3034A**, SN `MY53160630`,
firmware `02.66.2024012316`. Obecny sterownik obsługuje ten model oraz 2014A;
w starszym EXE identyfikacja 3034A jest odrzucana. Użyj aktualnego EXE albo
aktualnych źródeł i ponów Test oscyloskopu. Adres USB pozostaje ten sam.

## Instalacja na komputerze laboratoryjnym

PowerShell, katalog repozytorium; Python **3.12**, nie stare środowisko 3.9:

```powershell
py -3.12 -m venv .venv312
.\.venv312\Scripts\python.exe -m pip install --upgrade pip
.\.venv312\Scripts\python.exe -m pip install --only-binary=h5py -e ".[gui,hardware]"
.\.venv312\Scripts\python.exe -m nv_lab.ui
```

Jeżeli środowisko już istnieje, wystarczy instalacja aktualnego projektu i ostatnie
polecenie. Interpreter sprawdzisz przez `.\.venv312\Scripts\python.exe --version`.
W VS Code wybierz ten sam interpreter. Stare `.venv` może nadal używać Pythona 3.9.

### Błąd `hdf5.dll` podczas instalacji pip

Jeśli komunikat pochodzi z budowania `h5py`, pip próbuje kompilować zależność
QCoDeS i wymaga wtedy osobnej biblioteki HDF5. Preferujemy gotowy wheel:

```powershell
.\.venv312\Scripts\python.exe -m pip install --upgrade pip
.\.venv312\Scripts\python.exe -m pip install --only-binary=h5py -e ".[gui,hardware]"
.\.venv312\Scripts\python.exe -c "import h5py; print(h5py.version.info)"
```

`--only-binary=h5py` blokuje kompilację tego pakietu. Jeśli pip nie znajdzie
zgodnego wheel, zgłosi to bez rozpoczynania budowy HDF5. Wtedy sprawdź pełny
log, wersję i architekturę interpretera oraz skonfigurowane źródło pakietów.
Sprawdzone środowisko projektu to Python 3.12 x64; sama nazwa `.venv312`
nie gwarantuje wersji interpretera. Nie instaluj przypadkowej DLL ręcznie.
Źródło: [h5py — zalecana instalacja gotowych pakietów](https://docs.h5py.org/en/stable/build.html).

Skrypty `Start-NVLab.ps1 -Install` i `Build-EXE.ps1 -Install` używają tej opcji.
Uruchomienie gotowego `dist/NVLab.exe` nie wymaga instalowania pakietów przez pip.

Alternatywnie: `.\scripts\Start-NVLab.ps1 -Install` przygotowuje środowisko i
uruchamia okno; później wystarcza `.\scripts\Start-NVLab.ps1`. Jeżeli polityka
PowerShell blokuje skrypt, użyj bezpośrednich poleceń powyżej zamiast zmieniać
globalne ustawienia systemu. Lista głównych wersji bibliotek ze sprawdzonego
środowiska jest w `requirements-lab-py312.txt` (nie jest to pełny lockfile).

## Dziś: pełny przepływ na symulatorach

1. Zostaw środowisko **Symulator urządzeń**. Domyślny tryb to **CW ODMR**.
2. Ustaw zakres (np. 2820–2920 MHz), 101 punktów, 3 odczyty na punkt, -30 dBm,
   20 ms ustalania i 1000 próbek na przebieg. Referencja RF OFF/ON jest domyślnie włączona.
3. Naciśnij START. Widmo, procent postępu i konsola aktualizują się w trakcie.
4. Zakładka **Oscyloskop — surowe dane** pokazuje ostatnie przebiegi RF ON/OFF.
5. Sprawdź STOP w połowie, a następnie ponowny START. Przerwanie zachowuje ukończone
   punkty; nie wylicza kontrastu z niedokończonej pary.
6. W **Ustawienia → Symulator / awarie** ustaw awarię odczytu np. nr 8. Po uruchomieniu
   program ma przejść do ERROR, zakończyć sesje i zachować częściowe dane.
7. Wyzeruj numer awarii i powtórz test. SAVE pozwala dodatkowo wyeksportować dane.

Symulatory SG386, Pulse Streamera, oscyloskopu i bramki lasera mają wspólny stan:
brak światła daje sygnał ciemny; wyłączony RF/bramka MW/IQ usuwa rezonans.
Zmiana mocy wpływa na przykładowy kontrast. Uśrednianie wykonuje rzeczywiste
powtórzenia symulowanego odczytu; nie jest wyłącznie zmianą wyglądu krzywej.
To nadal model syntetyczny, bez kalibracji na stanowisku. Dostępny jest również
niezależny czterokanałowy symulator zasilacza HMP4040, poza pętlą CW.

`--demo` uruchamia wcześniejszą ilustrację T1/Pulsed ODMR. Do sprawdzania nowego
silnika CW używaj normalnego uruchomienia i środowiska **Symulator urządzeń**.

### T1 / Pulsed ODMR / T2 echo

W normalnym uruchomieniu wybierz odpowiedni przycisk trybu. START prowadzi
rzeczywisty przepływ silnika na symulowanych urządzeniach, zapisując surowe pary.
W T1 ustaw zakres τ; w T2 ustaw całkowity czas ewolucji `t=2τ`, π i π/2.
W Pulsed ODMR ustaw zakres częstotliwości i π. Uśrednienia impulsowe są liczbą
AVER oscyloskopu: 1, 2, 4, 8, 16…; silnik wysyła serię `AVER+2` cykli.
**Podgląd sekwencji** używa dokładnie kompilatora wysyłanego do sprzętu.
**Czasy / okna / kalibracja π** otwiera konfigurację okien tła, sygnału i referencji.
Na zakładce oscyloskopu okna są zaznaczone szarym, niebieskim i zielonym pasmem.

T2 używa końcowego π/2 o fazie 0°/180° przez dodatnie/ujemne I i wymaga I/Q.
To echo Hahna, nie pomiar T2* metodą Ramseya. Brak automatycznego fitu T1/T2.
Przed startem sprzętowym konieczna jest kalibracja i potwierdzenie bieżącego trybu;
zmiana czasów, trybu, częstotliwości lub mocy unieważnia potwierdzenie.
Instrukcja i źródła czasów: [CZASY_I_WALIDACJA.md](CZASY_I_WALIDACJA.md).

## Jutro: rzeczywiste CW ODMR

### Komunikat „Please install PyUSB / No module named usb”

Wybrano backend `@py` dla adresu `USB…`, ale w interpreterze albo EXE brakuje
modułu PyUSB. Najpierw sprawdź **Ustawienia → Połączenia i dane → Biblioteka VISA**:
jeśli komputer ma NI-VISA lub Keysight IO Libraries, wybierz **systemowy NI / Keysight**,
zapisz i ponów **Test oscyloskopu**. Brak biblioteki VISA po tym wyborze oznacza,
że trzeba ją zainstalować albo skonfigurować ścieżkę `@py`.

Dla uruchomienia z Pythona zainstaluj w tym samym środowisku i uruchom aplikację ponownie:

```powershell
.\.venv312\Scripts\python.exe -m pip install pyusb libusb-package
```

Pakiet nazywa się `pyusb`, a importowany moduł `usb`. Obecny extra `hardware`
instaluje PyUSB oraz, na Windows, libusb-package. Wersja EXE musi zawierać te
moduły podczas budowania; instalacja pip na komputerze nie dopisze ich do starego EXE.

`libusb-package` dostarcza bibliotekę, ale nie zmienia sterownika przypisanego do
oscyloskopu w Windows. Nie zakładamy, że samo zainstalowanie pakietów zapewni
łączność. Jeśli oscyloskop działa w narzędziu NI/Keysight, używaj tego samego
systemowego backendu VISA. Nie zmieniamy automatycznie sterowników USB.
Źródła: [PyVISA-py — USB](https://github.com/pyvisa/pyvisa-py/blob/main/docs/source/installation.rst),
[libusb-package](https://github.com/pyocd/libusb-package).

### Przed pierwszym START

- Sprawdź okablowanie i ustaw na panelu oscyloskopu właściwą sondę, offset,
  skalę pionową oraz podstawę czasu. Signal Scale w GUI dotyczy wyłącznie
  wyświetlania surowego przebiegu, nie programuje skali fizycznego oscyloskopu.
- Wybierz **Ustawienia**, uzupełnij rzeczywiste adresy i kanał fotodetektora.
  Dla USB najprostsza jest działająca instalacja NI-VISA lub Keysight VISA
  i backend systemowy. `@py` sam w sobie obsługuje TCP/IP; USB wymaga PyUSB/libusb.
- Generator ma adres ze starego kodu `TCPIP0::192.168.0.6::inst0::INSTR`;
  Pulse Streamer `192.168.0.5`. Musi istnieć trasa sieciowa do tych urządzeń.
- Stary kod wskazuje adres oscyloskopu
  `USB0::0x0957::0x17A4::MY53160630::INSTR`. To historyczny adres, nie potwierdzenie
  identyfikatora aktualnie podłączonego egzemplarza. Użyj wykrywania VISA.
- Mapowanie historyczne: laser D3, **ON=LOW, OFF=HIGH**; MW D1, ON=HIGH;
  fotodetektor CH2. D0/CH1 służyły do triggerowania pomiarów impulsowych.
- Domyślnie włączono zewnętrzne I/Q jak w starym kodzie: SG386 `TYPE 6`, `QFNC 5`,
  I=A0=0,5 V przy MW ON, Q=A1=0 V. Wyłącz tę opcję tylko dla rzeczywiście
  przebudowanego toru bez I/Q. SG386 musi mieć odpowiednią opcję sprzętową.
- Po sprawdzeniu na stanowisku zaznacz odpowiednie potwierdzenie w ustawieniach.
  Nie jest przywracane automatycznie po restarcie aplikacji.

### Krótki pomiar kontrolny

1. Wybierz środowisko **Stanowisko — sprzęt**. Sam wybór nie łączy się z urządzeniami.
2. Wykonaj osobno Test SG386 i Test oscyloskopu; sprawdź identyfikację w konsoli.
3. Na pierwszy przebieg wybierz np. 5–11 punktów, 1 odczyt na punkt i zatwierdzoną
   moc z zakresu -50…-10 dBm. Sprawdź odczyt częstotliwości i mocy na SG386.
4. START otwiera urządzenia, sprawdza modele, wyłącza RF, ustawia stan wyjść,
   a następnie rozpoczyna pomiar. Bez odpowiedzi urządzenia program kończy się
   błędem; **nie przechodzi samoczynnie na symulację**.
5. Sprawdź surowe odczyty i skalę napięciową. Dziury w danych, przepełnienie
   wyświetlacza i referencja bliska zeru są błędami, nie poprawnymi punktami ODMR.
6. Przetestuj STOP i potwierdź fizycznie RF OFF oraz bramkę lasera OFF.
7. Dopiero po poprawnym krótkim teście zwiększ rozdzielczość i liczbę powtórzeń.

CW nie używa obecnie sekwencji impulsów ani zewnętrznego triggera. Laser pozostaje
włączony w trakcie sweepu, bramka MW i RF są przełączane dla każdej pary OFF/ON.
Oscyloskop używa AUTO trigger i świeżej akwizycji `:DIGitize` zakończonej przez
`*OPC?`, z konfiguracją NORM. Liczba odczytów w GUI oznacza powtórzenia programowe,
nie tryb AVER oscyloskopu. Skalowanie BYTE jest obliczane z pełnej preambuły.

STOP jest obsługiwany pomiędzy operacjami. Bieżąca operacja VISA może czekać do
ustawionego timeoutu; komunikacja Pulse Streamera ma timeouty klienta producenta
(10 s na wywołanie, podczas łączenia możliwe kilka wywołań). To nie jest
sprzętowy przycisk awaryjny. Przy utracie łączności nie ma gwarancji fizycznego
wyłączenia urządzenia; błędy cleanup są wyświetlane i zapisane w danych.

## Dane i odtwarzalność

W `runs/` automatycznie powstają trzy pliki z prefiksem SIM albo HW i unikalnym ID:

- `.jsonl`: dziennik startu, każdego ukończonego punktu i zakończenia. Każda linia
  jest opróżniana do systemowego bufora pliku; po awarii aplikacji można odzyskać
  wcześniejsze kompletne linie. To nie gwarancja trwałości przy utracie zasilania.
- `.json`: pełny przebieg, surowe próbki każdej akwizycji RF ON/OFF, preambuły,
  konfiguracja, identyfikatory urządzeń, jednostki, UTC, stan i błędy cleanup.
- `.csv`: podsumowanie punktów, sygnał, referencja, kontrast i SEM między
  powtórzeniami. Przy jednym powtórzeniu SEM=0 jest wartością umowną,
  a nie dowodem zerowej niepewności pomiaru.

Kontrast to `(średnia_OFF − średnia_ON) / średnia_OFF`. W JSON/CSV ma jednostkę
bezwymiarową; GUI pokazuje procent. Obie wartości napięcia są zachowane osobno.
Program nie wyznacza jeszcze dopasowania rezonansów ani wartości pola magnetycznego.
Zmiana trybu widoku nie zmienia metadanych już zakończonego pomiaru.

Awaria zapisu CSV nie blokuje próby zapisu surowego JSON. Błędy zapisu są
widoczne w GUI i w `storage_errors` rekordu pozostającego w pamięci.

Katalog `runs/` i `local_config.json` są ignorowane przez Git. Surowych wyników
i lokalnych adresów nie publikuj przypadkiem razem z kodem.

## Test bez GUI

```powershell
.\.venv312\Scripts\python.exe -m nv_lab.measurement --points 21 --averages 2 --settling-ms 0
.\.venv312\Scripts\python.exe -m unittest discover -s tests -v
```

CLI domyślnie symuluje urządzenia. Rzeczywisty pomiar wymaga `--hardware`, adresu
`--scope`, poprawnego backendu `--visa` i `--wiring-verified`; użyj `--help`.
Ctrl+C prosi o STOP i pozwala wykonać cleanup oraz zapisać dane częściowe.

## Granice obecnej wersji

- CW ODMR, Pulsed ODMR, T1 i T2 echo mają silniki, GUI i symulatory; adaptery
  fizyczne wymagają testu na stanowisku. Rabi i dopasowanie krzywych nie są zaimplementowane.
- Sterujemy bramką lasera przez Pulse Streamer, nie prądem ani mocą kontrolera.
  Dokładny aktualny model źródła/sterownika laserowego nadal nie jest ustalony.
- HMP4040 nie jest automatycznie załączany. Jest symulator oraz osobny monitor
  odczytujący napięcie/prąd, ale zasilacz nie należy do pętli CW.
- Nie przenosimy nastaw fizycznych z doktoratu na obecne stanowisko bez sprawdzenia.
- Rejestr pochodzenia kodu i zakres pomocy AI: [ETYKA_AI.md](ETYKA_AI.md).
