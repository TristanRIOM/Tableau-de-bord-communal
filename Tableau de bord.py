import streamlit as st

st.title("Mon tableau de bord")
st.write("Bonjour, ça marche !")

commune = st.text_input("Entrez une commune")
if commune:
    st.write(f"Vous avez saisi : {commune}")
    