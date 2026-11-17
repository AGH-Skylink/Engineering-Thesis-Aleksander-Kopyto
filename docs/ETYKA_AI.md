# Rejestr wykorzystania AI — materiał roboczy

Zakres użycia generatywnej AI należy uzgodnić z opiekunem. Nie podpisuj bez zmian poniższego tekstu; uzupełnij fakty.

## Ustalenie autora i prace z 2026-11-16

Autor poinformował w rozmowie, że promotor zgodził się na generowanie kodu przez AI,
i zlecił rozwój programu, ze szczególnym priorytetem CW ODMR oraz symulatorów.
To zapis deklaracji autora; agent nie kontaktował się z promotorem ani nie
weryfikował niezależnie treści tej zgody. Własna analiza i ocena autora pozostają
niezbędne i nie są zastępowane testami wykonywanymi przez agenta.

OpenAI Codex przygotował w tej sesji:

- model konfiguracji i danych CW ODMR, pętlę RF OFF/ON, kontrolę limitów i cleanup;
- stanowe symulatory SG386, Pulse Streamera, oscyloskopu, bramki lasera i HMP4040;
- rozbudowę przekazanego sterownika SG386, adaptery oscyloskopu i stanowiska,
  opcjonalny monitor HMP4040; bez kopiowania całych implementacji historycznych;
- wątek akwizycji Qt, ustawienia połączeń/kanałów/IQ/awarii, uporządkowanie GUI,
  postęp i podgląd surowych przebiegów, automatyczny zapis i CLI;
- testy jednostkowe, integracyjne i GUI oraz dokumentację uruchomienia i źródeł.

Wykorzystano przekazane `prace_mrozka/NV-Mariusz(1).py`, `NV-Mariusz_v6(1).py`
i fragmenty doktoratu `DOKTORSKA_MM.pdf` jako materiały referencyjne. Ich autorstwo
nie jest przypisywane autorowi nowej pracy ani agentowi. Nie uruchamiano starego
kodu i nie zmieniano tych plików. Użytkownik potwierdził odwróconą polaryzację
bramki lasera; pozostałe nastawy sprzętowe wymagają sprawdzenia na stanowisku.

Przejrzano instrukcje producentów, wskazane w [SPRZET_I_ZRODLA.md](SPRZET_I_ZRODLA.md).
Agent wykonał testy na symulatorach i lokalnych serwerach SCPI, nie na rzeczywistym
stanowisku. Symulacje i ich pliki są jawnie oznaczone. Nie powstały w tej sesji
eksperymentalne wyniki ODMR ani pomiary pola magnetycznego.

Samodzielna ocena kodu, decyzje o przyjęciu, modyfikacje autora i testy laboratoryjne:
[do uzupełnienia przez autora po przeglądzie].

Raport programowej weryfikacji agenta (Python 3.12, 44 testy i uruchomienia GUI/CLI):
[WYNIKI_TESTOW_2026-11-16.md](WYNIKI_TESTOW_2026-11-16.md). Raport nie deklaruje
przeprowadzenia własnej weryfikacji przez autora ani testu aparatury.

| Data | Narzędzie | Element | Zakres | Jak zweryfikowano / wkład własny | Decyzja |
|---|---|---|---|---|---|
| 2026-11-02 | ChatGPT GPT-6 | Struktura projektu | Konsultacja architektury, proponowane wymagania i testy | [Do uzupełnienia] | [Do uzupełnienia] |
| 2026-11-02 | ChatGPT GPT-6 | Repozytorium startowe | Przykład edukacyjny kompilatora T1 offline, testów i dokumentacji | [Do samodzielnej analizy i uruchomienia] | [Do uzupełnienia] |
| 2026-11-02 | ChatGPT GPT-6 | Konspekt pracy | Lista rozdziałów, pytań i źródeł | [Do uzupełnienia] | [Do uzupełnienia] |
| 2026-11-10 | OpenAI Codex | Test komunikacji SG386 | AI wygenerowała `check_sg386.py`, instrukcję `SG386_CONNECTION.md`, opcjonalne zależności `hardware` i wpis ignorowania metadanych pakietu; zainstalowała backend `pyvisa-py` w lokalnym `.venv`. Sterownik `sg386.py` został przekazany przez użytkownika i nie był w tej sesji modyfikowany przez AI. | Agent uruchomił test z lokalnym serwerem TCP: potwierdzono wysłanie wyłącznie `*IDN?`, `FREQ?`, `AMPR?` i odczyt odpowiedzi testowych. To nie jest walidacja na aparaturze. Samodzielna analiza kodu przez autora: [do uzupełnienia]. | Zakres dopuszczonego użycia AI i przyjęcie kodu przez autora: [do uzupełnienia]. |
| 2026-11-10 | OpenAI Codex | Diagnostyka połączenia SG386 | Agent podjął próbę połączenia przez VXI-11 i raw socket oraz sprawdził konfigurację i routing sieci. | Nie uzyskano połączenia ani odczytów z fizycznego SG386. Zaobserwowano różne podsieci komputera i podanego adresu urządzenia; przyczyna wymaga dalszego potwierdzenia. Nie wykonano pomiaru eksperymentalnego. | Test stanowiskowy i samodzielna weryfikacja autora: [do wykonania]. |
| 2026-11-10 | OpenAI Codex | Przegląd zasad użycia AI | Agent przeczytał dokumentację projektu oraz wytyczne i skalę wykorzystania AI ze strony AGH; uzupełnił niniejszy rejestr o działania z sesji. | Sprawdzono treść obu oficjalnych PDF-ów podlinkowanych poniżej. Nie potwierdzono indywidualnych ustaleń z promotorem. | Ustalenia z promotorem: [do uzupełnienia]. |

## Zasady dalszej współpracy w tym projekcie

### Implementacja interfejsu — 2026-11-10

- Narzędzie: OpenAI Codex. Materiał wejściowy: interfejs zaprojektowany przez autora
  w Figmie i przekazane eksporty SVG. Agent nie projektował tych materiałów źródłowych.
- Zakres pomocy AI: implementacja okna PySide6 i wykresów pyqtgraph, formularzy,
  walidacji i podglądu istniejącego kompilatora T1; testy GUI, zależności `gui`
  oraz dokumentacja uruchomienia. To kod wygenerowany z pomocą AI.
- Weryfikacja agenta: uruchomienie okna i pętli zdarzeń Qt, inspekcja zrzutu ekranu,
  testy trybu offline, cyklu referencyjnego, zmian parametrów i błędnych ustawień.
  Nie wykonano pomiaru ani walidacji na aparaturze.
- Własna analiza, modyfikacje i weryfikacja autora: [do uzupełnienia przez autora].
  Dopuszczony zakres pomocy AI według ustaleń z promotorem: [do uzupełnienia].

### Zasady obowiązujące przy kolejnych zmianach

Demonstracja UI 2026-11-10 (OpenAI Codex), na wyraźną prośbę autora: AI
przygotowała oddzielny tryb `--demo` z syntetycznymi przebiegami T1/CW/Pulsed
ODMR, animowanym postępem, symulowanymi logami i testami urządzeń oraz eksportem
JSON z oznaczeniem DEMO i `simulated: true`. Generowane krzywe są ilustracją
interfejsu, nie zweryfikowanym modelem stanowiska ani wynikami eksperymentu.
Weryfikacja agenta: testy startu, stopu, zmiany trybów, eksportu i oznaczeń danych,
braku uruchamiania procesów VISA w DEMO, odrzucania błędnych parametrów oraz
uruchomienie flagi `--demo` przez pętlę Qt z ukończeniem 50 punktów i inspekcją
zrzutu ekranu. Analiza kodu i ocena demonstracji przez autora: [do uzupełnienia].

Zgodność zależności 2026-11-10 (OpenAI Codex): po zgłoszonym błędzie instalacji
AI obniżyła minimalną wersję pyqtgraph z 0.14 do 0.13.7, zachowując górne
ograniczenie <0.15. Agent sprawdził metadane PyPI i uruchomił komplet 15 testów
na pyqtgraph 0.13.7 w swoim środowisku. Nie potwierdzono przyczyny ograniczenia
listy pakietów ani działania na komputerze laboratoryjnym autora (Python 3.12).

Zmiana interfejsu 2026-11-10 (OpenAI Codex), na prośbę autora: konsola logów
programu z czasem wpisu, asynchroniczne testy SG386 i oscyloskopu DSO-X 2014A,
wykrywanie VISA, przerwanie testu i limit czasu. AI wygenerowała `ui/console.py`,
`hardware/diagnostics.py`, integrację z oknem oraz testy i dokumentację.
SG386 korzysta z dotychczasowego testu sterownika; oscyloskop wysyła wyłącznie
`*IDN?`. Agent sprawdził dokumentację Qt, PyVISA i podręcznik Keysight oraz
wykonał testy z lokalnymi serwerami TCP: poprawny model, błędny model, odczyty
SG386, timeout, anulowanie, zamknięcie okna i błąd startu procesu. Obejrzano
zrzut okna. Nie potwierdzono działania na fizycznej aparaturze. Analiza kodu
i testy stanowiskowe autora: [do uzupełnienia].

Zmiana interfejsu 2026-11-10 (OpenAI Codex): na prośbę autora dodano przycisk
„Ustawienia” w prawym górnym rogu paska stanu. Panel ustawień nie jest jeszcze
zaimplementowany. Weryfikacja agenta: uruchomienie okna i sprawdzenie położenia
przycisku przy dwóch rozmiarach okna. Weryfikacja autora: [do uzupełnienia].

Poniższe zasady organizują pracę w repozytorium; nie zastępują ustaleń z promotorem ani regulacji wydziałowych.

- Pomoc AI przy generowaniu kodu, dokumentacji i analiz opisujemy zgodnie z rzeczywistym zakresem. Nie przypisujemy autorowi pracy działań wykonanych przez agenta.
- Autor samodzielnie analizuje przyjęte rozwiązania, potrafi je objaśnić i dokumentuje swoją weryfikację. Uruchomienie testu przez agenta nie oznacza weryfikacji przez autora.
- Wyniki serwera testowego lub symulacji oznaczamy jako testowe. Udane połączenie i wyniki pomiarowe deklarujemy dopiero po ich rzeczywistym uzyskaniu.
- Sprawdzamy źródła techniczne przed wykorzystaniem twierdzeń lub komend; robocza bibliografia nie jest listą przeczytanych publikacji.
- Chronimy dane osobowe, informacje poufne laboratorium i prawa do kodu źródłowego.
- Dopuszczony zakres AI ustalamy z promotorem. Skala AGH przewiduje różne poziomy wykorzystania; sama jej publikacja nie oznacza zgody na dowolny zakres w tej pracy.

## Deklaracja do uzgodnienia (przykład, nie stwierdzenie faktów)

### Uzupełnienie rejestru — T1, Pulsed ODMR i T2, 2026-11-16

Kolejne zmiany na bezpośrednią prośbę autora: przygotowano pakowanie Windows EXE
(PyInstaller, skrypt budowania i punkt wejścia bez konsoli), zachowując działanie
diagnostyki w osobnym procesie bez wymogu zainstalowanego Pythona. Dodano
historyczny adres VISA oscyloskopu, przycisk Autoscale oraz zakładkę Help ze
schematem połączeń i kontrolkami ostatniego wyniku komunikacji. Symulacja jest
oznaczona SIM; kontrolki nie są przedstawiane jako fizyczny pomiar stanu wyjść.
Testy i oglądanie interfejsu wykonuje agent; autor nadal uzupełnia własną ocenę.
Kontrolę końcowego EXE z 2026-11-17 opisuje `WYNIKI_EXE_2026-11-17.md`:
cztery serie symulatora, diagnostyka przez lokalne serwery oraz testy z Pythonem
usuniętym z PATH procesu EXE. Nie wykonano testów laboratoryjnych.

2026-11-17, zgłoszenie błędu `hdf5.dll` podczas instalacji pip: AI dodała
`--only-binary=h5py` do obu skryptów instalacji i pliku requirements oraz opisała
procedurę naprawy. Bez pełnego logu budowanie h5py ze źródeł pozostaje hipotezą.
Agent sprawdził oficjalną dokumentację h5py/pip, pobrał wheel Windows x64 dla
Pythona 3.12 i potwierdził obecność `h5py/hdf5.dll` oraz `h5py/hdf5_hl.dll`.
Lokalny import h5py działał; nie potwierdzono naprawy na komputerze użytkownika.

Na prośbę użytkownika AI przygotowała silnik pomiarów impulsowych, kompilator
sekwencji z jawną definicją czasu, okna integracji i normalizację, symulatory,
integrację GUI oraz profil oscyloskopu z zewnętrznym triggerem i WORD/LSBF.
Niejasne „drugie takie” zinterpretowano roboczo jako T2 echo Hahna, po zadaniu
pytania doprecyzowującego. T2 ma cykl fazy ostatniego π/2: 0°/180°.
Zakres nie obejmuje pomiaru Rabi, dopasowania T1/T2 ani analizy niepewności.

Agent przeczytał fragmenty wykonawcze `NV-Mariusz_v6(1).py` dotyczące czasów,
oscyloskopu, MW/I/Q i ECHO; nie uruchamiał ani nie zmieniał starych skryptów.
Sprawdził komendy i format danych w instrukcji Keysight oraz API Swabian.
Pochodzenie czasów, brak pliku PARAMETERS.txt, demonstracyjne π/π/2 i zakresy
opisano w `CZASY_I_WALIDACJA.md`. Nowe definicje τ i okna nie są przedstawiane
jako odtworzenie kalibracji promotora.

Weryfikacja agenta obejmuje testy silnika, fazowania, równych odstępów echa,
WORD/preambuły, świeżego triggera, niepełnego uśredniania, porównania WORD/ASCII,
lokalne serwery SCPI z rzeczywistym PyVISA i obiektami Sequence producenta,
przepływ GUI, zapis par przebiegów oraz oglądanie zrzutów. Podczas inspekcji
wykryto i poprawiono znikające wartości pól liczbowych przy Qt 6.12/NoButtons;
dodano kontrolę geometrii pola edycji. Zrzuty w `docs/images/` zawierają wyłącznie
dane syntetyczne. Klient Pulse Streamera w integracji jest atrapą.

Nie potwierdzono połączenia ani pomiaru na fizycznym stanowisku. Weryfikacja
autora, ustalenia dotyczące kalibracji oraz wyniki laboratoryjne: **do uzupełnienia
przez autora po rzeczywistym wykonaniu**. Szczegółowy raport testów:
`WYNIKI_TESTOW_2026-11-16.md`.
„W trakcie przygotowania projektu korzystano z ChatGPT i OpenAI Codex do porządkowania wymagań, przeglądu dokumentacji technicznej, analizy przekazanego kodu oraz generowania fragmentów interfejsu, sterowników, symulatorów, silnika CW ODMR i testów. Zakres oraz pochodzenie poszczególnych elementów opisano w rejestrze wykorzystania AI. Weryfikacja wykonana samodzielnie przez autora obejmowała [wpisać wyłącznie wykonane działania i dowody]. Samodzielny wkład autora obejmuje [wypisać wyłącznie rzeczywiście wykonane działania].”

Nie ujawniaj danych poufnych laboratorium i nie przedstawiaj wyników syntetycznych jako eksperymentalnych. Pamiętaj o prawach do udostępnionego kodu historycznego.

Źródła: https://www.agh.edu.pl/pracownicy/aktualnosci/detail/wytyczne-dotyczace-odpowiedzialnego-wykorzystania-ai-w-procesie-ksztalcenia-w-agh
https://www.fis.agh.edu.pl/studenci/projekty-i-prace-dyplomowe/page

Dokumenty AGH odczytane podczas przeglądu 2026-11-10:
- [Wytyczne dotyczące odpowiedzialnego wykorzystania AI](https://www.agh.edu.pl/home/ckim/aktualnosci_i_wydarzenia/2025/0204/Wytyczne_GenAI_dla_AGH.pdf)
- [Skala wykorzystania AI w edukacji akademickiej dla AGH](https://www.agh.edu.pl/home/ckim/aktualnosci_i_wydarzenia/2025/0204/Skala_wykorzystania_AI_w_edukacji_akademickiej.pdf)
