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

# Notre petite base de données d'utilisateurs (les mots de passe seront cachés automatiquement)
credentials = {
    "usernames": {
        "admin": {
            "email": "admin@budget.com",
            "name": "Administrateur",
            "password": "123456" # Mot de passe en clair
        },
        "alice": {
            "email": "alice@budget.com",
            "name": "Alice",
            "password": "budget2026" # Mot de passe en clair
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

    cle_periode = f"{mois_selectionne}_{annee_selectionnee}_{id_utilisateur}"

    # ==========================================
    # 2.5 CHARGEMENT DES DONNÉES (Historique)
    # ==========================================
    if st.button("📥 Charger mes données pour ce mois"):
        try:
            creds_dict = json.loads(st.secrets["google_secret"])
            client = gspread.service_account_from_dict(creds_dict)
            sheet = client.open_by_url("https://docs.google.com/spreadsheets/d/12Sx9pwAmphhQGIxMtFrBJZrPEhZFntEUnknTPKi2oyo/edit?hl=fr&pli=1&gid=1461270140#gid=1461270140")
            
            # --- Chargement des Revenus ---
            ws_revenus = sheet.worksheet("Revenus")
            tous_revenus = ws_revenus.get_all_records()
            mes_revenus = [r for r in tous_revenus if str(r.get("Mois")) == str(mois_selectionne) and str(r.get("Année")) == str(annee_selectionnee) and str(r.get("Utilisateur")) == str(id_utilisateur)]
            
            if mes_revenus:
                df_mes_revenus = pd.DataFrame(mes_revenus)[["Source de revenu", "Montant (€)"]]
                st.session_state[f"revenus_{cle_periode}"] = df_mes_revenus
                
            # --- Chargement des Dépenses ---
            ws_depenses = sheet.worksheet("Depenses")
            toutes_depenses = ws_depenses.get_all_records()
            mes_depenses = [r for r in toutes_depenses if str(r.get("Mois")) == str(mois_selectionne) and str(r.get("Année")) == str(annee_selectionnee) and str(r.get("Utilisateur")) == str(id_utilisateur)]
            
            if mes_depenses:
                df_mes_depenses = pd.DataFrame(mes_depenses)
                # On répartit les dépenses dans les bonnes catégories
                for categorie in ["Logement", "Alimentation", "Transports", "Assurances", "Loisirs", "Autre"]:
                    depenses_cat = df_mes_depenses[df_mes_depenses["Grande Famille"] == categorie][["Sous-catégorie", "Montant (€)"]]
                    if not depenses_cat.empty:
                        st.session_state[f"depenses_{categorie}_{cle_periode}"] = depenses_cat

            st.success("✅ Données chargées avec succès !")
            st.rerun() # Rafraîchit la page pour afficher les tableaux remplis
            
        except Exception as e:
            st.error(f"❌ Erreur lors du chargement : {e}")

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
        st.subheader("📊 Répartition de mes dépenses")
        if total_depenses > 0:
            # 1. Couleurs modernes (Pastel)
            fig = px.sunburst(
                df_toutes_depenses, 
                path=['Grande Famille', 'Sous-catégorie'], 
                values='Montant (€)', 
                color='Grande Famille',
                color_discrete_sequence=px.colors.qualitative.Pastel 
            )
            
            # 2. Design des parts et de la bulle d'info (Hover) au passage de la souris
            fig.update_traces(
                textinfo="label+percent parent",
                insidetextorientation='radial',
                hovertemplate="<b>%{label}</b><br>💸 Montant : %{value} €<br>📊 Part : %{percentParent:.1%}<extra></extra>",
                marker=dict(line=dict(color='white', width=1.5)) # Bordures blanches design
            )
            
            # 3. Fond transparent et marges réduites
            fig.update_layout(
                margin=dict(t=20, l=10, r=10, b=10),
                paper_bgcolor="rgba(0,0,0,0)",
                plot_bgcolor="rgba(0,0,0,0)"
            )
            
            st.plotly_chart(fig, use_container_width=True)
        else:
            st.info("Ajoutez des dépenses pour voir le graphique.")

    with col_bilan:
        reste_a_vivre = total_revenus - total_depenses
        st.subheader("📈 Bilan du mois")
        
        # On met les métriques dans de jolies colonnes pour un effet "Dashboard"
        col_m1, col_m2 = st.columns(2)
        with col_m1:
            st.metric(label="Total Revenus", value=f"{total_revenus:.2f} €")
        with col_m2:
            st.metric(label="Total Dépenses", value=f"{total_depenses:.2f} €")
            
        st.metric(
            label="Reste à vivre", 
            value=f"{reste_a_vivre:.2f} €", 
            delta=f"{reste_a_vivre:.2f} €", 
            delta_color="normal" if reste_a_vivre >= 0 else "inverse"
        )

    # ==========================================
    # 3. SAUVEGARDE DANS GOOGLE SHEETS (Anti-Doublons)
    # ==========================================
    st.write("---")
    st.header("💾 Enregistrer mes données")
    
    if st.button("🚀 Sauvegarder ce mois dans ma base de données"):
        try:
            creds_dict = json.loads(st.secrets["google_secret"])
            client = gspread.service_account_from_dict(creds_dict)
            
            # /!\ N'OUBLIE PAS DE METTRE TON VRAI LIEN GOOGLE SHEETS ICI /!\
            sheet = client.open_by_url("https://docs.google.com/spreadsheets/d/12Sx9pwAmphhQGIxMtFrBJZrPEhZFntEUnknTPKi2oyo/edit?hl=fr&pli=1&gid=0#gid=0")
            
            # --- NOTRE NOUVELLE FONCTION DE MÉNAGE ---
            def nettoyer_doublons(worksheet):
                records = worksheet.get_all_records()
                lignes_a_supprimer = []
                
                # On cherche les lignes qui correspondent au mois, année ET utilisateur
                for i, row in enumerate(records):
                    if str(row.get("Mois")) == str(mois_selectionne) and \
                       str(row.get("Année")) == str(annee_selectionnee) and \
                       str(row.get("Utilisateur")) == str(id_utilisateur):
                        lignes_a_supprimer.append(i + 2) # +2 car Python compte à partir de 0 et il y a l'en-tête
                
                # On efface de bas en haut pour éviter de décaler les lignes
                for index_ligne in reversed(lignes_a_supprimer):
                    worksheet.delete_rows(index_ligne)

            # --- Envoi des Revenus ---
            if not df_rev_clean.empty:
                ws_revenus = sheet.worksheet("Revenus")
                nettoyer_doublons(ws_revenus) # 🧹 On efface les anciens
                
                df_rev_save = df_rev_clean.copy()
                df_rev_save["Mois"] = mois_selectionne
                df_rev_save["Année"] = annee_selectionnee
                df_rev_save["Utilisateur"] = id_utilisateur
                
                lignes_revenus = df_rev_save[["Mois", "Année", "Source de revenu", "Montant (€)", "Utilisateur"]].astype(str).values.tolist()
                ws_revenus.append_rows(lignes_revenus, value_input_option="USER_ENTERED") # 📝 On écrit les nouveaux
                
            # --- Envoi des Dépenses ---
            if not df_toutes_depenses.empty:
                ws_depenses = sheet.worksheet("Depenses")
                nettoyer_doublons(ws_depenses) # 🧹 On efface les anciens
                
                df_dep_save = df_toutes_depenses.copy()
                df_dep_save["Mois"] = mois_selectionne
                df_dep_save["Année"] = annee_selectionnee
                df_dep_save["Utilisateur"] = id_utilisateur
                
                lignes_depenses = df_dep_save[["Mois", "Année", "Grande Famille", "Sous-catégorie", "Montant (€)", "Utilisateur"]].astype(str).values.tolist()
                ws_depenses.append_rows(lignes_depenses, value_input_option="USER_ENTERED") # 📝 On écrit les nouveaux
                
            st.success(f"✅ Mise à jour réussie {nom_utilisateur} ! Votre budget a été enregistré sans doublon.")
            
        except Exception as e:
            st.error(f"❌ Une erreur s'est produite lors de la connexion à Google : {e}")

# ==========================================
# MESSAGES D'ERREUR (Si mauvais mot de passe)
# ==========================================
elif st.session_state["authentication_status"] is False:
    st.error("❌ Identifiant ou mot de passe incorrect.")
elif st.session_state["authentication_status"] is None:
    st.info("👋 Bienvenue ! Veuillez vous connecter avec votre identifiant pour accéder à votre espace.")