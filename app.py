import streamlit as st
import pandas as pd
import requests
from datetime import date


# =========================================================
# USTAWIENIA
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

        return {
            "krs": first_value(
                subject.get("krs")
            ),

            "name": first_value(
                subject.get("name")
            ),

            "regon": first_value(
                subject.get("regon")
            )

        }, "OK"

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
        # DEBUG - POKAZUJEMY SUROWY JSON
        # =================================================

        # -------------------------------------------------
        # STRUKTURA KRS
        # -------------------------------------------------

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

        dane_podmiotu = dzial1.get(
            "danePodmiotu",
            {}
        )

        identyfikatory = dane_podmiotu.get(
            "identyfikatory",
            {}
        )

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
        # NAGŁÓWEK
        # =================================================

        naglowek = data.get(
            "naglowekA",
            {}
        )

        # =================================================
        # DANE PODMIOTU
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
        # INNE DATY
        # =================================================

        data_ostatniego_wpisu = first_value(

            dzial1.get(
                "dataOstatniegoWpisu"
            ),

            dzial1.get(
                "dataWpisu"
            ),

            naglowek.get(
                "dataOstatniegoWpisu"
            )
        )

        stan_na_dzien = first_value(

            dzial1.get(
                "stanNaDzien"
            ),

            dzial1.get(
                "stanZDnia"
            ),

            naglowek.get(
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
        # PODGLĄD
        # =================================================

        st.subheader(
            "Kontrahenci"
        )

        st.dataframe(
            df,
            use_container_width=True
        )

        # =================================================
        # WALIDACJA
        # =================================================

        if "NIP" not in df.columns:

            st.error(
                "CSV musi zawierać kolumnę 'NIP'."
            )

            st.stop()

        # =================================================
        # PRZYCISK
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
            # PĘTLA
            # =================================================

            for i, row in df.iterrows():

                nip = str(
                    row["NIP"]
                ).strip()

                nip = (
                    nip
                    .replace(" ", "")
                    .replace("-", "")
                )

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

                    "Status KRS": ""
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

                            result["Status KRS"] = (
                                krs_status
                            )

                            # -----------------------------
                            # ZAPIS JSON DO DEBUG
                            # -----------------------------

                            if raw_json is not None:

                                debug_data[nip] = raw_json

                            # -----------------------------
                            # DANE KRS
                            # -----------------------------

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
                # DODAJEMY WYNIK
                # -----------------------------------------

                results.append(
                    result
                )

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
            # DEBUG JSON
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
                        "Brak odpowiedzi KRS do pokazania."
                    )

    except Exception as e:

        st.error(
            f"Nie udało się odczytać pliku: {e}"
        )
