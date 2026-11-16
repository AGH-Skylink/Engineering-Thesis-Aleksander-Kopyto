# Kontrola gotowego EXE — 2026-11-17

Wykonał agent OpenAI Codex. To weryfikacja oprogramowania na bieżącym Windows,
bez fizycznej aparatury; nie jest testem na osobnym czystym komputerze.

- Plik: `dist/NVLab.exe`, 139 059 576 bajtów.
- SHA-256: `7d9526180fb7c0e871fe4255d2577d23d86b7933e207ad1ef469e81890472504`.
- Python budowania: 3.12; PyInstaller: 6.22.3; EXE bez okna konsoli.
- Testy źródeł: **66/66 — OK**.
- `pip check`: brak niespójności zależności.
- Kontrola gotowego EXE: **OK**, z usuniętym Pythonem z PATH procesu potomnego.

Gotowy EXE ukończył cztery serie po 3 punkty: CW ODMR, Pulsed ODMR, T1 i T2 echo.
Sprawdzono zapis JSON/CSV/JSONL oraz uruchomienie interfejsu. Przycisk testu
oscyloskopu w GUI uruchomił osobny proces tego samego EXE i poprawnie pokazał
wynik IDN z lokalnego serwera SCPI. Osobno sprawdzono proces diagnostyki SG386
z rzeczywistym sterownikiem QCoDeS i lokalnym serwerem.

Raport maszynowy: `build/exe-check-20261116T230102Z/report.json` (czas w nazwie UTC).
Polecenie: `.\.venv312\Scripts\python.exe scripts/check_exe.py`.
Nie użyto adresów laboratoryjnych; serwery testowe pracowały na 127.0.0.1.

W binarium uwzględniono bieżący Help z dużym oknem diagramu i backend
`pyvisa.ctwrapper` dla zewnętrznej biblioteki VISA. Systemowe sterowniki USB/VISA
wciąż są wymagane do rzeczywistej komunikacji USB.

Autoscale, kolory kontrolek, oznaczenie SIM i zamykanie dużego schematu
zweryfikowano testami GUI; obejrzano zrzuty normalnego i powiększonego widoku.
Kontrolki są historią odpowiedzi/testu, nie ciągłym monitoringiem urządzeń.

Instrukcja: [WERSJA_EXE.md](WERSJA_EXE.md).
Weryfikacja autora i test na stanowisku: **do wykonania i zapisania przez autora**.
