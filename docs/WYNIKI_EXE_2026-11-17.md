# Kontrola gotowego EXE — 2026-11-17

Wykonał agent OpenAI Codex. To weryfikacja oprogramowania na bieżącym Windows,
bez fizycznej aparatury; nie jest testem na osobnym czystym komputerze.

- Plik: `dist/NVLab.exe`, 139 664 086 bajtów (aktualizacja USB i 3034A).
- SHA-256: `0d947625e3c7fd35610da2762b908f305b61f84aee18c24be667c7c5b55e89dc`.
- Python budowania: 3.12; PyInstaller: 6.22.3; EXE bez okna konsoli.
- Testy źródeł: **73/73 — OK**.
- `pip check`: brak niespójności zależności.
- Kontrola gotowego EXE: **OK**, z usuniętym Pythonem z PATH procesu potomnego.

Gotowy EXE ukończył cztery serie po 3 punkty: CW ODMR, Pulsed ODMR, T1 i T2 echo.
Sprawdzono zapis JSON/CSV/JSONL oraz uruchomienie interfejsu. Przycisk testu
oscyloskopu w GUI uruchomił osobny proces tego samego EXE i poprawnie pokazał
wynik IDN z lokalnego serwera SCPI. Osobno sprawdzono proces diagnostyki SG386
z rzeczywistym sterownikiem QCoDeS i lokalnym serwerem.

Raport maszynowy: `build/exe-check-20261117T195629Z/report.json` (czas w nazwie UTC).
Polecenie: `.\.venv312\Scripts\python.exe scripts/check_exe.py`.
Nie użyto adresów laboratoryjnych; serwery testowe pracowały na 127.0.0.1.

W binarium uwzględniono bieżący Help z dużym oknem diagramu i backend
`pyvisa.ctwrapper` dla zewnętrznej biblioteki VISA. Systemowe sterowniki USB/VISA
wciąż są wymagane do rzeczywistej komunikacji USB.

W aktualizacji po zgłoszeniu IDN użytkownika dodano DSO-X 3034A obok 2014A.
Serwer testowy oscyloskopu przedstawiał się jako Agilent DSO-X3034A; nowy EXE
zaakceptował tę odpowiedź w diagnostyce GUI. Sprawdzono import dołączonego
PyUSB 1.3.1 i rzeczywiste załadowanie backendu DLL libusb z libusb-package
1.0.30.1 przy PATH ograniczonym do katalogów systemu Windows. To nie jest
test zgodności sterownika USB ani akwizycji na fizycznym urządzeniu.

Autoscale, kolory kontrolek, oznaczenie SIM i zamykanie dużego schematu
zweryfikowano testami GUI; obejrzano zrzuty normalnego i powiększonego widoku.
Kontrolki są historią odpowiedzi/testu, nie ciągłym monitoringiem urządzeń.

Instrukcja: [WERSJA_EXE.md](WERSJA_EXE.md).
Weryfikacja autora i test na stanowisku: **do wykonania i zapisania przez autora**.
