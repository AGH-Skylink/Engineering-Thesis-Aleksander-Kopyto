# Szkielet projektu inżynierskiego — do samodzielnego uzupełnienia

**NIE jest to tekst do oddania jako własna praca.** To propozycja układu rozdziałów, pytań badawczo-inżynierskich i dowodów wykonania. Ostateczny tytuł i strukturę uzgodnij z promotorem i zasadami WFiIS.

## Strona tytułowa, streszczenie PL/EN, słowa kluczowe
- [ ] Uzupełnij według aktualnego wzoru WFiIS; bez fikcyjnych rezultatów.
- Proponowane słowa kluczowe: NV centers, ODMR, T1 relaxation, QCoDeS, synchronization, instrument control.

## 1. Wstęp (orientacyjnie 3–5 stron)
1.1 Kontekst: automatyzacja laboratoryjnych pomiarów centrów NV.
1.2 Problem inżynierski: powtarzalna synchronizacja i zapis parametrów pomiarów.
1.3 Cel i zakres: system operatora + sterowanie + analiza + walidacja.
1.4 Kryteria sukcesu i ograniczenia zakresu.
**Uzupełnij:** motywację laboratorium, faktyczny stan wyjściowy, uzgodnione cele, informację o autorstwie starszego kodu.

## 2. Podstawy teoretyczne (orientacyjnie 7–11 stron)
2.1 Defekt azot–wakancja NV⁻, poziomy spinowe, zeropolowe rozszczepienie ~2,87 GHz (wartość zależna od warunków).
2.2 Optyczna polaryzacja i fluorescencyjny odczyt stanu spinowego.
2.3 CW ODMR: jednoczesny laser/MW, sweep po częstotliwości.
2.4 Pulsed ODMR i oscylacje Rabiego: impuls i kalibracja π/π2.
2.5 Relaksacja podłużna T1: sweep czasu τ; pomiar różnicowy i modele relaksacji.
2.6 Jakie są źródła błędów: jitter, rozdzielczość sekwencji, okno integracji, dryft, nieliniowości, czas martwy.
**Uzupełnij:** równania wyprowadzone i omówione samodzielnie, ich założenia, cytowania z publikacji pierwotnych.

## 3. Analiza stanowiska i starego oprogramowania (5–8 stron)
3.1 Inwentaryzacja: rzeczywiste modele/wersje firmware, porty i połączenia.
3.2 Diagram sygnałowy: Pulse Streamer D0 trigger, D1 MW gate, D3 laser/shutter, A0/A1 I/Q — **odczyt ze starego kodu, do zweryfikowania**.
3.3 Funkcje `NV-Mariusz.py`, `NV-Mariusz_v6.py`: eksperymenty, GUI, dane wejściowe i wyjściowe.
3.4 Problemy kodu: monolit, rozbieżność inwersji lasera w preview, zapis TXT, oczekiwanie przez sleep, walidacja danych, brak bezpiecznego sprzętowego stop.
**Uzupełnij:** fotografie i schematy własne z zezwoleniem laboratorium, tabela rozbieżności i wyników inspekcji.

## 4. Wymagania i projekt oprogramowania (8–12 stron)
4.1 Wymagania funkcjonalne i niefunkcjonalne z identyfikatorami.
4.2 Architektura warstwowa (GUI / experiment engine / drivers / storage).
4.3 Model danych i stany eksperymentu (IDLE, ARMED, RUNNING, STOPPING, ERROR).
4.4 Generator impulsów, walidacja, mapowanie urządzeń, aktywny niski laser.
4.5 Koncepcja synchronizacji: PS master, trigger oscyloskopu, akwizycja i integracja okien.
4.6 Przepływ danych, przechowywanie i metadane, zakres odpowiedzialności QCoDeS.
4.7 Projekt GUI, komunikaty błędów i mechanizm bezpiecznego przerwania.
**Uzupełnij:** własne decyzje, diagramy, uzasadnienie wyboru technologii i kompromisy.

## 5. Implementacja (6–10 stron)
5.1 Repozytorium i środowisko, wersje bibliotek.
5.2 Adapter SG386 i VISA scope (po weryfikacji SCPI).
5.3 Integracja Pulse Streamera (API właściwej wersji).
5.4 Implementacja generatora sekwencji i walidatora.
5.5 Implementacja CW ODMR i T1, przetwarzanie surowego przebiegu.
5.6 Interfejs operatora oraz zapis datasetów.
**Uzupełnij:** tylko rzeczywiście napisany, objaśniony i uruchomiony kod; wycinki kodu opatrz pochodzeniem.

## 6. Testy i wyniki (8–12 stron)
6.1 Strategia testowa — jednostkowe, integracyjne, stanowiskowe.
6.2 Testy offline sekwencji T1, wartości brzegowych i błędów.
6.3 Testy portów: readback parametrów, trigger, sekwencje stanów logicznych.
6.4 Porównanie starej i nowej implementacji na identycznym eksperymencie.
6.5 Wyniki i niepewności T1 / ODMR **tylko po realnym wykonaniu**.
6.6 Dyskusja ograniczeń, wiarygodności i odtwarzalności.
**Wstaw:** daty, identyfikatory datasetów, jednostki, osie, konfigurację, surowe logi i protokoły.

## 7. Wnioski (2–3 strony)
- [ ] Które wymagania zrealizowano? Dowód z rozdziału 6.
- [ ] Co rzeczywiście zmieniło się względem starego programu?
- [ ] Co pozostaje ograniczeniem / propozycją dalszego rozwoju?

## Bibliografia / aneksy
- Bibliografia — każda teza techniczna do sprawdzonego źródła.
- Aneks A: architektura i schemat połączeń; Aneks B: wzorce sekwencji; Aneks C: procedury testowe; Aneks D: deklaracja wykorzystania AI jeśli uzgodniona.

## Lista elementów własnego wkładu
[ ] analiza wymagań [ ] decyzje architektoniczne [ ] implementacja sterowników [ ] GUI [ ] testy bezsprzętowe [ ] eksperymenty [ ] ocena wyników [ ] wnioski.
