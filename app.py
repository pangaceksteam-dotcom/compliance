import streamlit as st
import pandas as pd
import requests

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
# UPLOAD CSV
# ---------------------------------------------------------

uploaded_file = st.file_uploader(
    "Wybierz plik CSV",
    type=["csv"]
)

if uploaded_file is not None:

    try:
        # Wczytujemy wszystko jako tekst
        df = pd.read_csv(
            uploaded_file,
            dtype=str
        )

        # Usuwamy spacje z nazw kolumn
        df.columns = df.columns.str.strip()

        st.success(
            f"Plik wczytany poprawnie — {len(df)} rekordów."
        )

        # -------------------------------------------------
        # PODGLĄD CSV
        # -------------------------------------------------

        st.subheader("Kontrahenci")

        st.dataframe(
            df,
            use_container_width=True
        )

        # -------------------------------------------------
        # SPRAWDZENIE KOLUMNY NIP
        # -------------------------------------------------

        if "NIP" not in df.columns:

            st.error(
                "CSV musi zawierać kolumnę 'NIP'."
            )

            st.stop()

        # -------------------------------------------------
        # PRZYCISK KRS
        # -------------------------------------------------

        if st.button(
            "🔎 Sprawdź KRS",
            type="primary"
        ):

            results = []

            progress = st.progress(0)

            status_text = st.empty()

            # ---------------------------------------------
            # PRZEJŚCIE PO KONTRAHENTACH
            # ---------------------------------------------

            for i, row in df.iterrows():

                nip = str(row["NIP"]).strip()

                # Usuwamy spacje i myślniki z NIP
                nip = (
                    nip
                    .replace(" ", "")
                    .replace("-", "")
                )

                result = {
                    "NIP": nip,
                    "KRS": "",
                    "Nazwa KRS": "",
                    "REGON": "",
                    "Status": ""
                }

                status_text.write(
                    f"Sprawdzanie {i + 1} / {len(df)} — NIP: {nip}"
                )

                try:

                    # -------------------------------------
                    # TEST API KRS
                    # -------------------------------------
                    #
                    # Na tym etapie używamy jednego
                    # konkretnego KRS tylko po to,
                    # żeby sprawdzić połączenie z API.
                    #

                    krs = "0000009831"

                    url = (
                        "https://api-krs.ms.gov.pl/api/krs/"
                        f"OdpisAktualny/{krs}"
                        "?rejestr=P&format=json"
                    )

                    response = requests.get(
                        url,
                        timeout=20
                    )

                    # -------------------------------------
                    # ODPOWIEDŹ API
                    # -------------------------------------

                    if response.status_code == 200:

                        data = response.json()

                        result["KRS"] = krs
                        result["Status"] = "OK"

                    else:

                        result["Status"] = (
                            f"KRS HTTP {response.status_code}"
                        )

                except requests.exceptions.Timeout:

                    result["Status"] = (
                        "BŁĄD — przekroczono limit czasu"
                    )

                except requests.exceptions.RequestException as e:

                    result["Status"] = (
                        f"BŁĄD połączenia: {e}"
                    )

                except Exception as e:

                    result["Status"] = (
                        f"BŁĄD: {e}"
                    )

                # Dodajemy wynik
                results.append(result)

                # Aktualizacja progress bara
                progress.progress(
                    (i + 1) / len(df)
                )

            # -------------------------------------------------
            # WYNIKI
            # -------------------------------------------------

            status_text.empty()

            progress.empty()

            results_df = pd.DataFrame(
                results
            )

            st.subheader("Wyniki KRS")

            st.dataframe(
                results_df,
                use_container_width=True
            )

            # -------------------------------------------------
            # PODSUMOWANIE
            # -------------------------------------------------

            ok_count = (
                results_df["Status"]
                .eq("OK")
                .sum()
            )

            error_count = (
                len(results_df) - ok_count
            )

            col1, col2 = st.columns(2)

            with col1:
                st.metric(
                    "Poprawne odpowiedzi KRS",
                    ok_count
                )

            with col2:
                st.metric(
                    "Błędy",
                    error_count
                )

    except Exception as e:

        st.error(
            f"Nie udało się odczytać pliku: {e}"
        )
