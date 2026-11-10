# Interfejs — podgląd offline i diagnostyka komunikacji

Projekt wizualny pochodzi z eksportów autora w `ui/TV - 1.svg` i `ui/TV - 2.svg`.
Implementację PySide6 i testy przygotowano przy pomocy AI; szczegóły w `ETYKA_AI.md`.

## Uruchomienie

W PowerShell, z katalogu repozytorium:

```powershell
.\.venv\Scripts\python.exe -m pip install -e ".[gui]"
.\.venv\Scripts\python.exe -m nv_lab.ui
```

Jeżeli `.venv` jeszcze nie istnieje, najpierw wykonaj `python -m venv .venv`.

## Co można sprawdzić

- Układ z Figmy: duży wykres po lewej, parametry po prawej, tryby na dole.
- Edycję parametrów i przełączanie CW ODMR / Pulsed ODMR / T1.
- W T1 przycisk **PODGLĄD T1** generuje przebiegi logiczne dla Start τ lub Stop τ.
- **Ref. subtraction** dodaje do podglądu tor MW cyklu bez π. Czasy lasera i triggera
  są wspólne dla obu cykli. W tej wersji nie ma danych do odejmowania.
- Dodatkowe czasy i polaryzację lasera można rozwinąć przyciskiem pod wyborem punktu.
- Zmiana parametrów T1 usuwa poprzedni podgląd, aby nie pokazywać nieaktualnej sekwencji.
- Start τ większe niż Stop τ, impuls π większy niż Start τ (ograniczenie obecnego
  kompilatora) lub trigger dłuższy niż odczyt powodują komunikat błędu.
- Signal Scale określa symetryczny zakres osi Y pustego wykresu pomiarowego.

Podgląd pokazuje rzeczywiste poziomy logiczne wynikające z kompilatora, z pionowymi
przesunięciami kanałów dla czytelności. Przy laserze aktywnym stanem niskim poziom 0
oznacza proponowany stan ON. Polaryzacja i czasy wymagają potwierdzenia na stanowisku.
Krótki impuls π może być widoczny jako pionowa kreska; wykres można przybliżyć.

START, STOP i SAVE są nieaktywne. Połączenia diagnostyczne są uruchamiane wyłącznie
na żądanie z konsoli opisanej poniżej. Program nie wykonuje akwizycji ani
dopasowania i nie tworzy wyników pomiarowych. No. points, Averages,
częstotliwość i moc pozostają parametrami roboczymi. Podgląd nie realizuje całego
sweepu. Tryby ODMR mają na tym etapie formularze, bez wykonania eksperymentu.

## Konsola i testy urządzeń

Na dole okna znajduje się konsola z czasem wpisu, logami programu i wyjściem
procesu diagnostycznego. Separator nad nią pozwala zmienić wysokość panelu.
Konsola jest tylko do odczytu, ma przycisk czyszczenia i zachowuje maksymalnie
1500 linii w pamięci; nie zapisuje ich automatycznie do pliku.

Do testów potrzebne są dodatkowe zależności:

```powershell
.\.venv\Scripts\python.exe -m pip install -e ".[gui,hardware]"
```

1. Wybierz backend VISA. `@py` jest dostępny po instalacji `hardware` i obsługuje
   TCP/IP. Backend systemowy wymaga osobnej instalacji NI-VISA lub Keysight VISA.
2. W polu SG386 wpisz pełny adres VISA albo IP (sam IP używa portu TCP 5025).
   Przycisk **Test SG386** uruchamia istniejący test sterownika QCoDeS:
   `*IDN?`, `FREQ?`, `AMPR?`.
3. W polu oscyloskopu wpisz jego rzeczywisty adres VISA. **Wykryj VISA** wypisuje
   dostępne zasoby; odpowiedni adres trzeba skopiować do pola. Wykrywanie nie
   oznacza, że wszystkie urządzenia sieciowe muszą znaleźć się na liście.
4. **Test oscyloskopu** wysyła tylko `*IDN?` i sprawdza model DSO-X 2014A.
   Nie uruchamia akwizycji, resetu ani autoskalowania.
5. Odczytaj odpowiedzi i wynik w konsoli. Każdy test zamyka sesję po zakończeniu.
   Status „test OK (sesja zamknięta)” potwierdza jednorazową komunikację,
   nie gotowość całego stanowiska do pomiaru.

USB w backendzie `@py` wymaga dodatkowo PyUSB (`python -m pip install pyusb`),
libusb i zgodnego sterownika USB. Sama instalacja `pyvisa-py` nie wystarcza.
Nie zmieniamy automatycznie sterowników USB w systemie. Jeżeli oscyloskop jest
już obsługiwany przez NI/Keysight VISA, wybierz backend systemowy.

Test działa w osobnym procesie przez `QProcess`, a komunikaty trafiają do GUI
przez sygnały Qt. Interfejs pozostaje aktywny. **Przerwij test** kończy proces;
limit całego testu wynosi 30 s. Zamknięcie okna także kończy aktywny test.
Żaden test nie startuje automatycznie przy uruchomieniu aplikacji.

## Jak czytać kod

1. `src/nv_lab/ui/__main__.py` tworzy aplikację Qt i uruchamia pętlę zdarzeń.
2. `src/nv_lab/ui/main_window.py` buduje okno, formularze i wykresy.
3. `set_mode()` przełącza formularze, `invalidate_preview()` usuwa stary podgląd.
4. `show_preview()` przelicza µs na całkowite ns, waliduje dane i wywołuje
   istniejące `compile_t1()`. GUI nie definiuje własnego przebiegu eksperymentu.
5. `tests/test_ui.py` sprawdza tryb offline, cykle referencyjne, zmiany parametrów
   i odrzucanie błędnych ustawień. Sprawdza także konsolę i rzeczywisty proces
   diagnostyczny z lokalnym serwerem TCP, bez kontaktu z aparaturą. Bez opcjonalnych
   bibliotek odpowiednie testy są pomijane.
6. `src/nv_lab/ui/console.py` wyświetla logi z loggerów `nv_lab.*` i uruchamia
   diagnostykę. `src/nv_lab/hardware/diagnostics.py` odpowiada za wykrywanie VISA
   i identyfikację oscyloskopu; kod okna nie zawiera komend aparatury.

```powershell
.\.venv\Scripts\python.exe -m unittest discover -s tests -v
```

Do samodzielnej weryfikacji autora: uruchomić okno, zmienić τ, porównać granice
impulsów z `compile_t1()`, przełączyć polaryzację i uzasadnić konwersję jednostek.
Wyniki tej weryfikacji należy dopisać do rejestru AI.

Dokumentacja techniczna:
- [Qt for Python: QDoubleSpinBox](https://doc.qt.io/qtforpython-6/PySide6/QtWidgets/QDoubleSpinBox.html)
- [Qt for Python: QStackedWidget](https://doc.qt.io/qtforpython-6.11/PySide6/QtWidgets/QStackedWidget.html)
- [pyqtgraph 0.14: PlotItem](https://pyqtgraph.readthedocs.io/en/pyqtgraph-0.14.0/api_reference/graphicsItems/plotitem.html)
- [Qt for Python: QProcess](https://doc.qt.io/qtforpython-6/PySide6/QtCore/QProcess.html)
- [PyVISA: komunikacja z urządzeniem](https://pyvisa.readthedocs.io/en/latest/introduction/communication.html)
- [PyVISA-py: wymagania interfejsów, w tym USB](https://pyvisa.readthedocs.io/projects/pyvisa-py/en/latest/installation.html)
- [Keysight InfiniiVision 2000 X-Series Programmer's Guide, *IDN?, s. 147](https://www.keysight.com/cd/en/assets/9018-06893/programming-guides/9018-06893.pdf)
