# Rapport Dashboard Streamlit

Le dashboard a été refactorisé en rapport BI multi-page. La page principale `dashboard/app.py` sert uniquement d'accueil et présente le contexte, la problématique, l'architecture et les pages disponibles.

## Structure

```text
dashboard/
|-- app.py
|-- db.py
|-- components.py
|-- charts.py
`-- pages/
    |-- 1_Executive_Overview.py
    |-- 2_Sales_Performance.py
    |-- 3_Delivery_Satisfaction.py
    |-- 4_Marketing_Funnel.py
    `-- 5_Data_Quality.py
```

## Helpers

- `db.py` centralise l'accès SQLite, les requêtes cachées et les contrôles d'existence des tables/vues.
- `components.py` contient les éléments Streamlit réutilisables: titres, contexte, questions, KPIs, sections et alertes.
- `charts.py` contient les fonctions Plotly Express. Les graphiques reçoivent des DataFrames déjà préparés et ne contiennent pas de SQL.

## Pages

### 1. Executive Overview

Synthèse des indicateurs globaux :

- chiffre d'affaires total ;
- nombre de commandes ;
- nombre de clients ;
- nombre de vendeurs ;
- note moyenne ;
- taux de livraison en retard ;
- nombre de MQL ;
- taux de conversion des leads.

Visualisations : évolution mensuelle du revenu, volume mensuel des commandes, note moyenne mensuelle et conversion mensuelle des leads.

### 2. Sales Performance

Analyse commerciale :

- catégories qui génèrent le plus de revenus ;
- top vendeurs par revenu ;
- commandes par État client ;
- distribution des modes de paiement.

Des filtres simples par année et État client sont proposés.

### 3. Delivery & Satisfaction

Analyse logistique et satisfaction :

- note moyenne selon livraison en retard ou à temps ;
- délai moyen de livraison par État client ;
- taux de retard par État client ;
- distribution des notes ;
- catégories avec les notes moyennes les plus faibles.

La page rappelle que les avis sont agrégés au niveau commande alors que le fait commande est au grain article. Les volumes de commandes sont donc calculés avec `COUNT(DISTINCT order_id)`.

### 4. Marketing Funnel

Analyse marketing :

- MQL par origine ;
- taux de conversion par origine ;
- taux de conversion par segment business ;
- délai moyen de conversion ;
- revenu mensuel déclaré moyen ;
- deals gagnés par commercial SR.

Les leads non convertis restent dans les analyses pour calculer un taux de conversion correct.

### 5. Data Quality

Lecture de `etl_quality_report` et contrôles SQL complémentaires. Cette page aide à interpréter les indicateurs avec prudence en exposant les limites des données.
