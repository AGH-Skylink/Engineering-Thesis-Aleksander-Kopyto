# Wersja Windows EXE

Uruchom **`dist/NVLab.exe`** dwuklikiem. Python nie musi być zainstalowany.
Program startuje w trybie symulatora; sam nie łączy się z aparaturą.
Aktualizacja 2026-11-17: obsługiwane są DSO-X 3034A (zgłoszony na stanowisku)
oraz 2014A. Stara wersja odrzucała IDN 3034A. Przed podmianą EXE zamknij
poprzednią uruchomioną wersję; pip nie aktualizuje zawartości gotowego EXE.
W zakładce sekwencji jest **Autoscale**, a **Help · sprzęt** pokazuje schemat
z zielonymi/czerwonymi kontrolkami ostatniego testu oraz osobnym oznaczeniem SIM.
Pełną procedurę sprzętową opisuje [URUCHOMIENIE_ODMR.md](URUCHOMIENIE_ODMR.md).

Możesz skopiować pojedynczy EXE do własnego zapisywalnego katalogu, np.
`Dokumenty/NVLab`. Dane powstają w `runs/` obok EXE; ustawienia w
`local_config.json`. Katalog pomiarów można zmienić w Ustawieniach.
Do komunikacji USB ze sprzętem nadal potrzebna jest biblioteka NI-VISA lub
Keysight VISA zainstalowana w Windows (wybierz backend systemowy), albo zgodny
sterownik urządzenia dla PyUSB/libusb (backend @py). Aktualne pakowanie dołącza
PyUSB i DLL libusb; nie instaluje ani nie zmienia sterownika USB w Windows.

Adresy historyczne ze starego kodu v6 są już wpisane w ustawieniach:

- SG386: `TCPIP0::192.168.0.6::inst0::INSTR`.
- Oscyloskop: `USB0::0x0957::0x17A4::MY53160630::INSTR`.
- Pulse Streamer: `192.168.0.5`.

Adres oscyloskopu zawiera numer seryjny; porównaj go z urządzeniem na stanowisku.
Własna zapisana konfiguracja ma pierwszeństwo przed wartościami domyślnymi.

## Ponowne zbudowanie po zmianach kodu

W PowerShell, w folderze projektu:

```powershell
.\scripts\Build-EXE.ps1 -Install
```

Kolejne budowanie bez instalacji zależności:

```powershell
.\scripts\Build-EXE.ps1
```

Pakowanie używa PyInstaller 6.22.3, Pythona 3.12 i `NVLab.spec`.
Biblioteki Qt, QCoDeS, PyVISA/PyVISA-py i Pulse Streamera są w EXE.
Sterowniki USB/VISA systemu nie są dołączane. Sam projekt źródłowy, prace
promotora, lokalna konfiguracja i wyniki pomiarów nie są pakowane.

Wersja bez konsoli uruchamia diagnostykę jako proces tego samego EXE,
z osobnym raportem tymczasowym odczytywanym do konsoli GUI. Nie wymaga
uruchamiania `python.exe` na komputerze docelowym.
Decyzje dotyczące `sys.executable`, trybu windowed i `freeze_support` sprawdzono
w [dokumentacji PyInstaller](https://pyinstaller.org/en/stable/common-issues-and-pitfalls.html).

Wewnętrzne `NVLab.exe --smoke-test <nowy-katalog>` wykonuje cztery krótkie serie
wyłącznie w symulatorze i zapisuje raport, surowe pliki oraz zrzut okna.
Test ten nie jest kalibracją ani walidacją aparatury.

Pełna kontrola EXE przez lokalne serwery testowe (wymaga źródeł i środowiska
deweloperskiego, nie jest potrzebna do zwykłego uruchamiania programu):

```powershell
.\.venv312\Scripts\python.exe scripts/check_exe.py
```

Test usuwa Pythona z PATH procesu EXE, wykonuje cztery serie symulacyjne,
sprawdza zapis plików i diagnostykę oscyloskopu z GUI w osobnym procesie oraz
sterownik SG386 na localhost. Raport i SHA-256 trafiają do `build/exe-check-…`.
Nie otwiera żadnej sesji z fizyczną aparaturą laboratoryjną.
