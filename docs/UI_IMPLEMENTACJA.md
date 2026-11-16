# Interfejs — CW ODMR, symulatory i podgląd sekwencji

Aktualizacja 2026-11-16: domyślne okno uruchamia **CW ODMR / Symulator urządzeń**
z działającymi START/STOP/SAVE. Pełna instrukcja pomiaru, surowych danych,
ustawień i przejścia na sprzęt: [URUCHOMIENIE_ODMR.md](URUCHOMIENIE_ODMR.md).
Nowa warstwa akwizycji: `ui/acquisition.py`, silnik `experiments/cw_odmr.py`,
symulatory `hardware/simulators.py`, konfiguracja `core/odmr.py`.

Projekt wizualny pochodzi z eksportów autora w `ui/TV - 1.svg` i `ui/TV - 2.svg`.
Implementację PySide6 i testy przygotowano przy pomocy AI; szczegóły w `ETYKA_AI.md`.

## Uruchomienie

W PowerShell, z katalogu repozytorium:

```powershell
.\.venv\Scripts\python.exe -m pip install -e ".[gui]"
.\.venv\Scripts\python.exe -m nv_lab.ui
```

Jeżeli `.venv` jeszcze nie istnieje, najpierw wykonaj `python -m venv .venv`.

Projekt dopuszcza pyqtgraph od 0.13.7 do wersji poniżej 0.15. Gdy pip nie widzi
nowszych wydań, sprawdź wersję Pythona wewnątrz `.venv`, uaktualnij pip i
sprawdź konfigurację indeksu poleceniem `python -m pip config debug`.
Nie publikuj logów konfiguracji zawierających dane dostępowe do indeksu.

## Demonstracja działania bez aparatury

```powershell
.\.venv\Scripts\python.exe -m nv_lab.ui --demo
```

Tryb starej ilustracji DEMO jest wybierany przy uruchomieniu flagą. Żółty pasek, tytuł okna i wykresu
oznaczają dane syntetyczne. Zwykłe uruchomienie bez `--demo` udostępnia nowy
silnik CW z wyborem symulatora albo sprzętu; nie łączy się automatycznie z aparaturą.

1. Wybierz T1, CW ODMR lub Pulsed ODMR i kliknij START.
2. Wykres aktualizuje się co 100 ms, a konsola wypisuje postęp i symulowane
   czynności SG386, Pulse Streamera i oscyloskopu.
3. STOP zatrzymuje demonstrację z zachowaniem zebranych próbek. START rozpoczyna
   nowy przebieg. Zmiana trybu usuwa próbki poprzedniej demonstracji.
4. SAVE zapisuje ukończony lub zatrzymany przebieg do JSON. Plik zawiera
   `simulated: true`, etykietę DEMO, parametry, surowe próbki A/B i sygnał wykresu
   oraz informację `completed` odróżniającą pełny przebieg od przerwanego.
5. Przyciski testów i wykrywania VISA również symulują odpowiedzi. W DEMO nie
   uruchamiają procesów diagnostycznych ani połączeń z urządzeniami.

T1 przedstawia przykładową krzywą wykładniczą o zadanym w generatorze czasie
350 µs. To parametr ilustracji, nie wynik dopasowania. Ref. subtraction wybiera
różnicę syntetycznych A − B zamiast B. CW i Pulsed ODMR pokazują schematyczne
dołki rezonansowe o różnej szerokości. Nie jest to zweryfikowany model fizyczny
stanowiska. Wartości mocy i czasów impulsów nie sterują sprzętem ani nie
kalibrują modelu; zakresy Rabi nie są realizowane w demonstracji Pulsed ODMR.

No. points i Averages w formularzu T1 określają liczbę punktów demonstracji
(maks. 1000) i poziom sztucznego szumu, także po przełączeniu na ODMR. W ODMR
zakres osi pochodzi z Freq 1/2, a środek ilustracji z Freq. Domyślnych 50 punktów
pojawia się w około 5 s, niezależnie od rzeczywistych czasów cyklu i liczby
uśrednień. Oś Y dopasowuje się do danych; Signal Scale pozwala ustawić ją ręcznie.
Parametry są blokowane podczas przebiegu. Dane i logi DEMO służą wyłącznie
prezentacji UI i nie są dowodem działania aparatury.

## Podgląd sekwencji i akwizycja impulsowa

- Układ z Figmy: duży wykres po lewej, parametry po prawej, tryby na dole.
- Edycja parametrów i przełączanie CW ODMR / Pulsed ODMR / T1 / T2 echo.
- **PODGLĄD SEKWENCJI** używa kompilatora silnika `core/pulsed.py`; w T1 można
  wybrać Start τ lub Stop τ. T2 pokazuje również przeciwną fazę I referencji.
- T1 i Pulsed ODMR zawsze mierzą parę bez π / z π, ze wspólnymi czasami lasera
  i triggera. T2 mierzy parę końcowych faz π/2: 180° / 0°.
- Dodatkowe czasy i polaryzację lasera można rozwinąć przyciskiem pod wyborem punktu.
- Zmiana parametrów T1 usuwa poprzedni podgląd, aby nie pokazywać nieaktualnej sekwencji.
- Niepoprawny zakres, czasy ochronne i okna poza rekordem powodują błąd.
- Signal Scale określa zakres wyświetlania surowego przebiegu, nie fizyczną skalę wejścia.

Podgląd pokazuje rzeczywiste poziomy logiczne wynikające z kompilatora, z pionowymi
przesunięciami kanałów dla czytelności. Przy laserze aktywnym stanem niskim poziom 0
oznacza proponowany stan ON. Polaryzacja i czasy wymagają potwierdzenia na stanowisku.
Krótki impuls π może być widoczny jako pionowa kreska; wykres można przybliżyć.

Silniki T1/Pulsed ODMR/T2 echo działają z symulatorami i adapterami sprzętu;
fizyczna walidacja pozostaje otwarta. Okna tła, sygnału i referencji są edytowalne
w **Czasy / okna / kalibracja π** i widoczne na surowych przebiegach. Dane obu
faz, sekwencje i nastawy trafiają do JSON. Starszy `--demo` pozostaje oddzielną ilustracją.
Pochodzenie czasów: [CZASY_I_WALIDACJA.md](CZASY_I_WALIDACJA.md).

### Autoscale i Help

Przycisk **Autoscale** na zakładce sekwencji przywraca cały zakres czasu i wszystkie
kanały po przybliżeniu. Jest aktywny po poprawnym skompilowaniu sekwencji.

Zakładka **Help · sprzęt** zawiera schemat połączeń PC, Pulse Streamera, SG386,
lasera, toru MW, próbki NV, fotodetektora i oscyloskopu. HMP4040 pokazano jako
urządzenie poza bieżącą pętlą. Numery kanałów wynikają z bieżącej konfiguracji.
Schemat można otworzyć w dużym oknie, przybliżyć kółkiem myszy i przesuwać.

Kontrolki oznaczają **ostatni wynik**, bez ciągłego monitoringu: zielony —
poprawna identyfikacja/test, czerwony — błąd, szary — brak potwierdzenia,
żółty — test w toku. Dopisek SIM oznacza symulację. Zielony nie potwierdza
fizycznego światła ani mocy RF; laser sprzętowy pozostaje bez telemetrii.
Po zakończeniu pomiaru komunikacja jest opisana jako zamknięta sesja.

Domyślne VISA oscyloskopu ze starego v6:
`USB0::0x0957::0x17A4::MY53160630::INSTR`. Wcześniej zapisane ustawienia mają
pierwszeństwo; adres i numer seryjny nadal trzeba porównać z urządzeniem.
Program nie dopasowuje jeszcze wyników ani nie wyznacza pola magnetycznego.

## Konsola i testy urządzeń

Na dole okna znajduje się konsola z czasem wpisu, logami programu i wyjściem
procesu diagnostycznego. Separator nad nią pozwala zmienić wysokość panelu.
Konsola jest tylko do odczytu, ma przycisk czyszczenia i zachowuje maksymalnie
1500 linii w pamięci; nie zapisuje ich automatycznie do pliku.

Do testów potrzebne są dodatkowe zależności:

```powershell
.\.venv\Scripts\python.exe -m pip install -e ".[gui,hardware]"
```

1. W trybie **Stanowisko — sprzęt** wybierz backend VISA. `@py` jest dostępny po instalacji `hardware` i obsługuje
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

W domyślnym środowisku **Symulator urządzeń** te same przyciski testują obiekty
symulatora, bez VISA i sieci. Lista obejmuje też HMP4040 i bramkę lasera.

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
7. `src/nv_lab/ui/demo.py` zawiera oddzielny generator danych syntetycznych
   i obsługę START/STOP/SAVE przez timer Qt, bez importowania sterowników aparatury.

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
