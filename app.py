import streamlit as st
import pandas as pd
import plotly.express as px
from datetime import datetime

# Configuration de la page (passée en mode "wide" pour avoir de la place pour les colonnes)
st.set_page_config(page_title="Mon Budget", page_icon="💰", layout="wide")

st.title("💰 Ma Gestion Budgétaire")

# ==========================================
# PÉRIODE
# ==========================================
st.header("📅 Sélection de la période")
annee_actuelle = datetime.now().year
mois_actuel_index = datetime.now().month - 1
liste_mois = ["Janvier", "Février", "Mars", "Avril", "Mai", "Juin", "Juillet", "Août", "Septembre", "Octobre", "Novembre", "Décembre"]

col_annee, col_mois = st.columns([1, 3])
with col_annee:
    annee_selectionnee = st.number_input("Année", min_value=2020, max_value=2050, value=annee_actuelle, step=1)
with col_mois:
    mois_selectionne = st.select_slider("Mois", options=liste_mois, value=liste_mois[mois_actuel_index])

cle_periode = f"{mois_selectionne}_{annee_selectionnee}"

# ==========================================
# 1. REVENUS
# ==========================================
st.header("1. Mes Revenus")
cle_revenus = f"revenus_{cle_periode}"

if cle_revenus not in st.session_state:
    st.session_state[cle_revenus] = pd.DataFrame([
        {"Source de revenu": "Salaire net", "Montant (€)": 2000.0},
        {"Source de revenu": "Autre", "Montant (€)": 0.0}
    ])

edited_revenus = st.data_editor(
    st.session_state[cle_revenus],
    num_rows="dynamic",
    use_container_width=True,
    hide_index=True,
    key=f"editor_{cle_revenus}"
)

st.session_state[cle_revenus] = edited_revenus
df_rev_clean = edited_revenus.dropna(subset=["Source de revenu", "Montant (€)"])
total_revenus = df_rev_clean["Montant (€)"].sum()

# ==========================================
# 2. DÉPENSES (Nouvelle disposition en colonnes)
# ==========================================
st.header("2. Mes Dépenses")
st.write("Remplissez vos sous-catégories directement dans les tableaux correspondants :")

categories_meres = ["Logement", "Alimentation", "Transports", "Assurances", "Loisirs", "Autre"]
toutes_depenses = [] # Liste pour regrouper toutes les données à la fin

# On crée 3 colonnes pour afficher les tableaux côte à côte
cols = st.columns(3)

for index, categorie in enumerate(categories_meres):
    cle_depense_cat = f"depenses_{categorie}_{cle_periode}"
    
    # Tableau par défaut pour chaque catégorie
    if cle_depense_cat not in st.session_state:
        st.session_state[cle_depense_cat] = pd.DataFrame([
            {"Sous-catégorie": "", "Montant (€)": 0.0}
        ])
    
    # On place le tableau dans l'une des 3 colonnes
    with cols[index % 3]:
        st.subheader(f"📂 {categorie}")
        edited_df = st.data_editor(
            st.session_state[cle_depense_cat],
            num_rows="dynamic",
            use_container_width=True,
            hide_index=True,
            key=f"editor_{cle_depense_cat}"
        )
        st.session_state[cle_depense_cat] = edited_df
        
        # On nettoie et on ajoute la catégorie mère pour le graphique final
        df_clean = edited_df.dropna(subset=["Sous-catégorie"]).copy()
        df_clean = df_clean[df_clean["Sous-catégorie"].str.strip() != ""] # Enlever les lignes vides
        if not df_clean.empty:
            df_clean["Grande Famille"] = categorie
            toutes_depenses.append(df_clean)

# Fusionner toutes les dépenses pour les calculs et le graphique
if toutes_depenses:
    df_toutes_depenses = pd.concat(toutes_depenses, ignore_index=True)
    total_depenses = df_toutes_depenses["Montant (€)"].sum()
else:
    df_toutes_depenses = pd.DataFrame(columns=["Grande Famille", "Sous-catégorie", "Montant (€)"])
    total_depenses = 0.0

# ==========================================
# 3. GRAPHIQUE ET BILAN
# ==========================================
st.write("---")
col_graph, col_bilan = st.columns([1, 1])

with col_graph:
    st.subheader("📊 Répartition")
    if total_depenses > 0:
        fig = px.sunburst(
            df_toutes_depenses, 
            path=['Grande Famille', 'Sous-catégorie'], 
            values='Montant (€)',
            color='Grande Famille'
        )
        fig.update_traces(textinfo="label+percent entry")
        st.plotly_chart(fig, use_container_width=True)
    else:
        st.info("Ajoutez des dépenses pour voir le graphique.")

with col_bilan:
    reste_a_vivre = total_revenus - total_depenses
    st.subheader("📈 Bilan du mois")
    
    st.metric(label="Total Revenus", value=f"{total_revenus:.2f} €")
    st.metric(label="Total Dépenses", value=f"{total_depenses:.2f} €")
    st.metric(label="Reste à vivre", value=f"{reste_a_vivre:.2f} €", delta=f"{reste_a_vivre:.2f} €", delta_color="normal" if reste_a_vivre >=0 else "inverse")

    if reste_a_vivre > 0:
        epargne = st.slider("Objectif d'épargne", 0.0, float(reste_a_vivre), float(reste_a_vivre * 0.2), 10.0, key=f"epargne_{cle_periode}")
        st.success(f"🎯 Reste pour imprévus/plaisir : **{(reste_a_vivre - epargne):.2f} €**")