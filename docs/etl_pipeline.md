# Pipeline ETL

## 1. Extract

Le script lit les CSV depuis `data/raw/`. Les fichiers transactionnels et marketing principaux sont requis. Le fichier `product_category_name_translation.csv` est optionnel : s'il est absent, les catégories originales sont conservées comme libellés.

Les colonnes de dates connues sont parsées au moment de la lecture.

## 2. Transform

Transformations principales :

- normalisation des libellés texte ;
- création de clés de dates au format `YYYYMMDD` ;
- création des dimensions ;
- agrégation des paiements au niveau commande ;
- agrégation des reviews au niveau commande ;
- calcul des délais et retards de livraison ;
- calcul du délai de conversion marketing ;
- mapping des clés de dimensions vers les deux faits ;
- génération d'un rapport qualité.

Le pipeline ne crée pas de nouvelles tables de faits. Les deux grains restent :

- `fact_order_performance` : article de commande ;
- `fact_lead_conversion` : MQL.

## 3. Load

Le chargement se fait dans SQLite :

```text
data/warehouse/olist_dwh.sqlite
```

Les tables sont écrites via pandas, puis trois vues SQL sont créées pour simplifier le reporting :

- `vw_sales_monthly`
- `vw_category_performance`
- `vw_lead_funnel`

## 4. Rapport qualité

Le pipeline produit :

```text
etl_quality_report
docs/data_quality_report.md
```

Contrôles inclus :

- nombre de lignes par source ;
- note sur la source optionnelle de traduction des catégories ;
- nombre de lignes par dimension et fait ;
- commandes sans items, paiement ou avis ;
- deals sans MQL ;
- vendeurs de closed deals absents de la table seller marketplace ;
- doublons sur les identifiants principaux ;
- valeurs manquantes importantes.

## Commande

```bash
python -m src.run_etl --raw-data-dir data/raw --warehouse-path data/warehouse/olist_dwh.sqlite
```
