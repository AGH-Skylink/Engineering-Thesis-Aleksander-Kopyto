# Test połączenia z SG386

Podłącz komputer i SG386 do tej samej sieci. Odczytaj aktualny adres IP
generatora w menu NET. Test używa gniazda TCP na porcie 5025.

Instalacja w PowerShell, w katalogu repozytorium:

```powershell
python -m venv --system-site-packages .venv
.\.venv\Scripts\python.exe -m pip install -e ".[hardware]"
```

Uruchom test, zastępując `ADRES_IP` adresem generatora:

```powershell
.\.venv\Scripts\python.exe -m nv_lab.hardware.check_sg386 ADRES_IP --visalib '@py'
```

Można również podać pełny adres VISA, np.
`TCPIP0::ADRES_IP::5025::SOCKET`. Opcja `--timeout 5` określa czas oczekiwania
w sekundach. Zainstalowany backend NI-VISA można wybrać, pomijając `--visalib`.

Test używa sterownika `SG386` i wysyła wyłącznie `*IDN?`, `FREQ?` oraz
`AMPR?`. Nie zmienia częstotliwości, mocy ani stanu wyjścia RF. Pomija
również czyszczenie urządzenia podczas inicjalizacji QCoDeS.
Sukces wymaga rozpoznania modelu SG386 i odczytania obu parametrów.

Przy błędzie połączenia sprawdź adres IP, połączenie sieciowe oraz włączenie
interfejsu raw socket w generatorze. Przy błędzie backendu sprawdź, czy test
uruchamiasz tym samym Pythonem, w którym zainstalowano zależności.

Źródło: [instrukcja SRS SG380](https://www.thinksrs.com/downloads/pdfs/manuals/SG380m.pdf),
sekcje TCP/IP Based Remote Interfaces i Detailed Command List.
