# Skąd czasy i jak sprawdzić pomiar

Stan: 2026-11-16. Implementacja i testy programowe wykonane przy pomocy AI.
Nie wykonano walidacji na fizycznym stanowisku. Zgoda promotora na kodowanie
nie oznacza zatwierdzenia parametrów fizycznych.

## Pochodzenie wartości

| Parametr | Wartość robocza | Pochodzenie i ograniczenie |
|---|---:|---|
| Inicjalizacja / laser odczytu | 2 ms | `laser_time=2000000` w `prace_mrozka/NV-Mariusz_v6(1).py`, linia 387. Nowy cykl ma osobną inicjalizację i odczyt. |
| Trigger | 300 ns | `tr_time=300`, linia 390 tego samego kodu. |
| Guard I/Q, wyprzedzenie triggera | 500 ns | `laser_delay=500`, linia 391; intencja ochrony I/Q i wyzwalania przed odczytem. Nie zmierzono aktualnych opóźnień optycznych. |
| Laser TTL | ON=0, OFF=1 | Kod wykonawczy i potwierdzenie użytkownika. Wizualizacja starego kodu ma inną polaryzację. |
| π | 100 ns | Wartość demonstracyjna. Stary program wczytuje `PIPULSE` z brakującego `PARAMETERS.txt`; stałe `mw_time=500` nie są dowodem kalibracji π. |
| π/2 | 50 ns | Wartość demonstracyjna; historyczne `PI2PULSE` również pochodziło z brakującego pliku. Nie zakładamy kalibracji z samego stosunku 1:2. |
| Sweep T1 | 100–1000 µs | Zakres demonstracyjny. Stary kod wczytuje `T11/T12` z `PARAMETERS.txt`, którego nie dostarczono. |
| Uśrednienia | 16 | Konfigurowalny wybór roboczy, nie odtworzona wartość historycznego `PRECISION`. |
| Czas ustalania SG386 | 20 ms | Konfigurowalna wartość robocza; wymaga sprawdzenia stabilizacji rzeczywistego toru. |
| Przebieg oscyloskopu | 20 µs, 1000 próbek | Wybór roboczy dla początkowej fluorescencji; nie zastępuje pełnego przebiegu 2 ms. |
| Tło | 0–200 ns od triggera | Nowe jawne okno, przed planowanym laser ON=500 ns od triggera. Sprawdź rzeczywiste opóźnienie toru. |
| Sygnał | 200–1200 ns od laser ON | Nowe jawne okno; trzeba dopasować je do reakcji detektora i dynamiki fluorescencji. |
| Referencja | 5–15 µs od laser ON | Nowe jawne okno. Stary kod brał końcowe 50 próbek rekordu; nie przepisano go bez znajomości podstawy czasu. |

Symulator używa **fikcyjnego** T1=350 µs i π=100 ns, zanikającego impulsu
fluorescencji oraz rezonansów 2,864 i 2,876 GHz. Te stałe służą sprawdzeniu
reakcji programu, nie opisują próbki ani wyników doktorskich.

## Definicja nowej sekwencji

`inicjalizacja → guard → slot π → τ → laser odczytu`.
W T1 **τ jest od końca slotu π do laser ON**. Referencja rezerwuje ten sam
slot, ale nie podaje π; laser i trigger mają identyczne czasy w obu fazach.
To jawna definicja nowej implementacji, nie identyczna oś dawnego programu:
tam `dark_time` obejmowało cały odcinek laser OFF i impuls MW.

Impulsowe ODMR zmienia częstotliwość przy stałym π i przerwie przed odczytem.
I/Q przygotowuje I=0,5 V przed bramką MW, Q=0 V; końcowe czasy analogowe
leżą na siatce 8 ns, cykl jest dopełniony stanem OFF do wielokrotności 8 ns.
Ograniczenia te sprawdzono w [API Pulse Streamera](https://www.swabianinstruments.com/static/documentation/PulseStreamer/sections/api-doc.html).

## Oscyloskop: co przejęto ze starego kodu

Zachowano model DSO-X 2014A, CH2 jako sygnał, CH1 jako trigger dodatni 0,25 V,
D0 jako źródło triggera, uśrednianie AVER, WORD i kolejność LSBF.
Mapowanie kanałów można zmienić w ustawieniach.

Nowy sterownik uzbraja oscyloskop przed uruchomieniem skończonej serii impulsów.
Sprawdza AER, świeży TER i `WAV:COUN?`; nie używa poprzedniego rekordu, jeśli
brakuje triggera lub liczby uśrednień. Dwie dodatkowe repetycje dają zapas,
ale oscyloskop może gubić triggery — wtedy program zgłasza błąd, a nie dobry wynik.
WORD jest bez znaku (`UNS 1`), a napięcie liczone z aktualnej preambuły:
`(kod − YReference) × YIncrement + YOrigin`.
Brakujące i obcięte próbki kończą pomiar błędem. Nie przeniesiono arbitralnego
offsetu 32767 ani skali `SIGNAL_SCALE/8192`.

Stare `ACQ:COMP NORM` pominięto: dokumentacja 2000 X-Series dla tej komendy
przewiduje COMPLETE=100. Źródło: [Keysight Programmer’s Guide](https://www.keysight.com/cd/en/assets/9018-06893/programming-guides/9018-06893.pdf),
s. 170, 200, 204–205, 736–745 i 755. Dla NORM transferu przewidziano do
1000 punktów; przy niewystarczającej rozdzielczości skróć zakres czasu.

Wskaźniki triggera i liczby uśrednień są kontrolą protokołu; ich zachowanie
na konkretnym firmware wymaga testu. Przełączenie NORM→AVER przed każdą fazą
ma usunąć poprzednie uśrednianie; niezależność faz trzeba potwierdzić doświadczalnie.

## Jak uzyskać wiarygodność na stanowisku

1. **Kod i GUI:** uruchom testy, pomiary na symulatorze, STOP i wstrzyknięcie awarii.
   To dowodzi działania sprawdzonych ścieżek programu, nie poprawności eksperymentu.
2. **Komunikacja:** porównaj IDN i adresy z fizycznymi urządzeniami. Sam `*IDN?`
   potwierdza wyłącznie łączność i identyfikację.
3. **Skala oscyloskopu:** przy widocznym stabilnym sygnale użyj w konsoli
   **Skala WORD/ASCII (STOP)**. Program porówna dwa kodowania tego samego
   zatrzymanego rekordu i pozostawi oscyloskop w STOP. Akceptacja: zgodność do
   dwóch kroków kwantyzacji oraz zgodność z napięciem odczytanym na panelu.
4. **Czasy:** obejrzyj D0, D1, D3 i detektor; zmierz polaryzację, szerokość π,
   wyprzedzenie triggera i rzeczywisty moment narastania światła. Wykres sekwencji
   pokazuje żądane poziomy, nie oscyloskopowy pomiar opóźnień.
5. **Kalibracja fizyczna:** znajdź rezonans CW; π wyznacz z pomiaru oscylacji Rabi
   przy tej samej mocy. Obecna aplikacja nie wykonuje pomiaru Rabi automatycznie.
   Zweryfikuj inicjalizację, tło i okna na rzeczywistym przebiegu. Dopiero po tym
   zaznacz potwierdzenie w **CZASY / OKNA**. Zmiana czasów usuwa potwierdzenie.
6. **Krótki T1 / Pulsed ODMR:** 3–5 punktów, sprawdź surowe pary i uśrednienia.
   Normalizacja: `r=(sygnał−tło)/(referencja−tło)`, wynik `r_bezπ−r_zπ`.
   Powtórz serię i porównaj ze sprawdzonym starym programem przy równoważnych
   definicjach czasu. Nie uruchamiaj obu aplikacji równocześnie na tych samych sesjach.
7. **Zatrzymanie:** potwierdź na urządzeniach RF OFF i laser OFF. Sam zapis
   „procedura OFF zakończona” nie mierzy fizycznego stanu wyjść.

T1 obecnie oznacza pomiar krzywej relaksacji — nie automatyczne dopasowanie
parametru T1 ani oszacowanie jego niepewności. Dane surowe i sekwencje są w JSON;
do pracy można wpisać wynik dopiero po walidacji i analizie własnych pomiarów.

## T2: oddzielny protokół echa Hahna

Sekwencja: `π/2 — τ — π — τ — ±π/2`, po inicjalizacji i przed odczytem optycznym.
Oś to **t=2τ**, suma obu swobodnych odcinków, bez szerokości impulsów. Każdy
odcinek ma całkowitą liczbę ns; oś jest jawnie zaokrąglana do parzystych ns.
Referencja ma te same cyfrowe impulsy i przeciwną fazę końcowego π/2:
I=−0,5 V zamiast +0,5 V, Q=0. Wynik jest różnicą znormalizowanych odczytów
180°−0°. Bezwzględny znak zależy od fizycznej konwencji faz toru; sprawdź go
przy kalibracji. T2 wymaga zewnętrznego I/Q. Parametry π/2 i π są niezależne.

Stary kod v6, linie 561–571, zawiera sekwencję ECHO i sterowanie fazą I/Q;
nowa wersja jawnie wybiera dwie fazy ostatniego impulsu. Przykład publikacyjny
takiego odczytu różnicowego: [Coherent quantum control of nitrogen vacancy spin
with nanoscale magnets, Nature Communications (2026)](https://www.nature.com/articles/s41467-026-73087-z).
Źródło wspiera metodę, nie wartości czasów dla tego stanowiska.

Roboczy zakres T2: 5–200 µs; fikcyjny model symulatora: T2=80 µs i wykładnik 1,4.
Nie modeluje modulacji ESEEM ani całego hamiltonianu NV. Nie jest to T2* (Ramsey).
Przed pomiarem wymagane są kalibracja obu obrotów, sprawdzenie przełączenia fazy
i porównanie przebiegów z urządzeń. Aplikacja nie wyznacza jeszcze dopasowanego T2.
