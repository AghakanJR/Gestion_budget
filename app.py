import streamlit as st
import pandas as pd
import plotly.express as px
from datetime import datetime
import json
import gspread
import streamlit_authenticator as stauth

# Configuration de la page
st.set_page_config(page_title="Mon Budget", page_icon="💰", layout="wide")

# ==========================================
# 1. SYSTÈME DE CONNEXION (Phase 1)
# ==========================================
# On demande à Python de sécuriser (hasher) nos mots de passe
mots_de_passe_en_clair = ["123456", "budget2026"]
passwords_hashes = stauth.Hasher(mots_de_passe_en_clair).generate()

# Notre petite base de données d'utilisateurs
credentials = {
    "usernames": {
        "admin": {
            "email": "admin@budget.com",
            "name": "Administrateur",
            "password": passwords_hashes[0] 
        },
        "alice": {
            "email": "alice@budget.com",
            "name": "Alice",
            "password": passwords_hashes[1]
        }
    }
}

# Configuration de la boîte de connexion
authenticator = stauth.Authenticate(
    credentials,
    "cookie_budget_app",        # Nom du cookie
    "cle_secrete_super_robuste",# Clé de sécurité 
    cookie_expiry_days=30       # L'utilisateur reste connecté 30 jours
)

# Affiche le formulaire de connexion à l'écran
authenticator.login()

# ==========================================
# 2. L'APPLICATION BUDGET (Si connecté)
# ==========================================
if st.session_state["authentication_status"]:
    
    # Affiche un bouton pour se déconnecter dans le menu de gauche
    authenticator.logout('Se déconnecter', 'sidebar')
    
    # On récupère l'identité de la personne connectée !
    nom_utilisateur = st.session_state["name"]
    id_utilisateur = st.session_state["username"]
    
    st.title(f"💰 Ma Gestion Budgétaire ({nom_utilisateur})")

    # --- PÉRIODE ---
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

    # --- REVENUS ---
    st.header("1. Mes Revenus")
    cle_revenus = f"revenus_{cle_periode}"
    if cle_revenus not in st.session_state:
        st.session_state[cle_revenus] = pd.DataFrame([{"Source de revenu": "Salaire net", "Montant (€)": 2000.0}])

    edited_revenus = st.data_editor(st.session_state[cle_revenus], num_rows="dynamic", use_container_width=True, hide_index=True, key=f"editor_{cle_revenus}")
    st.session_state[cle_revenus] = edited_revenus
    df_rev_clean = edited_revenus.dropna(subset=["Source de revenu", "Montant (€)"])
    total_revenus = df_rev_clean["Montant (€)"].sum()

    # --- DÉPENSES ---
    st.header("2. Mes Dépenses")
    categories_meres = ["Logement", "Alimentation", "Transports", "Assurances", "Loisirs", "Autre"]
    toutes_depenses = []

    cols = st.columns(3)
    for index, categorie in enumerate(categories_meres):
        cle_depense_cat = f"depenses_{categorie}_{cle_periode}"
        if cle_depense_cat not in st.session_state:
            st.session_state[cle_depense_cat] = pd.DataFrame([{"Sous-catégorie": "", "Montant (€)": 0.0}])
        
        with cols[index % 3]:
            st.subheader(f"📂 {categorie}")
            edited_df = st.data_editor(st.session_state[cle_depense_cat], num_rows="dynamic", use_container_width=True, hide_index=True, key=f"editor_{cle_depense_cat}")
            st.session_state[cle_depense_cat] = edited_df
            
            df_clean = edited_df.dropna(subset=["Sous-catégorie"]).copy()
            df_clean = df_clean[df_clean["Sous-catégorie"].str.strip() != ""]
            if not df_clean.empty:
                df_clean["Grande Famille"] = categorie
                toutes_depenses.append(df_clean)

    if toutes_depenses:
        df_toutes_depenses = pd.concat(toutes_depenses, ignore_index=True)
        total_depenses = df_toutes_depenses["Montant (€)"].sum()
    else:
        df_toutes_depenses = pd.DataFrame(columns=["Grande Famille", "Sous-catégorie", "Montant (€)"])
        total_depenses = 0.0

    # --- GRAPHIQUE ET BILAN ---
    st.write("---")
    col_graph, col_bilan = st.columns([1, 1])

    with col_graph:
        st.subheader("📊 Répartition")
        if total_depenses > 0:
            fig = px.sunburst(df_toutes_depenses, path=['Grande Famille', 'Sous-catégorie'], values='Montant (€)', color='Grande Famille')
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

    # ==========================================
    # 3. SAUVEGARDE DANS GOOGLE SHEETS
    # ==========================================
    st.write("---")
    st.header("💾 Enregistrer mes données")
    
    if st.button("🚀 Sauvegarder ce mois dans ma base de données"):
        try:
            creds_dict = json.loads(st.secrets["google_secret"])
            client = gspread.service_account_from_dict(creds_dict)
            
            # /!\ N'OUBLIE PAS DE METTRE TON VRAI LIEN GOOGLE SHEETS ICI /!\
            sheet = client.open_by_url("https://docs.google.com/spreadsheets/d/12Sx9pwAmphhQGIxMtFrBJZrPEhZFntEUnknTPKi2oyo/edit?hl=fr&pli=1&gid=481933918#gid=481933918")
            
            # --- Envoi des Revenus ---
            if not df_rev_clean.empty:
                ws_revenus = sheet.worksheet("Revenus")
                df_rev_save = df_rev_clean.copy()
                df_rev_save["Mois"] = mois_selectionne
                df_rev_save["Année"] = annee_selectionnee
                df_rev_save["Utilisateur"] = id_utilisateur # On ajoute l'identité !
                
                # Ordre des colonnes modifié pour mettre l'utilisateur à la fin
                lignes_revenus = df_rev_save[["Mois", "Année", "Source de revenu", "Montant (€)", "Utilisateur"]].astype(str).values.tolist()
                ws_revenus.append_rows(lignes_revenus, value_input_option="USER_ENTERED")
                
            # --- Envoi des Dépenses ---
            if not df_toutes_depenses.empty:
                ws_depenses = sheet.worksheet("Depenses")
                df_dep_save = df_toutes_depenses.copy()
                df_dep_save["Mois"] = mois_selectionne
                df_dep_save["Année"] = annee_selectionnee
                df_dep_save["Utilisateur"] = id_utilisateur # On ajoute l'identité !
                
                # Ordre des colonnes modifié
                lignes_depenses = df_dep_save[["Mois", "Année", "Grande Famille", "Sous-catégorie", "Montant (€)", "Utilisateur"]].astype(str).values.tolist()
                ws_depenses.append_rows(lignes_depenses, value_input_option="USER_ENTERED")
                
            st.success(f"✅ Félicitations {nom_utilisateur} ! Vos données ont bien été sauvegardées.")
            
        except Exception as e:
            st.error(f"❌ Une erreur s'est produite lors de la connexion à Google : {e}")

# ==========================================
# MESSAGES D'ERREUR (Si mauvais mot de passe)
# ==========================================
elif st.session_state["authentication_status"] is False:
    st.error("❌ Identifiant ou mot de passe incorrect.")
elif st.session_state["authentication_status"] is None:
    st.info("👋 Bienvenue ! Veuillez vous connecter avec votre identifiant pour accéder à votre espace.")