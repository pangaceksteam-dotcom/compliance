import streamlit as st
import pandas as pd
import requests

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
# NIP → KRS / DANE PODMIOTU PRZEZ MF
# =========================================================

def get_company_from_mf(nip):

    # API MF wymaga daty
    from datetime import date

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
            "krs": subject.get("krs"),
            "name": subject.get("name"),
            "regon": subject.get("regon")
        }, "OK"

    except Exception as e:

        return None, f"Błąd MF: {e}"


# =========================================================
# KRS → DANE Z ODPISU AKTUALNEGO
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

    if response.status_code == 204:
        return None, "KRS 204 — brak danych"

    if response.status_code == 404:
        return None, "KRS 404 — nie znaleziono"

    if response.status_code != 200:
        return None, f"KRS HTTP {response.status_code}"

    try:

        data = response.json()

        # ---------------------------------------------
        # Główna sekcja danych
        # ---------------------------------------------

        odpis = data.get("odpis", {})
        dane = odpis.get("dane", {})
        dzial1 = dane.get("dzial1", {})

        # ---------------------------------------------
        # Dane podmiotu
        # ---------------------------------------------

        dane_podmiotu = dzial1.get(
            "danePodmiotu",
            {}
        )

        identyfikatory = dane_podmiotu.get(
            "identyfikatory",
            {}
        )

        # ---------------------------------------------
        # Adres
        # ---------------------------------------------

        siedziba = dzial1.get(
            "siedzibaIAdres",
            {}
        )

        adres = siedziba.get(
            "adres",
            {}
        )

        # ---------------------------------------------
        # Zwracamy uporządkowane dane
        # ---------------------------------------------

        result = {

            "KRS": krs,

            "Nazwa KRS": dane_podmiotu.get(
                "nazwa",
                ""
            ),

            "Forma prawna": dane_podmiotu.get(
                "formaPrawna",
                ""
            ),

            "NIP KRS": identyfikatory.get(
                "nip",
                ""
            ),

            "REGON KRS": identyfikatory.get(
                "regon",
                ""
            ),

            "Data rejestracji": dzial1.get(
                "dataRejestracji",
                ""
            ),

            "Województwo": adres.get(
                "wojewodztwo",
                ""
            ),

            "Powiat": adres.get(
                "powiat",
                ""
            ),

            "Gmina": adres.get(
                "gmina",
                ""
            ),

            "Miejscowość": adres.get(
                "miejscowosc",
                ""
            ),

            "Ulica": adres.get(
                "ulica",
                ""
            ),

            "Nr domu": adres.get(
                "nrDomu",
                ""
            ),

            "Kod pocztowy": adres.get(
                "kodPocztowy",
                ""
            )
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

        # -------------------------------------------------
        # WCZYTANIE CSV
        # -------------------------------------------------

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

        # -------------------------------------------------
        # PODGLĄD
        # -------------------------------------------------

        st.subheader("Kontrahenci")

        st.dataframe(
            df,
            use_container_width=True
        )

        # -------------------------------------------------
        # SPRAWDZENIE NIP
        # -------------------------------------------------

        if "NIP" not in df.columns:

            st.error(
                "CSV musi zawierać kolumnę 'NIP'."
            )

            st.stop()

        # -------------------------------------------------
        # PRZYCISK
        # -------------------------------------------------

        if st.button(
            "🔎 Sprawdź KRS",
            type="primary"
        ):

            results = []

            progress = st.progress(0)

            status_text = st.empty()

            total = len(df)

            # =============================================
            # PĘTLA
            # =============================================

            for i, row in df.iterrows():

                nip = str(
                    row["NIP"]
                ).strip()

                # Usuwamy spacje i myślniki

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
                )

                status_text.write(
                    f"Sprawdzanie "
                    f"{i + 1} / {total} "
                    f"— NIP: {nip}"
                )

                # -----------------------------------------
                # REKORD WYNIKOWY
                # -----------------------------------------

                result = {

                    "NIP": nip,

                    "Nazwa z CSV": nazwa_csv,

                    "KRS": "",

                    "Nazwa KRS": "",

                    "Forma prawna": "",

                    "REGON": "",

                    "Data rejestracji": "",

                    "Województwo": "",

                    "Powiat": "",

                    "Gmina": "",

                    "Miejscowość": "",

                    "Ulica": "",

                    "Nr domu": "",

                    "Kod pocztowy": "",

                    "Status MF": "",

                    "Status KRS": ""
                }

                # =========================================
                # MF
                # =========================================

                try:

                    mf_data, mf_status = (
                        get_company_from_mf(
                            nip
                        )
                    )

                    result["Status MF"] = (
                        mf_status
                    )

                    if mf_data:

                        krs = (
                            mf_data.get(
                                "krs"
                            )
                        )

                        # =================================
                        # KRS
                        # =================================

                        if krs:

                            krs_data, krs_status = (
                                get_krs_data(
                                    krs
                                )
                            )

                            result["Status KRS"] = (
                                krs_status
                            )

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

            # =============================================
            # KONIEC
            # =============================================

            progress.empty()
            status_text.empty()

            results_df = pd.DataFrame(
                results
            )

            # =============================================
            # WYNIKI
            # =============================================

            st.subheader(
                "Wyniki KRS"
            )

            st.dataframe(
                results_df,
                use_container_width=True,
                height=500
            )

            # =============================================
            # STATYSTYKI
            # =============================================

            col1, col2, col3 = st.columns(3)

            with col1:

                st.metric(
                    "Kontrahenci",
                    len(results_df)
                )

            with col2:

                st.metric(
                    "Znaleziono KRS",
                    (
                        results_df["KRS"]
                        .astype(bool)
                        .sum()
                    )
                )

            with col3:

                st.metric(
                    "Błędy MF",
                    (
                        ~results_df[
                            "Status MF"
                        ].eq("OK")
                    ).sum()
                )

    except Exception as e:

        st.error(
            f"Nie udało się odczytać pliku: {e}"
        )
