import streamlit as st
import pandas as pd
import requests
from datetime import date


# =========================================================
# USTAWIENIA APLIKACJI
# =========================================================

st.set_page_config(
    page_title="Sanctions Screening",
    page_icon="🔎",
    layout="wide"
)

st.title("🔎 Sanctions Screening")
st.write("Wgraj plik CSV z kontrahentami.")


# =========================================================
# FUNKCJA POMOCNICZA
# =========================================================

def first_value(*values):
    """
    Zwraca pierwszą niepustą wartość.
    """

    for value in values:

        if value is not None:

            value = str(value).strip()

            if value != "":
                return value

    return ""


# =========================================================
# MF API
# NIP -> KRS / REGON / NAZWA
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
        "https://api-krs.ms.gov.pl/api/krs/"
        f"OdpisAktualny/{krs}"
        "?rejestr=P&format=json"
    )

    response = requests.get(
        url,
        timeout=20
    )

    # Brak danych
    if response.status_code == 204:

        return None, "KRS 204 — brak danych"

    # Nie znaleziono
    if response.status_code == 404:

        return None, "KRS 404 — nie znaleziono"

    # Inny błąd
    if response.status_code != 200:

        return None, f"KRS HTTP {response.status_code}"

    try:

        data = response.json()

        # =================================================
        # STRUKTURA ODPISU KRS
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
        # DANE PODSTAWOWE
        # =================================================

        nazwa = first_value(
            dane_podmiotu.get("nazwa"),
            dane_podmiotu.get("nazwaSkrocona")
        )

        nip = first_value(
            identyfikatory.get("nip")
        )

        regon = first_value(
            identyfikatory.get("regon")
        )

        forma_prawna = first_value(
            dane_podmiotu.get("formaPrawna")
        )

        # =================================================
        # DATA REJESTRACJI
        # =================================================

        data_rejestracji = first_value(
            dzial1.get("dataRejestracji"),
            dane_podmiotu.get("dataRejestracji"),
            dzial1.get("dataWpisu")
        )

        # =================================================
        # ADRES
        # =================================================

        wojewodztwo = first_value(
            adres.get("wojewodztwo"),
            siedziba.get("wojewodztwo")
        )

        powiat = first_value(
            adres.get("powiat"),
            siedziba.get("powiat")
        )

        gmina = first_value(
            adres.get("gmina"),
            siedziba.get("gmina")
        )

        miejscowosc = first_value(
            adres.get("miejscowosc"),
            siedziba.get("miejscowosc")
        )

        ulica = first_value(
            adres.get("ulica")
        )

        nr_domu = first_value(
            adres.get("nrDomu")
        )

        nr_lokalu = first_value(
            adres.get("nrLokalu")
        )

        kod_pocztowy = first_value(
            adres.get("kodPocztowy")
        )

        # =================================================
        # ZŁOŻENIE WYNIKU
        # =================================================

        result = {

            "KRS": krs,

            "Nazwa KRS": nazwa,

            "Forma prawna": forma_prawna,

            "NIP KRS": nip,

            "REGON KRS": regon,

            "Data rejestracji": data_rejestracji,

            "Województwo": wojewodztwo,

            "Powiat": powiat,

            "Gmina": gmina,

            "Miejscowość": miejscowosc,

            "Ulica": ulica,

            "Nr domu": nr_domu,

            "Nr lokalu": nr_lokalu,

            "Kod pocztowy": kod_pocztowy
        }

        return result, "OK"

    except Exception as e:

        return None, f"Błąd parsowania KRS: {e}"


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

        # Usuwamy białe znaki z nazw kolumn
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

        st.subheader("Kontrahenci")

        st.dataframe(
            df,
            use_container_width=True
        )

        # =================================================
        # WALIDACJA KOLUMNY NIP
        # =================================================

        if "NIP" not in df.columns:

            st.error(
                "CSV musi zawierać kolumnę 'NIP'."
            )

            st.stop()

        # =================================================
        # PRZYCISK SCREENINGU KRS
        # =================================================

        if st.button(
            "🔎 Sprawdź KRS",
            type="primary"
        ):

            results = []

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

                # ---------------------------------------------
                # STATUS
                # ---------------------------------------------

                status_text.write(
                    f"Sprawdzanie "
                    f"{i + 1} / {total} "
                    f"— NIP: {nip}"
                )

                # ---------------------------------------------
                # PUSTY REKORD WYNIKOWY
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

                    "Województwo": "",

                    "Powiat": "",

                    "Gmina": "",

                    "Miejscowość": "",

                    "Ulica": "",

                    "Nr domu": "",

                    "Nr lokalu": "",

                    "Kod pocztowy": "",

                    "Status MF": "",

                    "Status KRS": ""
                }

                # =================================================
                # MF — NIP -> KRS
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

                    # ---------------------------------------------
                    # JEŻELI MF ZWRÓCIŁ DANE
                    # ---------------------------------------------

                    if mf_data:

                        krs = mf_data.get(
                            "krs",
                            ""
                        )

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

                        result["KRS"] = krs

                        # -----------------------------------------
                        # JEŻELI JEST KRS
                        # -----------------------------------------

                        if krs:

                            # =====================================
                            # KRS API
                            # =====================================

                            krs_data, krs_status = (
                                get_krs_data(
                                    krs
                                )
                            )

                            result["Status KRS"] = (
                                krs_status
                            )

                            # -------------------------------------
                            # PRZEPISANIE DANYCH KRS
                            # -------------------------------------

                            if krs_data:

                                for key in krs_data:

                                    if key in result:

                                        result[key] = (
                                            krs_data[key]
                                        )

                        else:

                            result["Status KRS"] = (
                                "Brak numeru KRS"
                            )

                    else:

                        result["Status KRS"] = (
                            "Nie znaleziono KRS"
                        )

                # =================================================
                # BŁĄD
                # =================================================

                except Exception as e:

                    result["Status MF"] = (
                        f"BŁĄD: {e}"
                    )

                # =================================================
                # DODAJ WYNIK
                # =================================================

                results.append(
                    result
                )

                # =================================================
                # PROGRESS
                # =================================================

                progress.progress(
                    (i + 1) / total
                )

            # =================================================
            # KONIEC
            # =================================================

            progress.empty()

            status_text.empty()

            results_df = pd.DataFrame(
                results
            )

            # =================================================
            # WYNIKI
            # =================================================

            st.subheader(
                "Wyniki KRS"
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
                    "Znaleziono KRS",
                    found_krs
                )

            with col3:

                st.metric(
                    "Błędy MF",
                    mf_errors
                )

            with col4:

                st.metric(
                    "Błędy KRS",
                    krs_errors
                )

            # =================================================
            # DEBUG — OPCJONALNIE
            # =================================================

            with st.expander(
                "🛠️ Debug — dane KRS"
            ):

                st.write(
                    "Jeżeli jakieś pole KRS jest puste, "
                    "tutaj będziemy mogli później "
                    "podejrzeć strukturę odpowiedzi API."
                )
