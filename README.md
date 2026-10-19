# Code Generator PRO

Streamlit aplikácia na tlač štítkov s QR, Aztec alebo Code 128 kódmi do PDF A4.

## Spustenie

```sh
python -m pip install -r requirements.txt
python -m streamlit run app.py
```

## Ručný zoznam

Predvolené poradie je **NÁZOV ; KÓD**:

```text
AB - HU - Miskolc A ; MOKR-Vykladka-01
AB - HU - Miskolc A;MOKR-Vykladka-01
```

Oba riadky vytvoria rovnaký štítok s obsahom kódu `MOKR-Vykladka-01`.
Medzery a tabulátory na okrajoch polí sa odstránia. Vnútorné medzery sa zachovajú,
pretože môžu byť súčasťou názvu alebo obsahu kódu. Prázdne riadky sa ignorujú.
Samostatný kód bez bodkočiarky sa použije aj ako názov. Názov je nepovinný,
kód musí byť vyplnený. Prvá bodkočiarka rozdeľuje polia.

Pri zoznamoch zo staršej verzie vyberte **KÓD ; NÁZOV**. Tabuľka pod vstupom
ukazuje, čo sa zakóduje a čo sa vytlačí ako názov. Výber poradia sa neodhaduje
automaticky, aby sa predišlo zámene názvu a kódu.

Po zmene vstupu alebo nastavení sa predchádzajúci náhľad a stiahnutie skryjú;
PDF treba znova vygenerovať. Chyby vstupu alebo nepodporované znaky zablokujú
vytvorenie neúplného PDF. Pre text s diakritikou v obsahu kódu použite QR alebo Aztec.
Písma pre tlač diakritiky sa načítavajú z adresára aplikácie.

## Testy

Python 3.12:

```sh
python -m pip install -r requirements-dev.txt
python -m unittest discover -s tests -v
```

Testy vykreslia skutočné PDF a dekódujú ich pomocou ZXing. Overujú všetky tri
formáty, otočenie, stránkovanie, obsah kódov, medzery, validáciu aj ovládanie
Streamlit rozhrania. Čitateľnosť vytlačených štítkov závisí aj od ich veľkosti,
rozlíšenia tlačiarne a použitej čítačky.
