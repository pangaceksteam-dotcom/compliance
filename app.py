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
        nip = nip.replace(" ", "").replace("-", "")

        result = {
            "NIP": nip,
            "KRS": "",
            "Nazwa KRS": "",
            "REGON": "",
            "Status": ""
        }

        try:
            # TEST:
            # na razie sprawdzamy jeden znany numer KRS
            krs = "0000009831"

            url = (
                f"https://api-krs.ms.gov.pl/api/krs/"
                f"OdpisAktualny/{krs}"
                f"?rejestr=P&format=json"
            )

            response = requests.get(
                url,
                timeout=20
            )

            if response.status_code == 200:

                data = response.json()

                result["KRS"] = krs

                # Tymczasowo pokazujemy cały JSON
                result["Status"] = "OK"

            else:
                result["Status"] = (
                    f"KRS HTTP {response.status_code}"
                )

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
