import streamlit as st
import pandas as pd
import requests

st.set_page_config(
    page_title="Sanctions Screening",
    page_icon="🔎",
    layout="wide"
)

st.title("🔎 Sanctions Screening")

uploaded_file = st.file_uploader(
    "Wybierz plik CSV",
    type=["csv"]
)

if uploaded_file is not None:

    try:
        df = pd.read_csv(uploaded_file, dtype=str)

        st.success(
            f"Plik wczytany poprawnie — {len(df)} rekordów."
        )

        st.subheader("Kontrahenci")
        st.dataframe(df, use_container_width=True)

        if "NIP" not in df.columns:
            st.error("CSV musi zawierać kolumnę 'NIP'.")
            st.stop()

        if st.button("🔎 Sprawdź KRS", type="primary"):

            results = []

            progress = st.progress(0)

            for i, row in df.iterrows():

                nip = str(row["NIP"]).strip()

                # usuwamy ewentualne spacje i myślniki
                nip = nip.replace(" ", "").replace("-", "")

                result = {
                    "NIP": nip,
                    "KRS": "",
                    "Nazwa KRS": "",
                    "REGON": "",
                    "Status": ""
                }

                try:
                    # TODO: tutaj podłączymy właściwe zapytanie KRS
                    # na razie testujemy strukturę aplikacji

                    result["Status"] = "DO SPRAWDZENIA"

                except Exception as e:
                    result["Status"] = f"BŁĄD: {e}"

                results.append(result)

                progress.progress(
                    (i + 1) / len(df)
                )

            results_df = pd.DataFrame(results)

            st.subheader("Wyniki KRS")
            st.dataframe(
                results_df,
                use_container_width=True
            )

    except Exception as e:

        st.error(
            f"Nie udało się odczytać pliku: {e}"
        )
