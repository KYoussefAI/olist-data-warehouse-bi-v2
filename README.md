# Olist E-commerce BI Pipeline

Projet BI / Data Engineering basé sur les données Olist. L'objectif est de transformer des fichiers CSV bruts en un Data Warehouse analytique SQLite, puis de présenter les indicateurs dans un rapport Streamlit multi-page.

## Objectif du projet

Le projet suit une chaîne décisionnelle simple et adaptée à un contexte universitaire :

```text
Sources CSV Olist
↓
ETL Python
↓
Data Warehouse SQLite
↓
Rapport BI Streamlit
```

## Problématique

Comment Olist peut-elle exploiter ses données de commandes, paiements, avis clients, produits, vendeurs et leads marketing pour suivre la performance commerciale, la qualité de livraison, la satisfaction client et l'efficacité de l'acquisition de vendeurs ?

## Sources attendues dans `data/raw/`

Fichiers principaux :

```text
olist_orders_dataset.csv
olist_order_items_dataset.csv
olist_order_payments_dataset.csv
olist_order_reviews_dataset.csv
olist_customers_dataset.csv
olist_products_dataset.csv
olist_sellers_dataset.csv
olist_marketing_qualified_leads_dataset.csv
olist_closed_deals_dataset.csv
```

Fichier optionnel :

```text
product_category_name_translation.csv
```

Si le fichier de traduction des catégories est absent, l'ETL continue et utilise les noms de catégories originaux comme libellés d'analyse. Le rapport qualité indique alors `0` ligne pour cette source et ajoute une note `missing_optional_using_original_category_names`.

Le fichier `olist_geolocation_dataset.csv` n'est pas utilisé dans cette première version afin de garder le modèle simple. Les villes et États présents dans les dimensions client et vendeur suffisent pour les analyses demandées.

## Installation

```bash
python -m venv .venv
source .venv/bin/activate  # Windows: .venv\Scripts\activate
pip install -r requirements.txt
```

## Lancer l'ETL

```bash
python -m src.run_etl --raw-data-dir data/raw --warehouse-path data/warehouse/olist_dwh.sqlite
```

Le script crée ou remplace :

```text
data/warehouse/olist_dwh.sqlite
docs/data_quality_report.md
```

## Lancer le dashboard

```bash
streamlit run dashboard/app.py
```

## Modèle Data Warehouse

Le modèle conserve uniquement deux tables de faits :

1. `fact_order_performance` : performance des commandes au grain article de commande.
2. `fact_lead_conversion` : conversion marketing au grain MQL.

Les paiements sont agrégés au niveau commande avant allocation aux lignes d'articles. Les avis clients sont aussi agrégés au niveau commande pour éviter de dupliquer les reviews.

Dimensions principales :

```text
dim_date
dim_customer
dim_seller
dim_product
dim_product_category
dim_payment_type
dim_order_status
dim_lead_origin
dim_business_segment
dim_lead_type
dim_lead_profile
dim_sales_team
```

## Pages du rapport Streamlit

- `Executive Overview` : synthèse des KPIs et évolution mensuelle.
- `Sales Performance` : revenus par catégorie, vendeur, État client et paiement.
- `Delivery & Satisfaction` : retard de livraison, délais, notes clients et catégories sensibles.
- `Marketing Funnel` : MQL, conversion par origine/segment et performance commerciale.
- `Data Quality` : contrôles ETL, lignes chargées, relations, doublons et valeurs manquantes.

## Validation

Après l'ETL, lancer :

```bash
python scripts/validate_project.py
```

Le script vérifie :

- les imports des helpers du dashboard ;
- les tables obligatoires du Data Warehouse ;
- les vues SQL `vw_sales_monthly`, `vw_category_performance` et `vw_lead_funnel`.

## Structure du projet

```text
olist-data-warehouse-bi-v2/
|-- dashboard/
|   |-- app.py
|   |-- db.py
|   |-- components.py
|   |-- charts.py
|   `-- pages/
|-- data/
|   |-- raw/
|   `-- warehouse/
|-- docs/
|-- scripts/
|-- screenshots/
|-- sql/
|-- src/
`-- requirements.txt
```

## Screenshots

Les captures d'écran du rapport peuvent être ajoutées dans `screenshots/`.
