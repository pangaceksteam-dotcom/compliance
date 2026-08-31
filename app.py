import streamlit as st
import pandas as pd
import requests
from datetime import date

# ---------------------------------------------------------
# USTAWIENIA
# ---------------------------------------------------------

st.set_page_config(
    page_title="Sanctions Screening",
    page_icon="🔎",
    layout="wide"
)

st.title("🔎 Sanctions Screening")
st.write("Wgraj plik CSV z kontrahentami.")

# ---------------------------------------------------------
# FUNKCJA: NIP → KRS przez API MF
# ---------------------------------------------------------

def get_krs_from_nip(nip):

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

    data = response.json()

    try:
        subject = data["result"]["subject"]

        krs = subject.get("krs")
        name = subject.get("name")
        regon = subject.get("regon")

        return {
            "krs": krs,
            "name": name,
            "regon": regon
        }, "OK"

    except Exception as e:

        return None, f"Błąd odczytu MF: {e}"


# ---------------------------------------------------------
# FUNKCJA: KRS → DANE Z KRS
# ---------------------------------------------------------

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

    if response.status_code != 200:
        return None, f"KRS HTTP {response.status_code}"

    try:
        return response.json(), "OK"

    except Exception as e:
        return None, f"Błąd JSON KRS: {e}"


# ---------------------------------------------------------
# UPLOAD CSV
# ---------------------------------------------------------

uploaded_file = st.file_uploader(
    "Wybierz plik CSV",
    type=["csv"]
)

if uploaded_file is not None:

    try:

        df = pd.read_csv(
            uploaded_file,
            dtype=str
        )

        df.columns = df.columns.str.strip()

        st.success(
            f"Plik wczytany poprawnie — {len(df)} rekordów."
        )

        st.subheader("Kontrahenci")

        st.dataframe(
            df,
            use_container_width=True
        )

        # -------------------------------------------------
        # WALIDACJA NIP
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

            # ---------------------------------------------
            # PĘTLA PO KONTRAHENTACH
            # ---------------------------------------------

            for i, row in df.iterrows():

                nip = str(row["NIP"]).strip()

                nip = (
                    nip
                    .replace(" ", "")
                    .replace("-", "")
                )

                status_text.write(
                    f"Sprawdzanie {i + 1} / {total} — NIP: {nip}"
                )

                result = {
                    "NIP": nip,
                    "Nazwa z CSV": row.get("Nazwa", ""),
                    "KRS": "",
                    "Nazwa z MF": "",
                    "REGON": "",
                    "Status MF": "",
                    "Status KRS": ""
                }

                # -----------------------------------------
                # NIP → KRS
                # -----------------------------------------

                try:

                    mf_data, mf_status = get_krs_from_nip(nip)

                    result["Status MF"] = mf_status

                    if mf_data:

                        result["KRS"] = (
                            mf_data.get("krs") or ""
                        )

                        result["Nazwa z MF"] = (
                            mf_data.get("name") or ""
                        )

                        result["REGON"] = (
                            mf_data.get("regon") or ""
                        )

                        # ---------------------------------
                        # KRS → DANE KRS
                        # ---------------------------------

                        if result["KRS"]:

                            krs_data, krs_status = (
                                get_krs_data(
                                    result["KRS"]
                                )
                            )

                            result["Status KRS"] = (
                                krs_status
                            )

                        else:

                            result["Status KRS"] = (
                                "Brak numeru KRS"
                            )

                    else:

                        result["Status KRS"] = (
                            "Nie znaleziono KRS"
                        )

                except Exception as e:

                    result["Status MF"] = (
                        f"BŁĄD: {e}"
                    )

                results.append(result)

                progress.progress(
                    (i + 1) / total
                )

            # ---------------------------------------------
            # WYNIKI
            # ---------------------------------------------

            progress.empty()
            status_text.empty()

            results_df = pd.DataFrame(
                results
            )

            st.subheader("Wyniki")

            st.dataframe(
                results_df,
                use_container_width=True
            )

            # ---------------------------------------------
            # STATYSTYKI
            # ---------------------------------------------

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
                        ~results_df["Status MF"]
                        .eq("OK")
                    ).sum()
                )

    except Exception as e:

        st.error(
            f"Nie udało się odczytać pliku: {e}"
        )
