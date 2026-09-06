import streamlit as st
import pandas as pd
import requests
import os
import re
from html.parser import HTMLParser
from io import BytesIO
import xml.etree.ElementTree as ET
from datetime import date


# =========================================================
# USTAWIENIA
# =========================================================

st.set_page_config(
    page_title="Sanctions Screening",
    page_icon="🔎",
    layout="wide"
)

st.title("🔎 Sanctions Screening — KRS / PL / EU / UK / USA")
st.write("Wgraj plik CSV z kontrahentami.")


# =========================================================
# EU FSF - TOKEN
# =========================================================

with st.sidebar:

    st.header("🇪🇺 EU FSF")

    eu_token_manual = st.text_input(
        "Token EU FSF (opcjonalnie)",
        type="password",
        help=(
            "Token pobierania EU Financial Sanctions File. "
            "Możesz też ustawić EU_FSF_TOKEN w Streamlit Secrets. "
            "Jeżeli oba są ustawione, użyty zostanie token wpisany tutaj."
        )
    ).strip()


    st.header("👤 Rejestr.io")

    # Klucz można podać przez Streamlit Secrets / zmienną środowiskową
    # albo jednorazowo w polu poniżej. Nie zapisujemy go w kodzie.
    try:
        rejestr_io_secret = str(
            st.secrets.get("REJESTR_IO_API_KEY", "")
        ).strip()
    except Exception:
        rejestr_io_secret = ""

    rejestr_io_env = os.getenv(
        "REJESTR_IO_API_KEY",
        ""
    ).strip()

    rejestr_io_key_manual = st.text_input(
        "Klucz API Rejestr.io",
        value="",
        type="password",
        help=(
            "Klucz API Rejestr.io. "
            "Najbezpieczniej przechowywać go w Streamlit Secrets "
            "jako REJESTR_IO_API_KEY. "
            "Pole ręczne nie jest zapisywane w repozytorium."
        )
    ).strip()

    rejestr_io_api_key = (
        rejestr_io_key_manual
        or rejestr_io_secret
        or rejestr_io_env
    )



# =========================================================
# FUNKCJA POMOCNICZA
# =========================================================

def first_value(*values):

    for value in values:

        if value is not None:

            value = str(value).strip()

            if value:
                return value

    return ""


# =========================================================
# MF API
# NIP -> KRS / NAZWA / REGON
# =========================================================

def get_company_from_mf(nip):

    today = date.today().isoformat()

    url = (
        f"https://wl-api.mf.gov.pl/api/search/nip/"
        f"{nip}?date={today}"
    )

    response = requests.get(
        url,
        timeout=20
    )

    if response.status_code != 200:

        return None, f"MF HTTP {response.status_code}"

    try:

        data = response.json()

        subject = data["result"]["subject"]

        result = {

            "krs": first_value(
                subject.get("krs")
            ),

            "name": first_value(
                subject.get("name")
            ),

            "regon": first_value(
                subject.get("regon")
            )
        }

        return result, "OK"

    except Exception as e:

        return None, f"Błąd MF: {e}"


# =========================================================
# KRS API
# KRS -> DANE PODMIOTU
# =========================================================

def get_krs_data(krs):

    url = (
        f"https://api-krs.ms.gov.pl/api/krs/"
        f"OdpisAktualny/{krs}?rejestr=P&format=json"
    )

    response = requests.get(
        url,
        timeout=20
    )

    if response.status_code == 204:

        return None, None, "KRS 204 — brak danych"

    if response.status_code == 404:

        return None, None, "KRS 404 — nie znaleziono"

    if response.status_code != 200:

        return None, None, f"KRS HTTP {response.status_code}"

    try:

        data = response.json()

        # =================================================
        # GŁÓWNA STRUKTURA KRS
        # =================================================

        odpis = data.get(
            "odpis",
            {}
        )

        dane = odpis.get(
            "dane",
            {}
        )

        dzial1 = dane.get(
            "dzial1",
            {}
        )

        # =================================================
        # NAGŁÓWEK ODPISU
        # =================================================

        # UWAGA:
        # naglowekA znajduje się wewnątrz "odpis"

        naglowek = odpis.get(
            "naglowekA",
            {}
        )

        # =================================================
        # DANE PODMIOTU
        # =================================================

        dane_podmiotu = dzial1.get(
            "danePodmiotu",
            {}
        )

        # =================================================
        # IDENTYFIKATORY
        # =================================================

        identyfikatory = dane_podmiotu.get(
            "identyfikatory",
            {}
        )

        # =================================================
        # SIEDZIBA I ADRES
        # =================================================

        siedziba_adres = dzial1.get(
            "siedzibaIAdres",
            {}
        )

        adres = siedziba_adres.get(
            "adres",
            {}
        )

        siedziba = siedziba_adres.get(
            "siedziba",
            {}
        )

        # =================================================
        # PODSTAWOWE DANE
        # =================================================

        nazwa = first_value(
            dane_podmiotu.get(
                "nazwa"
            ),

            dane_podmiotu.get(
                "nazwaSkrocona"
            )
        )

        nip = first_value(
            identyfikatory.get(
                "nip"
            )
        )

        regon = first_value(
            identyfikatory.get(
                "regon"
            )
        )

        forma_prawna = first_value(
            dane_podmiotu.get(
                "formaPrawna"
            )
        )

        # =================================================
        # DATA REJESTRACJI
        # =================================================

        data_rejestracji = first_value(
            naglowek.get(
                "dataRejestracjiWKRS"
            )
        )

        # =================================================
        # DATA OSTATNIEGO WPISU
        # =================================================

        data_ostatniego_wpisu = first_value(
            naglowek.get(
                "dataOstatniegoWpisu"
            ),

            dzial1.get(
                "dataOstatniegoWpisu"
            ),

            dzial1.get(
                "dataWpisu"
            )
        )

        # =================================================
        # STAN NA DZIEŃ
        # =================================================

        stan_na_dzien = first_value(
            naglowek.get(
                "stanZDnia"
            ),

            dzial1.get(
                "stanZDnia"
            ),

            dzial1.get(
                "stanNaDzien"
            )
        )

        # =================================================
        # ADRES
        # =================================================

        wojewodztwo = first_value(
            adres.get(
                "wojewodztwo"
            ),

            siedziba.get(
                "wojewodztwo"
            )
        )

        powiat = first_value(
            adres.get(
                "powiat"
            ),

            siedziba.get(
                "powiat"
            )
        )

        gmina = first_value(
            adres.get(
                "gmina"
            ),

            siedziba.get(
                "gmina"
            )
        )

        miejscowosc = first_value(
            adres.get(
                "miejscowosc"
            ),

            siedziba.get(
                "miejscowosc"
            )
        )

        ulica = first_value(
            adres.get(
                "ulica"
            )
        )

        nr_domu = first_value(
            adres.get(
                "nrDomu"
            )
        )

        nr_lokalu = first_value(
            adres.get(
                "nrLokalu"
            )
        )

        kod_pocztowy = first_value(
            adres.get(
                "kodPocztowy"
            )
        )

        # =================================================
        # WYNIK
        # =================================================

        result = {

            "KRS": krs,

            "Nazwa KRS": nazwa,

            "Forma prawna": forma_prawna,

            "NIP KRS": nip,

            "REGON KRS": regon,

            "Data rejestracji": data_rejestracji,

            "Data ostatniego wpisu": data_ostatniego_wpisu,

            "Stan na dzień": stan_na_dzien,

            "Województwo": wojewodztwo,

            "Powiat": powiat,

            "Gmina": gmina,

            "Miejscowość": miejscowosc,

            "Ulica": ulica,

            "Nr domu": nr_domu,

            "Nr lokalu": nr_lokalu,

            "Kod pocztowy": kod_pocztowy
        }

        return result, data, "OK"

    except Exception as e:

        return None, None, f"Błąd parsowania KRS: {e}"

# =========================================================
# KRS - REPREZENTACJA / DZIAŁ 2
# =========================================================

def get_krs_representation(krs):

    url = (
        f"https://api-krs.ms.gov.pl/api/krs/"
        f"OdpisAktualny/{krs}?rejestr=P&format=json"
    )

    response = requests.get(
        url,
        timeout=20
    )

    if response.status_code != 200:
        return None, f"KRS HTTP {response.status_code}"

    try:

        data = response.json()

        # -------------------------------------------------
        # GŁÓWNA STRUKTURA
        # -------------------------------------------------

        odpis = data.get(
            "odpis",
            {}
        )

        dane = odpis.get(
            "dane",
            {}
        )

        # -------------------------------------------------
        # DZIAŁ 2
        # -------------------------------------------------

        dzial2 = dane.get(
            "dzial2",
            {}
        )

        reprezentacja = dzial2.get(
            "reprezentacja",
            {}
        )

        # -------------------------------------------------
        # SPOSÓB REPREZENTACJI
        # -------------------------------------------------

        sposob = first_value(
            reprezentacja.get(
                "sposobReprezentacji"
            )
        )

        # -------------------------------------------------
        # SKŁAD ORGANU
        # -------------------------------------------------

        sklad = reprezentacja.get(
            "sklad",
            []
        )

        osoby = []

        if isinstance(sklad, dict):
            sklad = [sklad]

        for osoba in sklad:

            # KRS może zwracać pola osoby jako zagnieżdżone słowniki.
            # Sprowadzamy je zawsze do zwykłego tekstu.

            def text_from_value(value):

                if value is None:
                    return ""

                if isinstance(value, dict):

                    # Najpierw próbujemy typowych pól osobowych.
                    preferred_keys = [
                        "imie",
                        "imiePierwsze",
                        "imieDrugie",
                        "nazwisko",
                        "nazwiskoCzlon",
                        "nazwaLubFirma"
                    ]

                    values = []

                    for key in preferred_keys:

                        if key in value:

                            extracted = text_from_value(
                                value.get(key)
                            )

                            if extracted:
                                values.append(extracted)

                    if values:
                        return " ".join(dict.fromkeys(values))

                    # Fallback dla innych struktur.
                    values = []

                    for value_item in value.values():

                        extracted = text_from_value(
                            value_item
                        )

                        if extracted:
                            values.append(extracted)

                    return " ".join(dict.fromkeys(values))

                if isinstance(value, list):

                    values = []

                    for item in value:

                        extracted = text_from_value(item)

                        if extracted:
                            values.append(extracted)

                    return " ".join(values)

                return str(value).strip()

            # Jeżeli dane osoby są dodatkowo zagnieżdżone,
            # spróbujmy najpierw znaleźć właściwy obiekt.
            osoba_data = osoba

            if isinstance(osoba_data.get("osoba"), dict):

                osoba_data = osoba_data.get("osoba")

            imiona = text_from_value(
                osoba_data.get("imie")
            )

            if not imiona:
                imiona = text_from_value(
                    osoba_data.get("imiona")
                )

            nazwisko = text_from_value(
                osoba_data.get("nazwiskoCzlon")
            )

            if not nazwisko:
                nazwisko = text_from_value(
                    osoba_data.get("nazwisko")
                )

            if not nazwisko:
                nazwisko = text_from_value(
                    osoba_data.get("nazwaLubFirma")
                )

            funkcja = text_from_value(
                osoba.get("funkcjaWOrganie")
            )

            if not funkcja:
                funkcja = text_from_value(
                    osoba.get("funkcja")
                )

            osoby.append({
                "Nazwisko": nazwisko,
                "Imiona": imiona,
                "Funkcja": funkcja
            })

        # -------------------------------------------------
        # WYNIK
        # -------------------------------------------------

        result = {

            "Sposób reprezentacji": sposob,

            "Osoby reprezentujące": osoby
        }

        return result, "OK"

    except Exception as e:

        return None, f"Błąd parsowania reprezentacji: {e}"
# =========================================================
# MSWiA - LISTA SANKCYJNA
# =========================================================

def normalize_text(value):

    if value is None:
        return ""

    import unicodedata
    import re

    value = str(value).upper().strip()

    value = unicodedata.normalize(
        "NFKD",
        value
    )

    value = "".join(
        char
        for char in value
        if not unicodedata.combining(char)
    )

    value = re.sub(
        r"[^A-Z0-9]+",
        " ",
        value
    )

    return " ".join(
        value.split()
    )


@st.cache_data(ttl=3600)
def get_mswiA_sanctions():

    url = (
        "https://www.gov.pl/web/mswia/"
        "lista-osob-i-podmiotow-objetych-sankcjami"
    )

    try:

        response = requests.get(
            url,
            timeout=30,
            headers={
                "User-Agent": "Mozilla/5.0"
            }
        )

        if response.status_code != 200:

            return None, (
                f"MSWiA HTTP {response.status_code}"
            )

        # Nie używamy pd.read_html(), ponieważ wymaga zewnętrznego
        # parsera HTML (np. lxml), którego Streamlit może nie mieć.
        # Używamy standardowej biblioteki Pythona.

        from html.parser import HTMLParser

        class TableParser(HTMLParser):

            def __init__(self):

                super().__init__()

                self.tables = []
                self.current_table = None
                self.current_row = None
                self.current_cell = None
                self.cell_text = ""

            def handle_starttag(self, tag, attrs):

                if tag == "table":

                    self.current_table = []

                elif (
                    self.current_table is not None
                    and tag == "tr"
                ):

                    self.current_row = []

                elif (
                    self.current_row is not None
                    and tag in ("td", "th")
                ):

                    self.current_cell = tag
                    self.cell_text = ""

            def handle_data(self, data):

                if self.current_cell is not None:

                    self.cell_text += data

            def handle_endtag(self, tag):

                if (
                    self.current_cell is not None
                    and tag in ("td", "th")
                ):

                    self.current_row.append(
                        " ".join(
                            self.cell_text.split()
                        )
                    )

                    self.current_cell = None
                    self.cell_text = ""

                elif (
                    tag == "tr"
                    and self.current_row is not None
                ):

                    if self.current_row:

                        self.current_table.append(
                            self.current_row
                        )

                    self.current_row = None

                elif (
                    tag == "table"
                    and self.current_table is not None
                ):

                    if self.current_table:

                        self.tables.append(
                            self.current_table
                        )

                    self.current_table = None

        parser = TableParser()

        parser.feed(
            response.text
        )

        if not parser.tables:

            return None, (
                "MSWiA — nie znaleziono tabel"
            )

        frames = []

        for rows in parser.tables:

            if len(rows) < 2:
                continue

            headers = rows[0]

            # Uzupełniamy brakujące nagłówki.
            headers = [
                header
                if header
                else f"Kolumna_{i + 1}"
                for i, header in enumerate(headers)
            ]

            data_rows = []

            for row in rows[1:]:

                # Wyrównanie liczby kolumn.
                row = list(row)

                if len(row) < len(headers):

                    row.extend(
                        [""] * (
                            len(headers) - len(row)
                        )
                    )

                elif len(row) > len(headers):

                    row = row[:len(headers)]

                data_rows.append(
                    row
                )

            if data_rows:

                frames.append(
                    pd.DataFrame(
                        data_rows,
                        columns=headers
                    )
                )

        if not frames:

            return None, (
                "MSWiA — nie udało się odczytać danych"
            )

        sanctions = pd.concat(
            frames,
            ignore_index=True
        )

        return sanctions, "OK"

    except Exception as e:

        return None, (
            f"Błąd pobierania listy MSWiA: {e}"
        )


def check_mswiA_sanctions(
    name,
    nip,
    krs
):

    sanctions, status = (
        get_mswiA_sanctions()
    )

    if sanctions is None:

        return None, status

    name_norm = normalize_text(
        name
    )

    nip_norm = normalize_text(
        nip
    )

    krs_norm = normalize_text(
        krs
    )

    for _, row in sanctions.iterrows():

        row_values = [
            str(value)
            for value in row.tolist()
            if pd.notna(value)
        ]

        row_text = " ".join(
            row_values
        )

        row_norm = normalize_text(
            row_text
        )

        # Pomijamy wpisy wykreślone z listy,
        # jeżeli tabela zawiera datę wykreślenia.
        deleted = False

        for column in sanctions.columns:

            column_norm = normalize_text(
                column
            )

            if "DATA WYKRESLENIA" in column_norm:

                value = row.get(
                    column,
                    ""
                )

                if pd.notna(value) and str(
                    value
                ).strip():

                    deleted = True

                    break

        if deleted:
            continue

        # Najpierw najmocniejsze identyfikatory:
        # NIP lub KRS.
        if nip_norm and nip_norm in row_norm:

            return {
                "status": "ZNALEZIONO",
                "powod": "NIP",
                "wpis": row.to_dict()
            }, "OK"

        if krs_norm and krs_norm in row_norm:

            return {
                "status": "ZNALEZIONO",
                "powod": "KRS",
                "wpis": row.to_dict()
            }, "OK"

        # Nazwę traktujemy jako słabsze dopasowanie.
        if (
            name_norm
            and len(name_norm) >= 5
            and name_norm in row_norm
        ):

            return {
                "status": "ZNALEZIONO",
                "powod": "NAZWA",
                "wpis": row.to_dict()
            }, "OK"

    return {
        "status": "NIE ZNALEZIONO",
        "powod": "",
        "wpis": {}
    }, "OK"


# =========================================================
# GIIF - KRAJOWA LISTA SANKCYJNA
# =========================================================

@st.cache_data(ttl=3600)
def get_giif_sanctions():

    # Oficjalna strona MF z aktualną krajową listą sankcyjną GIIF.
    page_url = (
        "https://www.gov.pl/web/finanse/"
        "lista-osob-i-podmiotow-wobec-ktorych-stosuje-sie-"
        "szczegolne-srodki-ograniczajace-na-podstawie-art-118-"
        "ustawy-z-dnia-1-marca-2018-r-o-przeciwdzialaniu-"
        "praniu-pieniedzy-i-finansowaniu-terroryzmu"
    )

    try:

        page_response = requests.get(
            page_url,
            timeout=30,
            headers={
                "User-Agent": "Mozilla/5.0"
            }
        )

        if page_response.status_code != 200:

            return None, (
                f"GIIF strona HTTP "
                f"{page_response.status_code}"
            )

        # Szukamy linków do XLS/XLSX na aktualnej stronie MF.
        from html.parser import HTMLParser
        from urllib.parse import urljoin

        class LinkParser(HTMLParser):

            def __init__(self):

                super().__init__()

                self.links = []

            def handle_starttag(
                self,
                tag,
                attrs
            ):

                if tag.lower() != "a":
                    return

                attributes = dict(
                    attrs
                )

                href = attributes.get(
                    "href",
                    ""
                )

                text_parts = []

                self.current_text = text_parts

                self.links.append(
                    {
                        "href": href,
                        "text": ""
                    }
                )

                self.current_link = (
                    self.links[-1]
                )

            def handle_data(self, data):

                if hasattr(
                    self,
                    "current_link"
                ):

                    self.current_link["text"] += (
                        " "
                        + data.strip()
                    )

            def handle_endtag(self, tag):

                if tag.lower() == "a" and hasattr(
                    self,
                    "current_link"
                ):

                    self.current_link["text"] = (
                        self.current_link["text"].strip()
                    )

                    del self.current_link

        parser = LinkParser()

        parser.feed(
            page_response.text
        )

        candidates = []

        for link in parser.links:

            href = link.get(
                "href",
                ""
            )

            label = link.get(
                "text",
                ""
            )

            combined = (
                href + " " + label
            ).lower()

            if (
                ".xlsx" in combined
                or ".xls" in combined
            ):

                candidates.append(
                    href
                )

        # Usuwamy duplikaty i budujemy pełne adresy.
        candidates = list(
            dict.fromkeys(
                urljoin(
                    page_url,
                    href
                )
                for href in candidates
                if href
            )
        )

        if not candidates:

            return None, (
                "GIIF — na stronie MF nie znaleziono "
                "aktualnego pliku XLS/XLSX"
            )

        # Próbujemy kandydatów po kolei, zaczynając od XLSX.
        candidates = sorted(
            candidates,
            key=lambda url: (
                0 if ".xlsx" in url.lower()
                else 1
            )
        )

        file_response = None

        for file_url in candidates:

            try:

                response = requests.get(
                    file_url,
                    timeout=30,
                    headers={
                        "User-Agent": "Mozilla/5.0"
                    }
                )

                if response.status_code == 200:

                    file_response = response

                    break

            except Exception:
                continue

        if file_response is None:

            return None, (
                "GIIF — nie udało się pobrać "
                "aktualnego pliku XLS/XLSX"
            )

        from io import BytesIO

        try:

            giif = pd.read_excel(
                BytesIO(
                    file_response.content
                )
            )

        except ImportError:

            return None, (
                "GIIF: brak biblioteki openpyxl. "
                "Dodaj openpyxl do requirements.txt."
            )

        except Exception as e:

            return None, (
                f"GIIF — błąd odczytu XLSX: {e}"
            )

        if giif.empty:

            return None, (
                "GIIF — pobrany plik jest pusty"
            )

        giif.columns = [
            str(column).strip()
            for column in giif.columns
        ]

        return giif, "OK"

    except Exception as e:

        return None, (
            f"Błąd pobierania listy GIIF: {e}"
        )


def check_giif_sanctions(
    name,
    nip,
    krs
):

    sanctions, status = (
        get_giif_sanctions()
    )

    if sanctions is None:

        return None, status

    name_norm = normalize_text(
        name
    )

    nip_norm = normalize_text(
        nip
    )

    krs_norm = normalize_text(
        krs
    )

    for _, row in sanctions.iterrows():

        row_values = [
            str(value)
            for value in row.tolist()
            if pd.notna(value)
        ]

        row_text = " ".join(
            row_values
        )

        row_norm = normalize_text(
            row_text
        )

        if nip_norm and nip_norm in row_norm:

            return {
                "status": "ZNALEZIONO",
                "powod": "NIP",
                "wpis": row.to_dict()
            }, "OK"

        if krs_norm and krs_norm in row_norm:

            return {
                "status": "ZNALEZIONO",
                "powod": "KRS",
                "wpis": row.to_dict()
            }, "OK"

        if (
            name_norm
            and len(name_norm) >= 5
            and name_norm in row_norm
        ):

            return {
                "status": "ZNALEZIONO",
                "powod": "NAZWA",
                "wpis": row.to_dict()
            }, "OK"

    return {
        "status": "NIE ZNALEZIONO",
        "powod": "",
        "wpis": {}
    }, "OK"


# =========================================================
# UE - SKONSOLIDOWANA LISTA SANKCJI FINANSOWYCH
# =========================================================

EU_FSF_CSV_URL = (
    "https://webgate.ec.europa.eu/fsd/fsf/public/files/"
    "csvFullSanctionsList_1_1/content"
)

EU_FSF_XML_URL = (
    "https://webgate.ec.europa.eu/fsd/fsf/public/files/"
    "xmlFullSanctionsList_1_1/content"
)


def get_eu_fsf_token():

    """
    Pobiera token EU FSF z:
    1. Streamlit Secrets: EU_FSF_TOKEN
    2. zmiennej środowiskowej: EU_FSF_TOKEN

    Token można też wkleić ręcznie w sidebarze.
    """

    token = ""

    try:

        token = st.secrets.get(
            "EU_FSF_TOKEN",
            ""
        )

    except Exception:

        token = ""

    if not token:

        token = os.getenv(
            "EU_FSF_TOKEN",
            ""
        )

    token = str(token).strip()

    # Użytkownik może wkleić sam token albo cały parametr URL.
    if "token=" in token:

        token = token.split(
            "token=",
            1
        )[1]

        token = token.split(
            "&",
            1
        )[0]

    return token.strip()


def parse_eu_csv(content):

    from io import BytesIO

    try:

        eu = pd.read_csv(
            BytesIO(content),
            sep=";",
            dtype=str,
            keep_default_na=False
        )

    except UnicodeDecodeError:

        eu = pd.read_csv(
            BytesIO(content),
            sep=";",
            dtype=str,
            encoding="latin-1",
            keep_default_na=False
        )

    if eu.empty:

        raise ValueError(
            "plik CSV jest pusty"
        )

    eu.columns = [
        str(column).strip()
        for column in eu.columns
    ]

    return eu


def parse_eu_xml(content):

    """
    Awaryjny parser XML 1.1.

    Nie zakładamy sztywnego namespace ani konkretnej kolejności pól.
    Dla każdego elementu Entity zbieramy wszystkie wartości tekstowe
    znajdujące się w jego poddrzewie. Dzięki temu screening może działać
    również wtedy, gdy Komisja zmieni kolejność lub namespace XML.
    """

    root = ET.fromstring(content)

    rows = []

    for entity in root.iter():

        local_name = entity.tag.split(
            "}",
            1
        )[-1]

        if local_name.lower() != "entity":
            continue

        values = []

        for element in entity.iter():

            text = (element.text or "").strip()

            if text:

                values.append(text)

            for attr_value in element.attrib.values():

                attr_value = str(attr_value).strip()

                if attr_value:

                    values.append(attr_value)

        # Usuwamy duplikaty przy zachowaniu kolejności.
        values = list(
            dict.fromkeys(values)
        )

        if not values:
            continue

        row = {
            "EU Entity": entity.attrib.get(
                "euReferenceNumber",
                entity.attrib.get(
                    "ID",
                    ""
                )
            ),
            "_EU row text": " ".join(values)
        }

        rows.append(row)

    if not rows:

        raise ValueError(
            "w XML nie znaleziono elementów Entity"
        )

    return pd.DataFrame(rows)


@st.cache_data(ttl=3600)
def get_eu_sanctions(token):

    """
    Oficjalna EU Financial Sanctions File (FSF).

    Aktualny endpoint FSF wymaga tokenu pobierania. Token jest bezpłatny
    i można go uzyskać przez EU Login / konto FSF. Aplikacja nie używa
    agregatora typu OpenSanctions jako zastępczego źródła.

    Próby pobrania:
    1. CSV 1.1 z tokenem
    2. XML 1.1 z tokenem
    """

    token = str(token or "").strip()

    if not token:

        return None, (
            "UE FSF — wymagany token pobierania. "
            "Ustaw EU_FSF_TOKEN w Streamlit Secrets / zmiennej środowiskowej "
            "albo wklej token w panelu bocznym."
        )

    urls = [

        (
            EU_FSF_CSV_URL
            + "?token="
            + token,
            "CSV"
        ),

        (
            EU_FSF_XML_URL
            + "?token="
            + token,
            "XML"
        )
    ]

    headers = {

        "User-Agent": (
            "Mozilla/5.0 "
            "(Windows NT 10.0; Win64; x64) "
            "AppleWebKit/537.36 "
            "Chrome/140.0 Safari/537.36"
        ),

        "Accept": (
            "text/csv,application/csv,"
            "application/xml,text/xml,"
            "application/octet-stream,*/*"
        ),

        "Referer": (
            "https://webgate.ec.europa.eu/fsd/fsf/"
        )
    }

    last_error = ""

    for url, file_type in urls:

        try:

            response = requests.get(
                url,
                timeout=90,
                headers=headers
            )

        except requests.RequestException as e:

            last_error = (
                f"{file_type}: {e}"
            )

            continue

        if response.status_code != 200:

            last_error = (
                f"{file_type}: HTTP "
                f"{response.status_code}"
            )

            continue

        try:

            if file_type == "CSV":

                eu = parse_eu_csv(
                    response.content
                )

            else:

                eu = parse_eu_xml(
                    response.content
                )

            return eu, (
                f"OK — EU FSF {file_type}"
            )

        except Exception as e:

            last_error = (
                f"{file_type}: błąd parsowania — {e}"
            )

    return None, (
        "UE FSF — nie udało się pobrać listy. "
        + last_error
        + ". Sprawdź, czy token jest aktualny."
    )


def check_eu_sanctions(
    name,
    nip,
    krs,
    token
):

    sanctions, status = (
        get_eu_sanctions(
            token
        )
    )

    if sanctions is None:

        return None, status

    name_norm = normalize_text(
        name
    )

    nip_norm = normalize_text(
        nip
    )

    krs_norm = normalize_text(
        krs
    )

    # Dla XML 1.1 mamy przygotowaną jedną kolumnę z pełną treścią
    # danego Entity. Dla CSV budujemy tekst z całego rekordu.
    for _, row in sanctions.iterrows():

        if "_EU row text" in sanctions.columns:

            row_text = str(
                row.get(
                    "_EU row text",
                    ""
                )
            )

        else:

            row_values = [
                str(value)
                for value in row.tolist()
                if pd.notna(value)
            ]

            row_text = " ".join(
                row_values
            )

        row_norm = normalize_text(
            row_text
        )

        if nip_norm and nip_norm in row_norm:

            return {
                "status": "ZNALEZIONO",
                "powod": "NIP",
                "wpis": row.to_dict()
            }, status

        if krs_norm and krs_norm in row_norm:

            return {
                "status": "ZNALEZIONO",
                "powod": "KRS",
                "wpis": row.to_dict()
            }, status

        if (
            name_norm
            and len(name_norm) >= 5
            and name_norm in row_norm
        ):

            return {
                "status": "ZNALEZIONO",
                "powod": "NAZWA",
                "wpis": row.to_dict()
            }, status

    return {
        "status": "NIE ZNALEZIONO",
        "powod": "",
        "wpis": {}
    }, status


# =========================================================
# USA / OFAC - SDN + CONSOLIDATED NON-SDN
# =========================================================

# OFAC's Sanctions List Service (SLS) is the official source.
# The stable /api/download/ endpoints redirect to the current
# publication file. OFAC requires a User-Agent on automated requests.
OFAC_SDN_URL = (
    "https://sanctionslistservice.ofac.treas.gov/"
    "api/download/sdn.xml"
)

OFAC_CONSOLIDATED_URL = (
    "https://sanctionslistservice.ofac.treas.gov/"
    "api/download/consolidated.xml"
)

OFAC_HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/140.0 Safari/537.36"
    ),
    "Accept": "application/xml,text/xml,application/octet-stream,*/*"
}


def parse_ofac_xml(content, list_name):

    """
    Parsuje klasyczny OFAC XML (SDN.XML / CONSOLIDATED.XML).

    Dla każdego wpisu budujemy jeden rekord tekstowy zawierający
    nazwę, aliasy, adresy, programy i pozostałe informacje opublikowane
    przez OFAC. Dzięki temu screening może szukać nie tylko nazwy
    głównej, ale również aliasów i identyfikatorów zapisanych w rekordzie.
    """

    root = ET.fromstring(content)

    rows = []

    for entry in root.iter():

        local_name = entry.tag.split(
            "}",
            1
        )[-1]

        if local_name.lower() not in (
            "sdnentry",
            "entry"
        ):
            continue

        values = []

        for element in entry.iter():

            text = (element.text or "").strip()

            if text:
                values.append(text)

            for attr_value in element.attrib.values():

                attr_value = str(attr_value).strip()

                if attr_value:
                    values.append(attr_value)

        values = list(
            dict.fromkeys(values)
        )

        if not values:
            continue

        # Szukamy podstawowego numeru wpisu, jeżeli występuje.
        entry_id = ""

        for element in entry.iter():

            local = element.tag.split(
                "}",
                1
            )[-1].lower()

            if local in (
                "uid",
                "ent_num",
                "entnum"
            ):

                text = (element.text or "").strip()

                if text:
                    entry_id = text
                    break

        rows.append({
            "OFAC lista": list_name,
            "OFAC ID": entry_id,
            "_OFAC row text": " ".join(values)
        })

    if not rows:

        raise ValueError(
            f"{list_name}: XML nie zawiera wpisów"
        )

    return pd.DataFrame(rows)


@st.cache_data(ttl=3600)
def get_ofac_sanctions():

    """
    Pobiera oficjalne listy OFAC:

    1. SDN - Specially Designated Nationals and Blocked Persons
    2. Consolidated - Non-SDN sanctions lists

    OFAC publikuje oba pliki przez Sanctions List Service (SLS).
    """

    datasets = [

        (
            OFAC_SDN_URL,
            "SDN"
        ),

        (
            OFAC_CONSOLIDATED_URL,
            "CONSOLIDATED"
        )
    ]

    all_rows = []

    for url, list_name in datasets:

        try:

            response = requests.get(
                url,
                timeout=120,
                headers=OFAC_HEADERS
            )

        except requests.RequestException as e:

            return None, (
                f"OFAC {list_name}: błąd połączenia — {e}"
            )

        if response.status_code != 200:

            return None, (
                f"OFAC {list_name}: HTTP "
                f"{response.status_code}"
            )

        try:

            parsed = parse_ofac_xml(
                response.content,
                list_name
            )

            all_rows.append(
                parsed
            )

        except Exception as e:

            return None, (
                f"OFAC {list_name}: błąd parsowania — {e}"
            )

    result = pd.concat(
        all_rows,
        ignore_index=True
    )

    return result, "OK"


def check_ofac_sanctions(
    name,
    nip,
    krs
):

    sanctions, status = (
        get_ofac_sanctions()
    )

    if sanctions is None:

        return None, status

    name_norm = normalize_text(
        name
    )

    nip_norm = normalize_text(
        nip
    )

    krs_norm = normalize_text(
        krs
    )

    for _, row in sanctions.iterrows():

        row_text = str(
            row.get(
                "_OFAC row text",
                ""
            )
        )

        row_norm = normalize_text(
            row_text
        )

        list_name = first_value(
            row.get(
                "OFAC lista"
            )
        )

        if nip_norm and nip_norm in row_norm:

            return {
                "status": "ZNALEZIONO",
                "powod": f"NIP ({list_name})",
                "wpis": row.to_dict()
            }, status

        if krs_norm and krs_norm in row_norm:

            return {
                "status": "ZNALEZIONO",
                "powod": f"KRS ({list_name})",
                "wpis": row.to_dict()
            }, status

        if (
            name_norm
            and len(name_norm) >= 5
            and name_norm in row_norm
        ):

            return {
                "status": "ZNALEZIONO",
                "powod": f"NAZWA ({list_name})",
                "wpis": row.to_dict()
            }, status

    return {
        "status": "NIE ZNALEZIONO",
        "powod": "",
        "wpis": {}
    }, status


# =========================================================
# UK SANCTIONS LIST
# =========================================================

# Oficjalna lista UK Sanctions List (UKSL), publikowana przez FCDO.
# Od 28 stycznia 2026 r. jest to jedyne aktualne źródło brytyjskich
# designations; stara OFSI Consolidated List nie jest już aktualizowana.
UK_SANCTIONS_CSV_URL = (
    "https://sanctionslist.fcdo.gov.uk/docs/UK-Sanctions-List.csv"
)

UK_SANCTIONS_HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/140.0 Safari/537.36"
    ),
    "Accept": "text/csv,text/plain,application/octet-stream,*/*"
}


def parse_uk_csv(content):

    """
    Parsuje oficjalny UK Sanctions List CSV.

    Nie zakładamy konkretnego układu kolumn do matchingu. Budujemy
    dodatkowe pole tekstowe z całego rekordu, dzięki czemu możemy
    sprawdzać nazwę, aliasy, adresy, numery rejestracyjne i pozostałe
    identyfikatory publikowane przez UK.
    """

    df = pd.read_csv(
        BytesIO(content),
        dtype=str,
        keep_default_na=False
    )

    if df.empty:

        raise ValueError(
            "UK Sanctions List CSV jest pusty"
        )

    df.columns = [
        str(column).strip()
        for column in df.columns
    ]

    df["_UK row text"] = df.apply(
        lambda row: " ".join(
            str(value).strip()
            for value in row.tolist()
            if str(value).strip()
        ),
        axis=1
    )

    return df


@st.cache_data(ttl=3600)
def get_uk_sanctions():

    """
    Pobiera aktualną UK Sanctions List z oficjalnego źródła FCDO.
    """

    try:

        response = requests.get(
            UK_SANCTIONS_CSV_URL,
            timeout=120,
            headers=UK_SANCTIONS_HEADERS
        )

    except requests.RequestException as e:

        return None, (
            f"UK Sanctions List: błąd połączenia — {e}"
        )

    if response.status_code != 200:

        return None, (
            "UK Sanctions List: HTTP "
            f"{response.status_code}"
        )

    try:

        sanctions = parse_uk_csv(
            response.content
        )

        return sanctions, "OK"

    except Exception as e:

        return None, (
            "UK Sanctions List: błąd parsowania — "
            f"{e}"
        )


def check_uk_sanctions(
    name,
    nip,
    krs
):

    sanctions, status = (
        get_uk_sanctions()
    )

    if sanctions is None:

        return None, status

    name_norm = normalize_text(
        name
    )

    nip_norm = normalize_text(
        nip
    )

    krs_norm = normalize_text(
        krs
    )

    for _, row in sanctions.iterrows():

        row_text = str(
            row.get(
                "_UK row text",
                ""
            )
        )

        row_norm = normalize_text(
            row_text
        )

        if nip_norm and nip_norm in row_norm:

            return {
                "status": "ZNALEZIONO",
                "powod": "NIP",
                "wpis": row.to_dict()
            }, status

        if krs_norm and krs_norm in row_norm:

            return {
                "status": "ZNALEZIONO",
                "powod": "KRS",
                "wpis": row.to_dict()
            }, status

        if (
            name_norm
            and len(name_norm) >= 5
            and name_norm in row_norm
        ):

            return {
                "status": "ZNALEZIONO",
                "powod": "NAZWA",
                "wpis": row.to_dict()
            }, status

    return {
        "status": "NIE ZNALEZIONO",
        "powod": "",
        "wpis": {}
    }, status


# =========================================================
# STATUS KOŃCOWY SCREENINGU
# =========================================================


# =========================================================
# SEARCH RESOLVER - ODANONIMIZOWANIE OSÓB KRS
# =========================================================

class SearchResultParser(HTMLParser):
    """Wyciąga widoczny tekst z HTML wyników wyszukiwarki."""

    def __init__(self):
        super().__init__()
        self.parts = []

    def handle_data(self, data):
        text = re.sub(r"\s+", " ", data).strip()
        if text:
            self.parts.append(text)


def split_person_mask(person):
    """
    Rozbija zanonimizowaną osobę z KRS na tokeny imienia/nazwiska.

    Przykłady akceptowane:
      J**** K******
      J***N K*****I
      Jan**** Kowals****

    Zwraca listę tokenów zawierających pierwszą/ostatnią literę
    oraz długość tokenu.
    """

    text = str(person or "").strip()
    text = re.sub(r"\s+", " ", text)

    # Bierzemy tylko tokeny zawierające litery; usuwamy typowe dodatki.
    tokens = re.findall(
        r"[A-Za-zĄĆĘŁŃÓŚŹŻąćęłńóśźż*-]+",
        text
    )

    tokens = [
        token.strip("-")
        for token in tokens
        if token.strip("-")
    ]

    if len(tokens) < 2:
        return []

    result = []

    for token in tokens[:2]:
        letters = [c for c in token if c.isalpha()]
        if not letters:
            continue

        result.append({
            "mask": token,
            "length": len(letters),
            "first": letters[0],
            "last": letters[-1] if not set(letters) <= {"*"} else ""
        })

    return result if len(result) >= 2 else []


def person_mask_matches(masked_person, candidate_name):
    """Sprawdza, czy pełne nazwisko pasuje do maski KRS."""

    masks = split_person_mask(masked_person)

    if len(masks) < 2:
        return False, 0

    # Kandydat może zawierać drugie imię / nazwisko dwuczłonowe.
    candidate_tokens = re.findall(
        r"[A-Za-zĄĆĘŁŃÓŚŹŻąćęłńóśźż-]+",
        str(candidate_name or "")
    )

    candidate_tokens = [
        x for x in candidate_tokens
        if x and x.lower() not in {
            "prezes", "zarządu", "zarzad", "członek", "czlonek",
            "wiceprezes", "wice", "członk", "czlonk"
        }
    ]

    if len(candidate_tokens) < 2:
        return False, 0

    # Sprawdzamy wszystkie sensowne pary imię/nazwisko.
    best_score = 0
    best_match = False

    for i in range(len(candidate_tokens) - 1):
        pair = [candidate_tokens[i], candidate_tokens[i + 1]]
        score = 0
        ok = True

        for mask, cand in zip(masks[:2], pair):
            cand_letters = [c for c in cand if c.isalpha()]
            if len(cand_letters) != mask["length"]:
                ok = False
                break

            if cand_letters[0].casefold() != mask["first"].casefold():
                ok = False
                break

            # KRS nie zawsze pokazuje ostatnią literę. Jeżeli ją mamy,
            # musi się zgadzać.
            if mask["last"] and (
                cand_letters[-1].casefold() != mask["last"].casefold()
            ):
                ok = False
                break

            score += 25

        if ok:
            best_match = True
            best_score = max(best_score, score + 50)

    return best_match, best_score


def extract_name_candidates(text):
    """Wyciąga potencjalne pary imię+nazwisko z tekstu wyników."""

    # Typowe polskie imię/nazwisko zaczynające się wielką literą.
    pattern = re.compile(
        r"\b([A-ZĄĆĘŁŃÓŚŹŻ][A-Za-zĄĆĘŁŃÓŚŹŻąćęłńóśźż-]{2,})"
        r"\s+"
        r"([A-ZĄĆĘŁŃÓŚŹŻ][A-Za-zĄĆĘŁŃÓŚŹŻąćęłńóśźż-]{2,})\b"
    )

    candidates = []
    seen = set()

    for match in pattern.finditer(text):
        candidate = f"{match.group(1)} {match.group(2)}"
        key = normalize_text(candidate)

        if key in seen:
            continue

        seen.add(key)
        candidates.append(candidate)

    return candidates


def google_search_people(krs, company_name, role, masked_person):
    """
    Resolver osoby zanonimizowanej przez KRS.

    Google bardzo często blokuje automatyczne zapytania HTTP kodem 403.
    Dlatego używamy dwóch zwykłych, publicznych interfejsów wyszukiwarek:
      1) DuckDuckGo HTML
      2) Google jako fallback

    Nie próbujemy obchodzić CAPTCHA ani innych zabezpieczeń.
    Jeżeli wyszukiwarki nie zwrócą wyników, osoba nie jest automatycznie
    odanonimizowywana.
    """

    krs_clean = re.sub(r"\D", "", str(krs or ""))
    company = str(company_name or "").strip()
    role_text = str(role or "").strip()

    masks = split_person_mask(masked_person)

    if not krs_clean or len(masks) < 2:
        return [], "Nie udało się odczytać maski osoby z KRS"

    query = (
        f'"{krs_clean}" "{role_text}" '
        f'"{company}" site:rejestr.io'
    )

    headers = {
        "User-Agent": (
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
            "AppleWebKit/537.36 (KHTML, like Gecko) "
            "Chrome/140.0 Safari/537.36"
        ),
        "Accept-Language": "pl-PL,pl;q=0.9,en;q=0.8",
        "Accept": (
            "text/html,application/xhtml+xml,application/xml;"
            "q=0.9,*/*;q=0.8"
        )
    }

    search_engines = [
        (
            "DuckDuckGo",
            "https://html.duckduckgo.com/html/",
            {"q": query}
        ),
        (
            "Google",
            "https://www.google.com/search",
            {"q": query, "hl": "pl", "num": "10"}
        )
    ]

    errors = []

    for engine_name, url, params in search_engines:

        try:
            response = requests.get(
                url,
                params=params,
                headers=headers,
                timeout=20
            )
        except requests.RequestException as e:
            errors.append(
                f"{engine_name} — błąd połączenia: {e}"
            )
            continue

        if response.status_code != 200:
            errors.append(
                f"{engine_name} HTTP {response.status_code}"
            )
            continue

        lower_html = response.text.lower()

        if (
            "captcha" in lower_html
            or "unusual traffic" in lower_html
            or "detected unusual traffic" in lower_html
            or "automated queries" in lower_html
        ):
            errors.append(
                f"{engine_name} — automatyczne wyszukiwanie zablokowane/CAPTCHA"
            )
            continue

        parser = SearchResultParser()

        try:
            parser.feed(response.text)
        except Exception as e:
            errors.append(
                f"{engine_name} — błąd parsowania: {e}"
            )
            continue

        visible_text = " ".join(parser.parts)
        candidates = extract_name_candidates(visible_text)
        normalized_text = normalize_text(visible_text)

        scored = []

        for candidate in candidates:

            matched, score = person_mask_matches(
                masked_person,
                candidate
            )

            if not matched:
                continue

            context_score = 0

            if (
                krs_clean
                and krs_clean in normalized_text
            ):
                context_score += 20

            if (
                company
                and normalize_text(company) in normalized_text
            ):
                context_score += 15

            if (
                role_text
                and normalize_text(role_text) in normalized_text
            ):
                context_score += 15

            total_score = min(
                100,
                score + context_score
            )

            scored.append({
                "Osoba": candidate,
                "Confidence": total_score,
                "Źródło": f"{engine_name} → Rejestr.io",
                "Zapytanie": query
            })

        unique = {}

        for item in scored:
            key = normalize_text(item["Osoba"])

            if (
                key not in unique
                or item["Confidence"]
                > unique[key]["Confidence"]
            ):
                unique[key] = item

        results = sorted(
            unique.values(),
            key=lambda x: x["Confidence"],
            reverse=True
        )

        if results:
            return results[:5], "OK"

        errors.append(
            f"{engine_name} — brak kandydata pasującego do maski"
        )

    return [], " | ".join(errors)

def get_rejestr_io_people(krs, api_key):
    """
    Pobiera aktualne osoby powiązane z organizacją z Rejestr.io.

    Korzystamy z:
      GET /api/v2/org/{krs}/krs-powiazania?aktualnosc=aktualne

    API zwraca aktualne powiązania z KRS oraz dane osoby.
    Do screeningu osób reprezentujących wybieramy powiązania typu
    KRS_BOARD. Rejestr.io dokumentuje, że domyślne/aktualne powiązania
    odpowiadają najnowszemu wpisowi do KRS.
    """

    if not api_key:
        return [], "Brak klucza API Rejestr.io"

    krs_clean = re.sub(
        r"\D",
        "",
        str(krs or "")
    )

    if not krs_clean:
        return [], "Brak numeru KRS"

    url = (
        f"https://rejestr.io/api/v2/org/"
        f"{krs_clean}/krs-powiazania"
    )

    headers = {
        "Authorization": f"Bearer {api_key}",
        "Accept": "application/json",
        "User-Agent": "Compliance Screening App"
    }

    try:
        response = requests.get(
            url,
            headers=headers,
            params={"aktualnosc": "aktualne"},
            timeout=20
        )
    except requests.RequestException as e:
        return [], f"Rejestr.io — błąd połączenia: {e}"

    if response.status_code in (401, 403):
        return [], (
            f"Rejestr.io HTTP {response.status_code} — "
            "sprawdź klucz API i aktywację API"
        )

    if response.status_code == 402:
        return [], (
            "Rejestr.io HTTP 402 — brak środków / wymagany plan"
        )

    if response.status_code == 429:
        return [], (
            "Rejestr.io HTTP 429 — przekroczony limit zapytań"
        )

    if response.status_code != 200:
        return [], (
            f"Rejestr.io HTTP {response.status_code}"
        )

    try:
        data = response.json()
    except Exception as e:
        return [], f"Rejestr.io — nieprawidłowy JSON: {e}"

    if not isinstance(data, list):
        return [], "Rejestr.io — nieoczekiwany format odpowiedzi"

    people = []

    for item in data:

        if not isinstance(item, dict):
            continue

        if item.get("typ") != "osoba":
            continue

        identity = item.get("tozsamosc") or {}

        if not isinstance(identity, dict):
            continue

        full_name = first_value(
            identity.get("imiona_i_nazwisko"),
            (
                f"{first_value(identity.get('imie'))} "
                f"{first_value(identity.get('nazwisko'))}"
            ).strip()
        )

        if not full_name:
            continue

        # Powiązanie z konkretną odpytaną organizacją.
        relations = item.get(
            "krs_powiazania_kwerendowane",
            []
        )

        if not isinstance(relations, list):
            relations = []

        board_relations = []

        for relation in relations:

            if not isinstance(relation, dict):
                continue

            relation_type = str(
                relation.get("typ", "")
            ).strip().upper()

            description = first_value(
                relation.get("opis"),
                relation.get("nazwa"),
                "CZŁONEK ORGANU"
            )

            # KRS_BOARD = członek organu reprezentacji.
            if relation_type == "KRS_BOARD":
                board_relations.append({
                    "Funkcja": description,
                    "Od": first_value(
                        relation.get("data_start")
                    ),
                    "Do": first_value(
                        relation.get("data_koniec")
                    )
                })

        for relation in board_relations:

            # aktualne powiązanie powinno mieć brak daty końcowej.
            # Jeśli API mimo wszystko zwróci datę końca, pomijamy je.
            if relation["Do"]:
                continue

            people.append({
                "Osoba": full_name,
                "Funkcja": relation["Funkcja"],
                "Od": relation["Od"],
                "Confidence": 100,
                "Źródło": "Rejestr.io API"
            })

    # Usuwamy duplikaty osoby + funkcji.
    unique = {}

    for person in people:

        key = (
            normalize_text(person["Osoba"]),
            normalize_text(person["Funkcja"])
        )

        if key not in unique:
            unique[key] = person

    return list(unique.values()), "OK"


def resolve_people_from_rejestr_io(krs, api_key):
    """
    Zwraca aktualne osoby z organu reprezentacji.

    Nie korzystamy już z Google, DuckDuckGo ani z anonimizowanej maski KRS.
    Rejestr.io dostarcza jawne imię/nazwisko oraz funkcję.
    """

    people, status = get_rejestr_io_people(
        krs,
        api_key
    )

    if not people:
        return [], status

    return people, "OK — Rejestr.io API"



def screen_person_on_sanctions(person_name):
    """
    Screening jednej osoby po pełnym imieniu i nazwisku.

    Używamy tych samych oficjalnych list, które są już załadowane
    dla kontrahenta. Nie próbujemy dopasowywać osoby po NIP/KRS.
    """

    result = {
        "Osoba": person_name,
        "MSWiA": "",
        "MSWiA dopasowanie": "",
        "GIIF": "",
        "GIIF dopasowanie": "",
        "UE": "",
        "UE dopasowanie": "",
        "UK": "",
        "UK dopasowanie": "",
        "USA": "",
        "USA dopasowanie": ""
    }

    # MSWiA — nazwa osoby, brak NIP/KRS.
    try:
        mswia_result, mswia_status = check_mswiA_sanctions(
            person_name, "", ""
        )
        if mswia_result is None:
            result["MSWiA"] = "BŁĄD"
            result["MSWiA dopasowanie"] = mswia_status
        else:
            result["MSWiA"] = mswia_result.get("status", "")
            result["MSWiA dopasowanie"] = mswia_result.get("powod", "")
    except Exception as e:
        result["MSWiA"] = "BŁĄD"
        result["MSWiA dopasowanie"] = str(e)

    # GIIF
    try:
        giif_result, giif_status = check_giif_sanctions(
            person_name, "", ""
        )
        if giif_result is None:
            result["GIIF"] = "BŁĄD"
            result["GIIF dopasowanie"] = giif_status
        else:
            result["GIIF"] = giif_result.get("status", "")
            result["GIIF dopasowanie"] = giif_result.get("powod", "")
    except Exception as e:
        result["GIIF"] = "BŁĄD"
        result["GIIF dopasowanie"] = str(e)

    # EU
    try:
        eu_result, eu_status = check_eu_sanctions(
            person_name, "", "", eu_fsf_token
        )
        if eu_result is None:
            result["EU"] = "BŁĄD"
            result["EU dopasowanie"] = eu_status
        else:
            result["EU"] = eu_result.get("status", "")
            result["EU dopasowanie"] = eu_result.get("powod", "")
    except Exception as e:
        result["EU"] = "BŁĄD"
        result["EU dopasowanie"] = str(e)

    # UK
    try:
        uk_result, uk_status = check_uk_sanctions(
            person_name, "", ""
        )
        if uk_result is None:
            result["UK"] = "BŁĄD"
            result["UK dopasowanie"] = uk_status
        else:
            result["UK"] = uk_result.get("status", "")
            result["UK dopasowanie"] = uk_result.get("powod", "")
    except Exception as e:
        result["UK"] = "BŁĄD"
        result["UK dopasowanie"] = str(e)

    # OFAC
    try:
        ofac_result, ofac_status = check_ofac_sanctions(
            person_name, "", ""
        )
        if ofac_result is None:
            result["USA"] = "BŁĄD"
            result["USA dopasowanie"] = ofac_status
        else:
            result["USA"] = ofac_result.get("status", "")
            result["USA dopasowanie"] = ofac_result.get("powod", "")
    except Exception as e:
        result["USA"] = "BŁĄD"
        result["USA dopasowanie"] = str(e)

    return result


def get_people_screening_status(people_results):
    """Agreguje wynik screeningu osób reprezentujących."""

    if not people_results:
        return "", "", ""

    hits = []
    errors = []

    source_map = [
        ("MSWiA", "MSWiA"),
        ("GIIF", "GIIF"),
        ("EU", "EU"),
        ("UK", "UK"),
        ("USA", "USA")
    ]

    for person in people_results:
        person_name = person.get("Osoba", "")

        for field, label in source_map:
            value = str(person.get(field, "")).strip().upper()

            if value == "ZNALEZIONO":
                hits.append(f"{person_name} — {label}")
            elif value == "BŁĄD":
                errors.append(f"{person_name} — {label}")

    if hits:
        return "🔴 SANCTIONS HIT", "; ".join(hits), "; ".join(errors)

    if errors:
        return "⚠️ DATA ERROR", "", "; ".join(errors)

    return "🟢 CLEAR", "", ""


def get_final_screening_status(row):

    sources = [
        "MSWiA sankcje",
        "GIIF sankcje",
        "UE sankcje",
        "UK sankcje",
        "USA sankcje"
    ]

    hits = []
    errors = []

    for source in sources:

        value = str(
            row.get(source, "")
        ).strip().upper()

        if value == "ZNALEZIONO":
            hits.append(source.replace(" sankcje", ""))

        elif value == "BŁĄD":
            errors.append(source.replace(" sankcje", ""))

    # Screening osób reprezentujących ma taki sam priorytet jak screening spółki.
    person_status = str(row.get("Screening osób", "")).strip()

    if person_status == "🔴 SANCTIONS HIT":
        person_hits = str(row.get("Osoby trafienia", "")).strip()
        if person_hits:
            hits.append("OSOBY: " + person_hits)

    elif person_status == "⚠️ DATA ERROR":
        person_errors = str(row.get("Osoby błędy", "")).strip()
        if person_errors:
            errors.append("OSOBY: " + person_errors)

    # Trafienie ma najwyższy priorytet.
    if hits:
        return "🔴 SANCTIONS HIT", "; ".join(hits), "; ".join(errors)

    # Jeżeli którekolwiek źródło było niedostępne, nie oznaczamy
    # kontrahenta jako CLEAR.
    if errors:
        return "⚠️ DATA ERROR", "", "; ".join(errors)

    return "🟢 CLEAR", "", ""


# Token ręczny ma pierwszeństwo przed Secrets / ENV.
eu_fsf_token = eu_token_manual or get_eu_fsf_token()


# =========================================================
# UPLOAD CSV
# =========================================================

uploaded_file = st.file_uploader(
    "Wybierz plik CSV",
    type=["csv"]
)


if uploaded_file is not None:

    try:

        # =================================================
        # WCZYTANIE CSV
        # =================================================

        df = pd.read_csv(
            uploaded_file,
            dtype=str
        )

        df.columns = (
            df.columns
            .str.strip()
        )

        st.success(
            f"Plik wczytany poprawnie — "
            f"{len(df)} rekordów."
        )

        # =================================================
        # PODGLĄD CSV
        # =================================================

        st.subheader(
            "Kontrahenci"
        )

        st.dataframe(
            df,
            use_container_width=True
        )

        # =================================================
        # WALIDACJA NIP
        # =================================================

        if "NIP" not in df.columns:

            st.error(
                "CSV musi zawierać kolumnę 'NIP'."
            )

            st.stop()

        # =================================================
        # PRZYCISK SCREENINGU
        # =================================================

        if st.button(
            "🔎 Sprawdź KRS",
            type="primary"
        ):

            results = []

            debug_data = {}

            progress = st.progress(0)

            status_text = st.empty()

            total = len(df)

            # =================================================
            # PĘTLA PO KONTRAHENTACH
            # =================================================

            for i, row in df.iterrows():

                # ---------------------------------------------
                # NIP
                # ---------------------------------------------

                nip = str(
                    row["NIP"]
                ).strip()

                nip = (
                    nip
                    .replace(" ", "")
                    .replace("-", "")
                )

                # ---------------------------------------------
                # NAZWA Z CSV
                # ---------------------------------------------

                nazwa_csv = str(
                    row.get(
                        "Nazwa",
                        ""
                    )
                ).strip()

                status_text.write(
                    f"Sprawdzanie "
                    f"{i + 1} / {total} "
                    f"— NIP: {nip}"
                )

                # ---------------------------------------------
                # PUSTY REKORD
                # ---------------------------------------------

                result = {

                    "NIP": nip,

                    "Nazwa z CSV": nazwa_csv,

                    "KRS": "",

                    "Nazwa KRS": "",

                    "Forma prawna": "",

                    "NIP KRS": "",

                    "REGON": "",

                    "REGON KRS": "",

                    "Data rejestracji": "",

                    "Data ostatniego wpisu": "",

                    "Stan na dzień": "",

                    "Województwo": "",

                    "Powiat": "",

                    "Gmina": "",

                    "Miejscowość": "",

                    "Ulica": "",

                    "Nr domu": "",

                    "Nr lokalu": "",

                    "Kod pocztowy": "",

                    "Status MF": "",

                    "Status KRS": "",

                    "Sposób reprezentacji": "",

                    "Osoby reprezentujące": "",
                    "Screening osób": "",
                    "Osoby trafienia": "",
                    "Osoby błędy": "",
                    "MSWiA sankcje": "",

                    "MSWiA dopasowanie": "",

                    "GIIF sankcje": "",

                    "GIIF dopasowanie": "",

                    "UE sankcje": "",

                    "UE dopasowanie": "",

                    "USA sankcje": "",

                    "USA dopasowanie": "",

                    "Status końcowy": "",

                    "Źródła z trafieniem": "",

                    "Źródła z błędem": ""
                }

                # =================================================
                # MF
                # =================================================

                try:

                    mf_data, mf_status = (
                        get_company_from_mf(
                            nip
                        )
                    )

                    result["Status MF"] = (
                        mf_status
                    )

                    if mf_data is None:

                        result["Status KRS"] = (
                            "Nie znaleziono KRS"
                        )

                    else:

                        # -----------------------------------------
                        # REGON Z MF
                        # -----------------------------------------

                        result["REGON"] = (
                            mf_data.get(
                                "regon",
                                ""
                            )
                        )

                        # -----------------------------------------
                        # KRS
                        # -----------------------------------------

                        krs = mf_data.get(
                            "krs",
                            ""
                        )

                        result["KRS"] = krs

                        # =========================================
                        # KRS
                        # =========================================

                        if krs:

                            krs_data, raw_json, krs_status = (
                                get_krs_data(
                                    krs
                                )
                            )

                            representation_result, representation_status = (
                                get_krs_representation(
                                    krs
                                )
                            )

                            result["Status KRS"] = (
                                krs_status
                            )

                            if representation_result is not None:

                                result["Sposób reprezentacji"] = (
                                    representation_result.get(
                                        "Sposób reprezentacji",
                                        ""
                                    )
                                )

                                osoby = representation_result.get(
                                    "Osoby reprezentujące",
                                    []
                                )

                                result["Osoby reprezentujące"] = (
                                    "; ".join(
                                        first_value(
                                            osoba.get("Imiona"),
                                            ""
                                        )
                                        + " "
                                        + first_value(
                                            osoba.get("Nazwisko"),
                                            ""
                                        )
                                        + " — "
                                        + first_value(
                                            osoba.get("Funkcja"),
                                            ""
                                        )
                                        for osoba in osoby
                                    )
                                )

                            # -------------------------------------
                            # OSOBY — REJESTR.IO API
                            # -------------------------------------

                            resolved_people = []
                            resolver_details = []
                            resolver_errors = []

                            if rejestr_io_api_key:

                                rejestr_people, rejestr_status = (
                                    resolve_people_from_rejestr_io(
                                        krs,
                                        rejestr_io_api_key
                                    )
                                )

                                if rejestr_people:

                                    for person in rejestr_people:

                                        resolved_people.append(
                                            person
                                        )

                                        resolver_details.append({
                                            "KRS maska": "",
                                            "Funkcja": person.get(
                                                "Funkcja",
                                                ""
                                            ),
                                            "Resolver": (
                                                "OK — Rejestr.io API"
                                            ),
                                            "Kandydaci": (
                                                f"{person.get('Osoba', '')} "
                                                f"(100%)"
                                            )
                                        })

                                else:

                                    resolver_errors.append(
                                        f"Rejestr.io — {rejestr_status}"
                                    )

                            else:

                                resolver_errors.append(
                                    "Brak klucza API Rejestr.io"
                                )

                            # -------------------------------------
                            # SCREENING OSÓB
                            # -------------------------------------
                            # Rejestr.io zwrócił jawne osoby. Teraz każdą z nich
                            # przepuszczamy przez te same listy sankcyjne co spółkę.
                            if resolved_people:
                                people_screening = []

                                for person in resolved_people:
                                    person_result = screen_person_on_sanctions(
                                        person.get("Osoba", "")
                                    )

                                    person_result["Funkcja"] = person.get(
                                        "Funkcja", ""
                                    )
                                    person_result["Od"] = person.get(
                                        "Od", ""
                                    )
                                    person_result["Źródło"] = person.get(
                                        "Źródło", ""
                                    )

                                    people_screening.append(
                                        person_result
                                    )

                                (
                                    person_status,
                                    person_hits,
                                    person_errors
                                ) = get_people_screening_status(
                                    people_screening
                                )

                                result["Screening osób"] = person_status
                                result["Osoby trafienia"] = person_hits

                                combined_errors = []

                                if person_errors:
                                    combined_errors.append(
                                        person_errors
                                    )

                                if resolver_errors:
                                    combined_errors.extend(
                                        resolver_errors
                                    )

                                result["Osoby błędy"] = "; ".join(
                                    x for x in combined_errors if x
                                )

                                result["_people_details"] = people_screening
                                result["_resolver_details"] = resolver_details

                                # Jeżeli część osób nie została pobrana,
                                # nie możemy uznać screeningu osób za CLEAR.
                                if (
                                    resolver_errors
                                    and result["Screening osób"]
                                    != "🔴 SANCTIONS HIT"
                                ):
                                    result["Screening osób"] = (
                                        "⚠️ DATA ERROR"
                                    )

                            else:
                                result["Screening osób"] = (
                                    "⚠️ DATA ERROR"
                                )
                                result["Osoby błędy"] = "; ".join(
                                    resolver_errors
                                    or [
                                        "Nie znaleziono osób reprezentujących w Rejestr.io"
                                    ]
                                )
                                result["_resolver_details"] = resolver_details


                            # -------------------------------------
                            # SCREENING MSWiA
                            # -------------------------------------

                            mswia_result, mswia_status = (
                                check_mswiA_sanctions(
                                    result.get(
                                        "Nazwa KRS",
                                        ""
                                    ),
                                    result.get(
                                        "NIP KRS",
                                        ""
                                    ),
                                    krs
                                )
                            )

                            if mswia_result is None:

                                result["MSWiA sankcje"] = (
                                    "BŁĄD"
                                )

                                result["MSWiA dopasowanie"] = (
                                    mswia_status
                                )

                            else:

                                result["MSWiA sankcje"] = (
                                    mswia_result.get(
                                        "status",
                                        ""
                                    )
                                )

                                result["MSWiA dopasowanie"] = (
                                    mswia_result.get(
                                        "powod",
                                        ""
                                    )
                                )

                            # -------------------------------------
                            # SCREENING GIIF
                            # -------------------------------------

                            giif_result, giif_status = (
                                check_giif_sanctions(
                                    result.get(
                                        "Nazwa KRS",
                                        ""
                                    ),
                                    result.get(
                                        "NIP KRS",
                                        ""
                                    ),
                                    krs
                                )
                            )

                            if giif_result is None:

                                result["GIIF sankcje"] = (
                                    "BŁĄD"
                                )

                                result["GIIF dopasowanie"] = (
                                    giif_status
                                )

                            else:

                                result["GIIF sankcje"] = (
                                    giif_result.get(
                                        "status",
                                        ""
                                    )
                                )

                                result["GIIF dopasowanie"] = (
                                    giif_result.get(
                                        "powod",
                                        ""
                                    )
                                )

                            # -------------------------------------
                            # SCREENING UE
                            # -------------------------------------

                            eu_result, eu_status = (
                                check_eu_sanctions(
                                    result.get(
                                        "Nazwa KRS",
                                        ""
                                    ),
                                    result.get(
                                        "NIP KRS",
                                        ""
                                    ),
                                    krs,
                                    eu_fsf_token
                                )
                            )

                            if eu_result is None:

                                result["UE sankcje"] = (
                                    "BŁĄD"
                                )

                                result["UE dopasowanie"] = (
                                    eu_status
                                )

                            else:

                                result["UE sankcje"] = (
                                    eu_result.get(
                                        "status",
                                        ""
                                    )
                                )

                                result["UE dopasowanie"] = (
                                    eu_result.get(
                                        "powod",
                                        ""
                                    )
                                )


                            # -------------------------------------
                            # SCREENING UK
                            # -------------------------------------

                            uk_result, uk_status = (
                                check_uk_sanctions(
                                    result.get(
                                        "Nazwa KRS",
                                        ""
                                    ),
                                    result.get(
                                        "NIP KRS",
                                        ""
                                    ),
                                    krs
                                )
                            )

                            if uk_result is None:

                                result["UK sankcje"] = (
                                    "BŁĄD"
                                )

                                result["UK dopasowanie"] = (
                                    uk_status
                                )

                            else:

                                result["UK sankcje"] = (
                                    uk_result.get(
                                        "status",
                                        ""
                                    )
                                )

                                result["UK dopasowanie"] = (
                                    uk_result.get(
                                        "powod",
                                        ""
                                    )
                                )


                            # -------------------------------------
                            # SCREENING USA / OFAC
                            # -------------------------------------

                            ofac_result, ofac_status = (
                                check_ofac_sanctions(
                                    result.get(
                                        "Nazwa KRS",
                                        ""
                                    ),
                                    result.get(
                                        "NIP KRS",
                                        ""
                                    ),
                                    krs
                                )
                            )

                            if ofac_result is None:

                                result["USA sankcje"] = (
                                    "BŁĄD"
                                )

                                result["USA dopasowanie"] = (
                                    ofac_status
                                )

                            else:

                                result["USA sankcje"] = (
                                    ofac_result.get(
                                        "status",
                                        ""
                                    )
                                )

                                result["USA dopasowanie"] = (
                                    ofac_result.get(
                                        "powod",
                                        ""
                                    )
                                )


                            # -------------------------------------
                            # DEBUG JSON
                            # -------------------------------------

                            if raw_json is not None:

                                debug_data[nip] = raw_json

                            # -------------------------------------
                            # DANE KRS
                            # -------------------------------------

                            if krs_data is not None:

                                for key, value in (
                                    krs_data.items()
                                ):

                                    if key in result:

                                        result[key] = value

                        else:

                            result["Status KRS"] = (
                                "Brak numeru KRS"
                            )

                except Exception as e:

                    result["Status MF"] = (
                        f"BŁĄD: {e}"
                    )

                # -----------------------------------------
                # STATUS KOŃCOWY
                # -----------------------------------------

                final_status, hit_sources, error_sources = (
                    get_final_screening_status(
                        result
                    )
                )

                result["Status końcowy"] = final_status

                result["Źródła z trafieniem"] = hit_sources

                result["Źródła z błędem"] = error_sources

                # -----------------------------------------
                # ZAPIS WYNIKU
                # -----------------------------------------

                results.append(
                    result
                )

                # -----------------------------------------
                # PROGRESS
                # -----------------------------------------

                progress.progress(
                    (i + 1) / total
                )

            # =================================================
            # KONIEC
            # =================================================

            progress.empty()

            status_text.empty()

            # Szczegóły screeningu osób trzymamy poza główną tabelą.
            people_debug = {}
            resolver_debug = {}
            for item in results:
                if item.get("_people_details"):
                    people_debug[item.get("NIP", "")] = item["_people_details"]
                if item.get("_resolver_details"):
                    resolver_debug[item.get("NIP", "")] = item["_resolver_details"]
                item.pop("_people_details", None)
                item.pop("_resolver_details", None)

            results_df = pd.DataFrame(
                results
            )

            # =================================================
            # WYNIKI
            # =================================================

            st.subheader(
                "Wyniki screeningu"
            )

            st.dataframe(
                results_df,
                use_container_width=True,
                height=600
            )

            # =================================================
            # STATYSTYKI
            # =================================================

            total_companies = len(
                results_df
            )

            found_krs = (
                results_df["KRS"]
                .astype(str)
                .str.strip()
                .ne("")
                .sum()
            )

            mf_errors = (
                ~results_df[
                    "Status MF"
                ].eq("OK")
            ).sum()

            krs_errors = (
                ~results_df[
                    "Status KRS"
                ].eq("OK")
            ).sum()

            sanctions_hits = (
                results_df[
                    "Status końcowy"
                ].eq("🔴 SANCTIONS HIT")
            ).sum()

            data_errors = (
                results_df[
                    "Status końcowy"
                ].eq("⚠️ DATA ERROR")
            ).sum()

            clear_companies = (
                results_df[
                    "Status końcowy"
                ].eq("🟢 CLEAR")
            ).sum()

            # =================================================
            # METRYKI
            # =================================================

            col1, col2, col3, col4 = (
                st.columns(4)
            )

            with col1:

                st.metric(
                    "Kontrahenci",
                    total_companies
                )

            with col2:

                st.metric(
                    "🟢 CLEAR",
                    clear_companies
                )

            with col3:

                st.metric(
                    "🔴 SANCTIONS HIT",
                    sanctions_hits
                )

            with col4:

                st.metric(
                    "⚠️ DATA ERROR",
                    data_errors
                )

            st.caption(
                f"KRS znaleziono: {found_krs} | "
                f"Błędy MF: {mf_errors} | "
                f"Błędy KRS: {krs_errors}"
            )

            # =================================================
            # SCREENING OSÓB — SZCZEGÓŁY
            # =================================================

            st.divider()

            with st.expander(
                "👤 Screening osób reprezentujących"
            ):

                if people_debug:

                    selected_people_nip = st.selectbox(
                        "Wybierz NIP:",
                        list(people_debug.keys()),
                        key="people_debug_nip"
                    )

                    st.dataframe(
                        pd.DataFrame(
                            people_debug[selected_people_nip]
                        ),
                        use_container_width=True
                    )

                else:

                    st.write(
                        "Brak osób odanonimizowanych automatycznie."
                    )

            with st.expander(
                "🧩 Rejestr.io API → osoby — szczegóły"
            ):

                if resolver_debug:

                    selected_resolver_nip = st.selectbox(
                        "Wybierz NIP:",
                        list(resolver_debug.keys()),
                        key="resolver_debug_nip"
                    )

                    st.dataframe(
                        pd.DataFrame(
                            resolver_debug[selected_resolver_nip]
                        ),
                        use_container_width=True
                    )

                else:

                    st.write(
                        "Brak danych resolvera."
                    )

            # =================================================
            # DEBUG
            # =================================================

            st.divider()

            with st.expander(
                "🔧 Debug — surowa odpowiedź KRS"
            ):

                if debug_data:

                    selected_nip = st.selectbox(
                        "Wybierz NIP:",
                        list(debug_data.keys())
                    )

                    st.json(
                        debug_data[selected_nip]
                    )

                else:

                    st.write(
                        "Brak odpowiedzi KRS."
                    )

    except Exception as e:

        st.error(
            f"Nie udało się odczytać pliku: {e}"
        )
