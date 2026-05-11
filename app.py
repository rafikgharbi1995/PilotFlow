import streamlit as st
import pandas as pd
import plotly.express as px

# ==========================================
# 1. CONFIGURATION DE LA PAGE
# ==========================================
st.set_page_config(page_title="DataSaaS 📈", page_icon="📈", layout="wide")

# Initialisation de la mémoire de l'application (Session State)
if 'logged_in' not in st.session_state:
    st.session_state.logged_in = False
if 'data_prete' not in st.session_state:
    st.session_state.data_prete = False
if 'df_final' not in st.session_state:
    st.session_state.df_final = None
if 'nom_entreprise' not in st.session_state:
    st.session_state.nom_entreprise = ""
if 'magasin_present' not in st.session_state:
    st.session_state.magasin_present = False

# ==========================================
# 2. PAGE DE CONNEXION / INSCRIPTION
# ==========================================
if not st.session_state.logged_in:
    st.title("Bienvenue sur PilotFlow 🚀")
    st.markdown("La solution d'analyse de données intelligente pour votre entreprise.")

    col1, col2 = st.columns([1, 1])
    with col1:
        st.subheader("Connexion à l'espace client")
        with st.form("login_form"):
            entreprise = st.text_input("Nom de l'entreprise")
            email = st.text_input("Email professionnel")
            password = st.text_input("Mot de passe", type="password")
            submit_button = st.form_submit_button("Se connecter / Créer un compte")

            if submit_button and entreprise and email:
                st.session_state.logged_in = True
                st.session_state.nom_entreprise = entreprise
                st.success("Connexion réussie !")
                st.rerun()

# ==========================================
# 3. ESPACE CLIENT (SaaS B2B)
# ==========================================
else:
    # --- BARRE DE NAVIGATION (SIDEBAR) ---
    st.sidebar.title(f"🏢 {st.session_state.nom_entreprise}")
    menu = st.sidebar.radio(
        "Menu Principal",
        [
            "🔌 Étape 1 : Import & Configuration",
            "📊 Étape 2 : Mon Dashboard",
            "🚪 Déconnexion"
        ]
    )

    # ---------------------------------------------------------
    # PAGE : IMPORT ET CONFIGURATION (MAPPING)
    # ---------------------------------------------------------
    if menu == "🔌 Étape 1 : Import & Configuration":
        st.title("🔌 Importez et configurez vos données")
        st.info(
            "Uploadez votre fichier brut (Excel ou CSV) exporté depuis votre base de données locale ou votre logiciel de caisse."
        )

        uploaded_file = st.file_uploader("Glissez votre fichier ici", type=['csv', 'xlsx', 'xls'])

        if uploaded_file is not None:
            try:
                if uploaded_file.name.endswith('.csv'):
                    df_brut = pd.read_csv(uploaded_file, sep=None, engine='python')
                elif uploaded_file.name.endswith('.xlsx'):
                    df_brut = pd.read_excel(uploaded_file, engine='openpyxl')
                elif uploaded_file.name.endswith('.xls'):
                    df_brut = pd.read_excel(uploaded_file, engine='xlrd')
                else:
                    st.error("Format non supporté. Veuillez uploader un .csv, .xlsx ou .xls")
                    st.stop()

                st.success(f"Fichier '{uploaded_file.name}' lu avec succès !")
                colonnes = df_brut.columns.tolist()

                with st.expander("Voir un aperçu de mes données brutes"):
                    st.dataframe(df_brut.head(5), use_container_width=True)

                st.divider()

                # --- MAPPING DES COLONNES ---
                st.subheader("⚙️ Aidez-nous à comprendre vos données")
                col1, col2 = st.columns(2)
                with col1:
                    col_date = st.selectbox("📅 Colonne des Dates", colonnes)
                with col2:
                    col_produit = st.selectbox("📦 Colonne des Produits/Catégories", colonnes)

                # --- DÉFINITION DES REVENUS : colonne existante OU calcul Prix×Quantité ---
                st.subheader("💰 Définition des Revenus")
                revenue_type = st.radio(
                    "Méthode de calcul des revenus",
                    ("Colonne existante (montant déjà calculé)", "Calcul automatique : Prix × Quantité"),
                    index=0,
                    help="Choisissez 'Calcul automatique' si vous avez une colonne Prix et une colonne Quantité (les retours en quantité négative réduiront le CA)."
                )

                if revenue_type.startswith("Colonne"):
                    col_revenu = st.selectbox("💲 Colonne des Revenus (Montant)", colonnes)
                else:
                    col_p1, col_p2 = st.columns(2)
                    with col_p1:
                        col_prix = st.selectbox("💵 Colonne du Prix Unitaire", colonnes)
                    with col_p2:
                        col_qte = st.selectbox("🔢 Colonne de la Quantité", colonnes)

                # Magasin (optionnel)
                col_magasin = st.selectbox(
                    "🏬 Colonne du Magasin / Point de vente",
                    options=["Aucune"] + colonnes,
                    help="Laissez 'Aucune' si votre fichier ne contient pas cette information."
                )

                # Bouton de validation
                if st.button("Valider et Générer le Dashboard 🚀", type="primary"):
                    df_propre = df_brut.copy()

                    # Nettoyage et standardisation
                    df_propre['Date_Std'] = pd.to_datetime(df_propre[col_date], errors='coerce')
                    df_propre['Produit_Std'] = df_propre[col_produit].astype(str)

                    # Calcul du revenu selon la méthode choisie
                    if revenue_type.startswith("Colonne"):
                        df_propre['Revenu_Std'] = pd.to_numeric(df_propre[col_revenu], errors='coerce').fillna(0)
                    else:
                        prix = pd.to_numeric(df_propre[col_prix], errors='coerce').fillna(0)
                        qte = pd.to_numeric(df_propre[col_qte], errors='coerce').fillna(0)
                        df_propre['Revenu_Std'] = prix * qte

                    # Magasin
                    if col_magasin != "Aucune":
                        df_propre['Magasin_Std'] = df_propre[col_magasin].astype(str)
                        st.session_state.magasin_present = True
                    else:
                        st.session_state.magasin_present = False

                    # Supprimer les dates invalides
                    df_propre = df_propre.dropna(subset=['Date_Std'])

                    # Garder uniquement les colonnes standardisées (optionnel mais plus propre)
                    colonnes_std = ['Date_Std', 'Produit_Std', 'Revenu_Std']
                    if st.session_state.magasin_present:
                        colonnes_std.append('Magasin_Std')
                    df_propre = df_propre[colonnes_std]

                    # Sauvegarde
                    st.session_state.df_final = df_propre
                    st.session_state.data_prete = True

                    st.success("Configuration terminée ! Allez dans l'onglet '📊 Étape 2 : Mon Dashboard'.")
                    st.balloons()

            except Exception as e:
                st.error(f"Une erreur est survenue lors de la lecture du fichier : {e}")
                st.stop()

    # ---------------------------------------------------------
    # PAGE : DASHBOARD AUTOMATIQUE (avec filtre magasin)
    # ---------------------------------------------------------
    elif menu == "📊 Étape 2 : Mon Dashboard":
        st.title("📊 Tableau de Bord Analytique")

        if not st.session_state.data_prete or st.session_state.df_final is None:
            st.warning("⚠️ Aucune donnée détectée. Veuillez retourner à l'Étape 1.")
        else:
            df = st.session_state.df_final
            mag_dispo = st.session_state.magasin_present

            # Filtre magasin
            if mag_dispo:
                magasins_valides = df['Magasin_Std'].dropna().unique()
                if len(magasins_valides) == 0:
                    st.sidebar.warning("Aucun magasin trouvé.")
                    mag_dispo = False
                else:
                    liste_magasins = sorted(magasins_valides.tolist())
                    magasin_choisi = st.sidebar.selectbox(
                        "🏬 Choisir un magasin",
                        options=["Tous"] + liste_magasins
                    )
            else:
                magasin_choisi = "Tous"

            # Application du filtre
            if mag_dispo and magasin_choisi != "Tous":
                df_filtre = df[df['Magasin_Std'] == magasin_choisi]
            else:
                df_filtre = df

            # KPIs
            revenu_total = df_filtre['Revenu_Std'].sum()
            nb_ventes = len(df_filtre)
            if not df_filtre.empty:
                try:
                    produit_top = df_filtre.groupby('Produit_Std')['Revenu_Std'].sum().idxmax()
                except ValueError:
                    produit_top = "N/A"
            else:
                produit_top = "N/A"

            col1, col2, col3 = st.columns(3)
            col1.metric("Revenus Totals", f"{revenu_total:,.2f} TND")
            col2.metric("Nombre de Lignes", f"{nb_ventes}")
            col3.metric("Meilleur Produit", f"{produit_top}")

            if mag_dispo and magasin_choisi != "Tous":
                st.caption(f"🔍 Vue filtrée sur le magasin : **{magasin_choisi}**")

            st.divider()

            if df_filtre.empty:
                st.info("Aucune donnée pour cette sélection.")
            else:
                col_graph1, col_graph2 = st.columns(2)

                with col_graph1:
                    st.subheader("Répartition par Produit")
                    df_produit = df_filtre.groupby('Produit_Std', as_index=False)['Revenu_Std'].sum()
                    fig_pie = px.pie(df_produit, values='Revenu_Std', names='Produit_Std', hole=0.4)
                    st.plotly_chart(fig_pie, use_container_width=True)

                with col_graph2:
                    if mag_dispo:
                        st.subheader("Comparaison par Magasin")
                        df_mag = df.groupby('Magasin_Std', as_index=False)['Revenu_Std'].sum()
                        df_mag = df_mag.sort_values(by='Revenu_Std', ascending=False)
                        fig_bar_mag = px.bar(
                            df_mag, x='Magasin_Std', y='Revenu_Std',
                            text_auto=True, color='Revenu_Std',
                            color_continuous_scale='blues'
                        )
                        st.plotly_chart(fig_bar_mag, use_container_width=True)
                    else:
                        st.subheader("Top 5 des Produits")
                        df_top5 = df_produit.sort_values(by='Revenu_Std', ascending=False).head(5)
                        fig_bar = px.bar(
                            df_top5, x='Produit_Std', y='Revenu_Std',
                            text_auto=True, color='Revenu_Std',
                            color_continuous_scale='greens'
                        )
                        st.plotly_chart(fig_bar, use_container_width=True)

                st.subheader("Évolution dans le temps")
                df_temps = df_filtre.groupby(df_filtre['Date_Std'].dt.date, as_index=False)['Revenu_Std'].sum()
                df_temps = df_temps.sort_values('Date_Std')
                fig_line = px.line(df_temps, x='Date_Std', y='Revenu_Std', markers=True)
                st.plotly_chart(fig_line, use_container_width=True)

    # ---------------------------------------------------------
    # PAGE : DECONNEXION
    # ---------------------------------------------------------
    elif menu == "🚪 Déconnexion":
        for key in list(st.session_state.keys()):
            del st.session_state[key]
        st.rerun()