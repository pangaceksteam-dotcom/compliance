import streamlit as st
import pandas as pd

st.set_page_config(
    page_title="Sanctions Screening",
    page_icon="🔎",
    layout="wide"
)

st.title("🔎 Sanctions Screening")
st.write("Wgraj plik CSV z kontrahentami.")

uploaded_file = st.file_uploader(
    "Wybierz plik CSV",
    type=["csv"]
)

if uploaded_file is not None:

    try:
        df = pd.read_csv(uploaded_file)

        st.success(
            f"Plik wczytany poprawnie — {len(df)} kontrahentów."
        )

        st.subheader("Podgląd danych")

        st.dataframe(
            df,
            use_container_width=True
        )

        st.subheader("Wykryte kolumny")

        for column in df.columns:
            st.write(f"- `{column}`")

    except Exception as e:

        st.error(
            f"Nie udało się odczytać pliku: {e}"
        )
