import streamlit as st
import pandas as pd
import plotly.express as px
from datetime import datetime
import csv
from io import BytesIO

# ==========================================
# NOM DE L'APPLICATION – modifiable ici
# ==========================================
APP_NAME = "PilotFlow"

# ==========================================
# 1. CONFIGURATION DE LA PAGE
# ==========================================
st.set_page_config(page_title=f"{APP_NAME} 📈", page_icon="📈", layout="wide")

# Initialisation de la session (ventes + stock)
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

# Variables pour le module Stock
if 'stock_initial' not in st.session_state:
    st.session_state.stock_initial = None
if 'mouvements' not in st.session_state:
    st.session_state.mouvements = pd.DataFrame(columns=['Date', 'Produit', 'Type', 'Quantité'])
if 'stock_seuils' not in st.session_state:
    st.session_state.stock_seuils = {}

# ==========================================
# FONCTION ROBUSTE DE LECTURE CSV
# ==========================================
def read_csv_robust(uploaded_file):
    """Lit un fichier CSV avec détection automatique du délimiteur et de l'encodage."""
    content = uploaded_file.read()
    # Sauvegarde pour réutiliser en BytesIO après
    buffer = BytesIO(content)

    # 1. Essayer de détecter le délimiteur à partir du contenu
    try:
        # On prend les premiers octets pour sniffer
        sample = content[:2048].decode('utf-8', errors='ignore')
        sniffer = csv.Sniffer()
        delimiter = sniffer.sniff(sample).delimiter
    except:
        delimiter = None

    # 2. Liste des séparateurs à tester (détecté en priorité, puis virgule, point-virgule, tab)
    if delimiter:
        seps_to_try = [delimiter, ',', ';', '\t']
    else:
        seps_to_try = [',', ';', '\t']

    # 3. Liste des encodages à essayer
    encodings_to_try = ['utf-8', 'latin-1']

    for encoding in encodings_to_try:
        for sep in seps_to_try:
            try:
                buffer.seek(0)
                return pd.read_csv(buffer, sep=sep, encoding=encoding)
            except:
                continue

    # Si rien ne fonctionne
    raise ValueError("Impossible de lire le fichier CSV. Vérifiez le séparateur et l'encodage.")

# ==========================================
# 2. PAGE DE CONNEXION / INSCRIPTION
# ==========================================
if not st.session_state.logged_in:
    st.title(f"Bienvenue sur {APP_NAME} 🚀")
    st.markdown("Votre solution de pilotage commercial évolutive (ventes, stocks, etc.).")

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
# 3. ESPACE CLIENT
# ==========================================
else:
    # --- SIDEBAR ---
    st.sidebar.title(f"🏢 {st.session_state.nom_entreprise}")
    menu = st.sidebar.radio(
        "Menu Principal",
        [
            "🔌 Étape 1 : Import & Configuration",
            "📊 Étape 2 : Mon Dashboard",
            "📦 Gestion de Stock",
            "🚪 Déconnexion"
        ]
    )

    # ============================================================
    # PAGE 1 : IMPORT & CONFIGURATION (ventes)
    # ============================================================
    if menu == "🔌 Étape 1 : Import & Configuration":
        st.title("🔌 Importez et configurez vos données")
        st.info(
            "Uploadez votre fichier brut (Excel ou CSV). Les retours (quantités négatives) seront automatiquement soustraits si vous choisissez le calcul Prix × Quantité."
        )

        uploaded_file = st.file_uploader("Glissez votre fichier ici", type=['csv', 'xlsx', 'xls'])

        if uploaded_file is not None:
            try:
                # --- LECTURE DU FICHIER ---
                if uploaded_file.name.endswith('.csv'):
                    df_brut = read_csv_robust(uploaded_file)
                elif uploaded_file.name.endswith('.xlsx'):
                    df_brut = pd.read_excel(uploaded_file, engine='openpyxl')
                elif uploaded_file.name.endswith('.xls'):
                    df_brut = pd.read_excel(uploaded_file, engine='xlrd')
                else:
                    st.error("Format non supporté. Veuillez uploader un .csv, .xlsx ou .xls")
                    st.stop()

                st.success(f"Fichier '{uploaded_file.name}' lu avec succès !")
                colonnes = df_brut.columns.tolist()

                with st.expander("Aperçu des données brutes"):
                    st.dataframe(df_brut.head(5), use_container_width=True)

                st.divider()

                # --- MAPPING ---
                st.subheader("⚙️ Aidez-nous à comprendre vos données")
                col1, col2 = st.columns(2)
                with col1:
                    col_date = st.selectbox("📅 Colonne des Dates", colonnes)
                with col2:
                    col_produit = st.selectbox("📦 Colonne des Produits / Catégories", colonnes)

                st.subheader("💰 Définition des Revenus")
                revenue_type = st.radio(
                    "Méthode de calcul",
                    ("Colonne existante (montant déjà calculé)", "Calcul automatique : Prix × Quantité"),
                    index=0,
                    help="Si vous avez une colonne Quantité (avec des valeurs négatives pour les retours), choisissez 'Calcul automatique'."
                )

                if revenue_type.startswith("Colonne"):
                    col_revenu = st.selectbox("💲 Colonne des Revenus (Montant)", colonnes)
                else:
                    c1, c2 = st.columns(2)
                    with c1:
                        col_prix = st.selectbox("💵 Colonne du Prix Unitaire", colonnes)
                    with c2:
                        col_qte = st.selectbox("🔢 Colonne de la Quantité", colonnes)

                col_magasin = st.selectbox(
                    "🏬 Colonne du Magasin / Point de vente (optionnel)",
                    options=["Aucune"] + colonnes
                )

                if st.button("Valider et Générer le Dashboard 🚀", type="primary"):
                    df_propre = df_brut.copy()

                    df_propre['Date_Std'] = pd.to_datetime(df_propre[col_date], errors='coerce')
                    df_propre['Produit_Std'] = df_propre[col_produit].astype(str)

                    if revenue_type.startswith("Colonne"):
                        df_propre['Revenu_Std'] = pd.to_numeric(df_propre[col_revenu], errors='coerce').fillna(0)
                    else:
                        prix = pd.to_numeric(df_propre[col_prix], errors='coerce').fillna(0)
                        qte = pd.to_numeric(df_propre[col_qte], errors='coerce').fillna(0)
                        df_propre['Revenu_Std'] = prix * qte

                    if col_magasin != "Aucune":
                        df_propre['Magasin_Std'] = df_propre[col_magasin].astype(str)
                        st.session_state.magasin_present = True
                    else:
                        st.session_state.magasin_present = False

                    df_propre = df_propre.dropna(subset=['Date_Std'])
                    colonnes_gardees = ['Date_Std', 'Produit_Std', 'Revenu_Std']
                    if st.session_state.magasin_present:
                        colonnes_gardees.append('Magasin_Std')
                    df_propre = df_propre[colonnes_gardees]

                    st.session_state.df_final = df_propre
                    st.session_state.data_prete = True
                    st.success("Configuration terminée ! Rendez-vous dans '📊 Mon Dashboard'.")
                    st.balloons()

            except Exception as e:
                st.error(f"Erreur lors de la lecture : {e}")
                st.stop()

    # ============================================================
    # PAGE 2 : DASHBOARD DES VENTES
    # ============================================================
    elif menu == "📊 Étape 2 : Mon Dashboard":
        st.title("📊 Tableau de Bord Analytique")

        if not st.session_state.data_prete or st.session_state.df_final is None:
            st.warning("⚠️ Aucune donnée configurée. Retournez à l'Étape 1.")
        else:
            df = st.session_state.df_final
            mag_dispo = st.session_state.magasin_present

            if mag_dispo:
                magasins = sorted(df['Magasin_Std'].dropna().unique())
                if magasins:
                    magasin_choisi = st.sidebar.selectbox("🏬 Magasin", ["Tous"] + magasins)
                else:
                    st.sidebar.warning("Aucun magasin valide trouvé.")
                    magasin_choisi = "Tous"
            else:
                magasin_choisi = "Tous"

            if mag_dispo and magasin_choisi != "Tous":
                df_filtre = df[df['Magasin_Std'] == magasin_choisi]
            else:
                df_filtre = df

            revenu_total = df_filtre['Revenu_Std'].sum()
            nb_lignes = len(df_filtre)
            if not df_filtre.empty:
                try:
                    produit_top = df_filtre.groupby('Produit_Std')['Revenu_Std'].sum().idxmax()
                except ValueError:
                    produit_top = "N/A"
            else:
                produit_top = "N/A"

            col1, col2, col3 = st.columns(3)
            col1.metric("Revenus Totals", f"{revenu_total:,.2f} TND")
            col2.metric("Nb de lignes", f"{nb_lignes}")
            col3.metric("Meilleur produit", produit_top)

            if magasin_choisi != "Tous":
                st.caption(f"🔍 Vue filtrée sur le magasin : **{magasin_choisi}**")
            st.divider()

            if df_filtre.empty:
                st.info("Aucune donnée pour cette sélection.")
            else:
                col_g1, col_g2 = st.columns(2)

                with col_g1:
                    st.subheader("Répartition par Produit")
                    df_prod = df_filtre.groupby('Produit_Std', as_index=False)['Revenu_Std'].sum()
                    fig1 = px.pie(df_prod, values='Revenu_Std', names='Produit_Std', hole=0.4)
                    st.plotly_chart(fig1, use_container_width=True)

                with col_g2:
                    if mag_dispo:
                        st.subheader("Comparaison par Magasin")
                        df_mag = df.groupby('Magasin_Std')['Revenu_Std'].sum().reset_index()
                        df_mag = df_mag.sort_values('Revenu_Std', ascending=False)
                        fig2 = px.bar(df_mag, x='Magasin_Std', y='Revenu_Std', text_auto=True,
                                      color='Revenu_Std', color_continuous_scale='blues')
                    else:
                        st.subheader("Top 5 Produits")
                        top5 = df_prod.sort_values('Revenu_Std', ascending=False).head(5)
                        fig2 = px.bar(top5, x='Produit_Std', y='Revenu_Std', text_auto=True,
                                      color='Revenu_Std', color_continuous_scale='greens')
                    st.plotly_chart(fig2, use_container_width=True)

                st.subheader("Évolution dans le temps")
                df_temps = df_filtre.groupby(df_filtre['Date_Std'].dt.date)['Revenu_Std'].sum().reset_index()
                df_temps = df_temps.sort_values('Date_Std')
                fig3 = px.line(df_temps, x='Date_Std', y='Revenu_Std', markers=True)
                st.plotly_chart(fig3, use_container_width=True)

    # ============================================================
    # PAGE 3 : GESTION DE STOCK
    # ============================================================
    elif menu == "📦 Gestion de Stock":
        st.title("📦 Gestion de Stock")
        st.markdown("Suivez vos stocks en temps réel, gérez les entrées/sorties et définissez des seuils d'alerte.")

        tab1, tab2, tab3 = st.tabs(["📋 Stock Actuel", "➕ Nouveau mouvement", "⚙️ Initialisation & Paramètres"])

        def calculer_stock_actuel():
            if st.session_state.stock_initial is None:
                return pd.DataFrame(columns=['Produit', 'Quantité Initiale', 'Total Entrées', 'Total Sorties', 'Stock Final'])
            initial = st.session_state.stock_initial.copy()
            mouvs = st.session_state.mouvements.copy()

            if not mouvs.empty:
                entrees = mouvs[mouvs['Type'] == 'Entrée'].groupby('Produit')['Quantité'].sum().reset_index()
                entrees.columns = ['Produit', 'Total Entrées']
                sorties = mouvs[mouvs['Type'] == 'Sortie'].groupby('Produit')['Quantité'].sum().reset_index()
                sorties.columns = ['Produit', 'Total Sorties']

                stock = initial.merge(entrees, on='Produit', how='left').merge(sorties, on='Produit', how='left')
                stock['Total Entrées'] = stock['Total Entrées'].fillna(0)
                stock['Total Sorties'] = stock['Total Sorties'].fillna(0)
            else:
                stock = initial.copy()
                stock['Total Entrées'] = 0
                stock['Total Sorties'] = 0

            stock['Stock Final'] = stock['Quantité Initiale'] + stock['Total Entrées'] - stock['Total Sorties']
            return stock

        def verifier_seuils(stock_df):
            alertes = []
            for _, row in stock_df.iterrows():
                produit = row['Produit']
                if produit in st.session_state.stock_seuils and row['Stock Final'] <= st.session_state.stock_seuils[produit]:
                    alertes.append(produit)
            return alertes

        # --- Onglet 1 : Stock Actuel ---
        with tab1:
            stock_actuel = calculer_stock_actuel()
            if stock_actuel.empty:
                st.info("Aucun stock initialisé. Allez dans l'onglet 'Initialisation' pour importer un fichier.")
            else:
                alertes = verifier_seuils(stock_actuel)
                if alertes:
                    st.error(f"⚠️ Stock critique pour : {', '.join(alertes)}")

                recherche = st.text_input("🔍 Rechercher un produit")
                if recherche:
                    stock_affiche = stock_actuel[stock_actuel['Produit'].str.contains(recherche, case=False)]
                else:
                    stock_affiche = stock_actuel

                st.dataframe(
                    stock_affiche.style.applymap(
                        lambda val: 'background-color: #ffcccc' if (isinstance(val, (int, float)) and val < 0) else '',
                        subset=['Stock Final']
                    ),
                    use_container_width=True
                )

                fig_stock = px.bar(stock_actuel, x='Produit', y='Stock Final',
                                   title="Niveau de stock par produit",
                                   color='Stock Final',
                                   color_continuous_scale='RdYlGn')
                st.plotly_chart(fig_stock, use_container_width=True)

        # --- Onglet 2 : Nouveau mouvement ---
        with tab2:
            if st.session_state.stock_initial is None:
                st.warning("Initialisez d'abord le stock dans l'onglet 'Initialisation'.")
            else:
                st.subheader("Enregistrer un mouvement de stock")
                with st.form("form_mouvement"):
                    col1, col2 = st.columns(2)
                    with col1:
                        date_mvt = st.date_input("Date", value=datetime.now())
                    with col2:
                        type_mvt = st.selectbox("Type", ["Entrée", "Sortie"])

                    liste_produits = st.session_state.stock_initial['Produit'].tolist()
                    produit_mvt = st.selectbox("Produit", liste_produits)
                    qte_mvt = st.number_input("Quantité", min_value=1, step=1)

                    if st.form_submit_button("✅ Valider le mouvement"):
                        nouveau_mvt = pd.DataFrame({
                            'Date': [date_mvt],
                            'Produit': [produit_mvt],
                            'Type': [type_mvt],
                            'Quantité': [qte_mvt]
                        })
                        st.session_state.mouvements = pd.concat(
                            [st.session_state.mouvements, nouveau_mvt],
                            ignore_index=True
                        )
                        st.success("Mouvement enregistré !")
                        st.rerun()

                st.divider()
                st.subheader("Historique des mouvements")
                if not st.session_state.mouvements.empty:
                    mouvs_affiche = st.session_state.mouvements.sort_values('Date', ascending=False)
                    st.dataframe(mouvs_affiche, use_container_width=True)
                else:
                    st.info("Aucun mouvement pour le moment.")

        # --- Onglet 3 : Initialisation et paramètres ---
        with tab3:
            st.subheader("📂 Initialiser le stock depuis un fichier")
            stock_file = st.file_uploader(
                "Importer un fichier (CSV ou Excel) avec les colonnes : Produit, Quantité Initiale",
                type=['csv', 'xlsx', 'xls'],
                key="stock_uploader"
            )
            if stock_file is not None:
                try:
                    if stock_file.name.endswith('.csv'):
                        df_stock = read_csv_robust(stock_file)
                    elif stock_file.name.endswith('.xlsx'):
                        df_stock = pd.read_excel(stock_file, engine='openpyxl')
                    else:
                        df_stock = pd.read_excel(stock_file, engine='xlrd')

                    if 'Produit' not in df_stock.columns or 'Quantité Initiale' not in df_stock.columns:
                        st.error("Le fichier doit contenir les colonnes 'Produit' et 'Quantité Initiale'.")
                    else:
                        df_stock = df_stock[['Produit', 'Quantité Initiale']].dropna()
                        st.session_state.stock_initial = df_stock
                        st.session_state.mouvements = pd.DataFrame(columns=['Date', 'Produit', 'Type', 'Quantité'])
                        st.session_state.stock_seuils = {}
                        st.success(f"{len(df_stock)} produits chargés !")
                        st.rerun()
                except Exception as e:
                    st.error(f"Erreur de lecture : {e}")

            st.divider()
            st.subheader("Ou créer manuellement un stock initial")
            with st.form("form_manuel_stock"):
                produit_nom = st.text_input("Nom du produit")
                qte_init = st.number_input("Quantité initiale", min_value=0, step=1)
                if st.form_submit_button("➕ Ajouter ce produit"):
                    if produit_nom:
                        nouvelle_ligne = pd.DataFrame({'Produit': [produit_nom], 'Quantité Initiale': [qte_init]})
                        if st.session_state.stock_initial is None:
                            st.session_state.stock_initial = nouvelle_ligne
                        else:
                            st.session_state.stock_initial = pd.concat(
                                [st.session_state.stock_initial, nouvelle_ligne],
                                ignore_index=True
                            )
                        st.success(f"Produit '{produit_nom}' ajouté.")
                        st.rerun()
                    else:
                        st.error("Veuillez entrer un nom de produit.")

            if st.session_state.stock_initial is not None:
                st.divider()
                st.subheader("🎯 Gestion des seuils d'alerte")
                for idx, row in st.session_state.stock_initial.iterrows():
                    produit = row['Produit']
                    seuil_actuel = st.session_state.stock_seuils.get(produit, 0)
                    nouveau_seuil = st.number_input(
                        f"Seuil minimum pour {produit}",
                        min_value=0,
                        value=seuil_actuel,
                        step=1,
                        key=f"seuil_{produit}"
                    )
                    if nouveau_seuil != seuil_actuel:
                        st.session_state.stock_seuils[produit] = nouveau_seuil

                if st.button("💾 Enregistrer les seuils"):
                    st.success("Seuils mis à jour !")
                    st.rerun()

    # ============================================================
    # PAGE 4 : DECONNEXION
    # ============================================================
    elif menu == "🚪 Déconnexion":
        for key in list(st.session_state.keys()):
            del st.session_state[key]
        st.rerun()
