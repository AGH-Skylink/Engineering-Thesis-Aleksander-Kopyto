# Rejestr wykorzystania AI — materiał roboczy

Zakres użycia generatywnej AI należy uzgodnić z opiekunem. Nie podpisuj bez zmian poniższego tekstu; uzupełnij fakty.

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
„W trakcie przygotowania projektu korzystano z ChatGPT (OpenAI) jako narzędzia pomocniczego do porządkowania wymagań, przeglądu dokumentacji technicznej, analizy przekazanego kodu oraz przygotowania edukacyjnych przykładów testów. Każdy wykorzystany fragment poddano indywidualnej analizie i weryfikacji [opisać dokładnie]. Samodzielny wkład autora obejmuje [wypisać wyłącznie rzeczywiście wykonane działania].”

Nie ujawniaj danych poufnych laboratorium i nie przedstawiaj wyników syntetycznych jako eksperymentalnych. Pamiętaj o prawach do udostępnionego kodu historycznego.

Źródła: https://www.agh.edu.pl/pracownicy/aktualnosci/detail/wytyczne-dotyczace-odpowiedzialnego-wykorzystania-ai-w-procesie-ksztalcenia-w-agh
https://www.fis.agh.edu.pl/studenci/projekty-i-prace-dyplomowe/page

Dokumenty AGH odczytane podczas przeglądu 2026-11-10:
- [Wytyczne dotyczące odpowiedzialnego wykorzystania AI](https://www.agh.edu.pl/home/ckim/aktualnosci_i_wydarzenia/2025/0204/Wytyczne_GenAI_dla_AGH.pdf)
- [Skala wykorzystania AI w edukacji akademickiej dla AGH](https://www.agh.edu.pl/home/ckim/aktualnosci_i_wydarzenia/2025/0204/Skala_wykorzystania_AI_w_edukacji_akademickiej.pdf)
