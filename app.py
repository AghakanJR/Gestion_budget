import streamlit as st
import pandas as pd
import plotly.express as px
from datetime import datetime

# Configuration de la page
st.set_page_config(page_title="Mon Budget", page_icon="💰", layout="centered")

st.title("💰 Ma Gestion Budgétaire Personnalisée")
st.write("Sélectionnez la période, puis définissez vos revenus et dépenses.")

# ==========================================
# NOUVEAU : SÉLECTION DE LA PÉRIODE
# ==========================================
st.header("📅 Sélection de la période")

# Récupérer l'année et le mois actuels par défaut
annee_actuelle = datetime.now().year
mois_actuel_index = datetime.now().month - 1
liste_mois = [
    "Janvier", "Février", "Mars", "Avril", "Mai", "Juin", 
    "Juillet", "Août", "Septembre", "Octobre", "Novembre", "Décembre"
]

col_annee, col_mois = st.columns([1, 3])

with col_annee:
    annee_selectionnee = st.number_input("Année", min_value=2020, max_value=2050, value=annee_actuelle, step=1)

with col_mois:
    # La fameuse "petite barre" pour switcher entre les mois
    mois_selectionne = st.select_slider(
        "Mois", 
        options=liste_mois, 
        value=liste_mois[mois_actuel_index]
    )

# On crée une clé unique pour cette période (ex: "Mars_2026")
cle_periode = f"{mois_selectionne}_{annee_selectionnee}"


# ==========================================
# 1. SECTION REVENUS
# ==========================================
st.header("1. Mes Revenus")

# Clé spécifique pour les revenus de CE mois
cle_revenus = f"revenus_{cle_periode}"

# Si ce mois n'a pas encore de données, on crée un tableau par défaut
if cle_revenus not in st.session_state:
    st.session_state[cle_revenus] = pd.DataFrame([
        {"Source de revenu": "Salaire net", "Montant (€)": 2000.0},
        {"Source de revenu": "Prime", "Montant (€)": 0.0}
    ])

edited_revenus = st.data_editor(
    st.session_state[cle_revenus],
    num_rows="dynamic",
    use_container_width=True,
    hide_index=True,
    column_config={
        "Source de revenu": st.column_config.TextColumn("Source de revenu", required=True),
        "Montant (€)": st.column_config.NumberColumn("Montant (€)", min_value=0.0, format="%.2f", required=True)
    },
    key=f"editor_{cle_revenus}" # Clé unique pour le composant éditeur
)

st.session_state[cle_revenus] = edited_revenus
df_rev_clean = edited_revenus.dropna(subset=["Source de revenu", "Montant (€)"])
total_revenus = df_rev_clean["Montant (€)"].sum()


# ==========================================
# 2. SECTION DÉPENSES
# ==========================================
st.header("2. Mes Dépenses")

grandes_familles = [
    "Logement", "Assurances", "Alimentation", 
    "Transports", "Loisirs", "Santé", 
    "Abonnements", "Autre"
]

# Clé spécifique pour les dépenses de CE mois
cle_depenses = f"depenses_{cle_periode}"

if cle_depenses not in st.session_state:
    st.session_state[cle_depenses] = pd.DataFrame([
        {"Grande Famille": "Logement", "Sous-catégorie": "Loyer", "Montant (€)": 800.0},
        {"Grande Famille": "Alimentation", "Sous-catégorie": "Courses", "Montant (€)": 300.0}
    ])

edited_df = st.data_editor(
    st.session_state[cle_depenses],
    num_rows="dynamic",
    use_container_width=True,
    hide_index=True,
    column_config={
        "Grande Famille": st.column_config.SelectboxColumn("Grande Famille", options=grandes_familles, required=True),
        "Sous-catégorie": st.column_config.TextColumn("Sous-catégorie", required=True),
        "Montant (€)": st.column_config.NumberColumn("Montant (€)", min_value=0.0, format="%.2f", required=True)
    },
    key=f"editor_{cle_depenses}"
)

st.session_state[cle_depenses] = edited_df
df_clean = edited_df.dropna(subset=["Grande Famille", "Montant (€)"])
total_depenses = df_clean["Montant (€)"].sum()


# ==========================================
# 3. GRAPHIQUE ET BILAN
# ==========================================
st.subheader(f"📊 Répartition de mes dépenses - {mois_selectionne} {annee_selectionnee}")
if total_depenses > 0:
    fig = px.sunburst(
        df_clean, 
        path=['Grande Famille', 'Sous-catégorie'], 
        values='Montant (€)',
        color='Grande Famille',
        color_discrete_sequence=px.colors.qualitative.Pastel
    )
    fig.update_traces(textinfo="label+percent entry")
    st.plotly_chart(fig, use_container_width=True)

reste_a_vivre = total_revenus - total_depenses

st.header("3. Bilan et Épargne")
col_bilan1, col_bilan2, col_bilan3 = st.columns(3)
col_bilan1.metric(label="Total Revenus", value=f"{total_revenus:.2f} €")
col_bilan2.metric(label="Total Dépenses", value=f"{total_depenses:.2f} €")
col_bilan3.metric(label="Reste à vivre", value=f"{reste_a_vivre:.2f} €", delta=f"{reste_a_vivre:.2f} €", delta_color="normal" if reste_a_vivre >=0 else "inverse")

# ==========================================
# 4. OBJECTIF D'ÉPARGNE
# ==========================================
st.write("---")
if reste_a_vivre > 0:
    epargne = st.slider(
        "Combien souhaitez-vous épargner ce mois-ci ?", 
        min_value=0.0, 
        max_value=float(reste_a_vivre), 
        value=float(reste_a_vivre * 0.2), 
        step=10.0,
        key=f"slider_{cle_periode}" # Le slider s'adapte aussi au mois
    )
    
    argent_de_poche = reste_a_vivre - epargne
    st.success(f"🎯 En épargnant **{epargne:.2f} €**, il vous restera **{argent_de_poche:.2f} €** pour les imprévus ou vous faire plaisir !")
else:
    st.error("⚠️ Attention, vos dépenses dépassent ou égalent vos revenus. Vous êtes à découvert ou à l'équilibre strict.")