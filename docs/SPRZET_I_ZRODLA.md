# Przegląd aparatury i źródeł — 2026-11-16

Poniżej rozdzielono dane z dokumentacji producentów, historycznego kodu oraz
potwierdzenia użytkownika. Przegląd dokumentacji nie zastępuje testu aparatury.

## Materiały stanowiska

- `prace_mrozka/NV-Mariusz(1).py` oraz `NV-Mariusz_v6(1).py`: przejrzano kod
  połączeń, konfigurację SG386/oscyloskopu, mapowanie TTL/IQ, odbiór danych
  i zakończenie pomiaru. Plików nie uruchamiano ani nie modyfikowano.
- `prace_mrozka/DOKTORSKA_MM.pdf`: rozprawa Mariusza Mrózka z 2017 r., 83 strony;
  przejrzano przede wszystkim opis układu i CW ODMR w rozdziale 2. Publiczny
  [opis pracy UJ](https://zf.if.uj.edu.pl/pl/node/486).
- Potwierdzenie użytkownika 2026-11-16: laser ma odwróconą polaryzację bramkowania.
- W przekazanym katalogu nie znaleziono oddzielnej pracy licencjackiej.

Kod historyczny wskazuje D3 jako laser, D1 jako MW, A0/A1 jako I/Q, sygnał CH2
i trigger CH1. Jest rozbieżność między wizualizacją v6 (laser ON=1) i wykonaniem
(laser ON=0). Nowa implementacja używa jednej konfiguracji polaryzacji;
domyślnie laser ON=0 zgodnie z wykonaniem i potwierdzeniem użytkownika.

Doktorat opisuje m.in. laser Lighthouse Photonics Sprout H, modulator AOM,
detektor Thorlabs APD110A oraz Agilent DSO-X 3034A. Nie wynika z tego, że aktualne
stanowisko ma identyczny kontroler lasera. Thorlabs występuje tam również jako
producent elementów optycznych/detektora. Aktualny sterownik aplikacji celuje
w DSO-X 2014A wskazany w projekcie; inny model jest odrzucany przy identyfikacji.

## Dokumentacja producentów i decyzje implementacyjne

### SRS SG386

[SRS SG380 Series User Manual, rev. 2.07](https://www.thinksrs.com/downloads/pdfs/manuals/SG380m.pdf):
rozdział Remote Programming, komendy FREQ, AMPR, ENBR oraz MODL, TYPE i QFNC.
Sprawdzono sterowanie RF i wybór zewnętrznego I/Q. Nowy sterownik wykonuje
readback częstotliwości, mocy, modulacji oraz stanu RF; zakresy toru pozostają
2–3 GHz i -50…-10 dBm z dotychczasowego sterownika autora.

CW może korzystać z I/Q jak stary kod albo z wyłączonej modulacji dla bezpośredniego
toru RF. Wybór jest jawny w ustawieniach; nie wyprowadzamy go z samej nazwy modelu.

### Pulse Streamer 8/2

[Swabian Instruments — Programming interface 2.1](https://www.swabianinstruments.com/static/documentation/PulseStreamer/sections/api-doc.html):
sprawdzono `constant`, `OutputState`, identyfikację, wyłączenie persistent 125 MHz
i zasady zatrzymania. CW używa stanów stałych, bez streamowania impulsów.
Nieużywane cyfrowe wyjścia są LOW; laser OFF wymaga HIGH na jego kanale.
Przed pomiarem wyłączane są utrwalone wyjścia 125 MHz. A0=0,5 V przy MW ON
dotyczy wyłącznie wybranego zewnętrznego I/Q; A1 pozostaje 0 V.

Sprawdzono też lokalnie sygnaturę i kod klienta `pulsestreamer` 2.1.2:
konstruktor nie przyjmuje argumentu `timeout`; transport HTTP używa własnych
timeoutów 10 s. Nie podajemy nieistniejącego parametru API.

### DSO-X 2014A

[Keysight InfiniiVision 2000 X-Series Programmer's Guide, 2024](https://www.keysight.com/cd/en/assets/9018-06893/programming-guides/9018-06893.pdf):
przejrzano opis świeżej akwizycji (s. 56–57 i 177), danych (s. 737), preambuły
(s. 744–745), unsigned (s. 755) i skalowania (s. 757–762).

Używamy NORM, unsigned BYTE i `:DIGitize` + `*OPC?`; binarny blok IEEE 488.2
odbiera PyVISA. Skale napięcia/czasu pochodzą z preambuły. W odróżnieniu od
starego kodu nie zakładamy nagłówka stałej długości ani stałego offsetu ADC.
Wykrywamy kody brakujących/obciętych danych. Skale fizycznego oscyloskopu
ustawia operator; nie wykonujemy resetu ani autoskalowania podczas sweepu.

### R&S HMP4040

[R&S HMP Series User Manual, v05](https://scdn.rohde-schwarz.com/ur/pws/dl_downloads/pdm/cl_manuals/user_manual/1178_6833_01/HMPSeries_UserManual_en_05.pdf):
sprawdzono wybór kanału i odczyty MEAS:VOLT?/MEAS:CURR? w rozdziałach 8.2 i 8.9.
Monitor nie ustawia napięć/prądów ani nie załącza wyjść; po odczycie przywraca
poprzednio wybrany kanał. Symulator to prosty model obciążenia rezystancyjnego,
nie pełna symulacja elektryczna i zabezpieczeń zasilacza. HMP nie jest wymagany
do uruchomienia CW w tej wersji.

### Laser / elementy Thorlabs

Sprawdzono [stronę kontrolerów Thorlabs](https://www.thorlabs.com/high-power-laser-diode-controllers),
ale bez dokładnego modelu aktualnego urządzenia nie przypisujemy mu komend API
ani limitów prądu. W aplikacji istnieje wyłącznie konfigurowalna zewnętrzna
bramka laserowa, potwierdzona jako active-low. Dokumentacja starego stanowiska
nie jest podstawą do automatycznego programowania nieznanego kontrolera.

## Co zweryfikowano bez aparatury

Jednostki, normalizację OFF/ON, stany symulatorów, kodowanie danych BYTE,
readback rzeczywistego sterownika QCoDeS przez lokalne serwery TCP, nieprawidłowy
model oscyloskopu, STOP, błędy otwierania/akwizycji/cleanup, zapis częściowy,
metadane symulacji oraz działanie GUI i wątku pomiarowego.

Nadal konieczne są: potwierdzenie modeli/firmware, mapowania i polaryzacji,
kalibracja skali detektora, sensowny czas ustalania i powtarzalność widma
na rzeczywistym stanowisku. Nie wykonano pomiaru magnetycznego ani fizycznej
walidacji czasów/stanów wyjściowych.

## Uzupełnienie: impulsy, T1 i T2 echo

Przejrzano szczegółowo fragment wykonawczy starego v6: konfigurację oscyloskopu,
sekwencje ODMR/RABI/T1/ECHO, fazy analogowe oraz przetwarzanie przebiegów.
Nowy silnik impulsowy przejmuje profil trigger/AVER/WORD/LSBF; skalowanie i
kontrole świeżości pochodzą z instrukcji Keysight. Dodatkowo sprawdzono w niej
AER (s.170), TER (s.200), AVER/COMP (s.204–205), COUN (s.736) oraz WORD/UNS.
W API Swabian sprawdzono `createSequence`, `setDigital`, `setAnalog`,
`setTrigger`, skończone `stream` z `final` oraz `hasFinished` i dopełnienie 8 ns.

Źródłem układu trzech impulsów ECHO jest również stary kod v6, linie 561–571.
Odczyt z przeciwnymi fazami końcowego π/2 porównano z publikacją
[Coherent quantum control of nitrogen vacancy spin with nanoscale magnets](https://www.nature.com/articles/s41467-026-73087-z).
Artykuł wspiera wybór metody; wartości czasów i mocy nie zostały przeniesione
na aktualne stanowisko. W [CZASY_I_WALIDACJA.md](CZASY_I_WALIDACJA.md) zapisano
pochodzenie każdej wartości roboczej i różnicę definicji czasu względem starego kodu.
