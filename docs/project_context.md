# Project Context — Olist E-commerce BI Pipeline

## Objectif

Construire un mini-système décisionnel complet à partir des fichiers CSV Olist : extraction, transformation, Data Warehouse et rapport Streamlit.

Le projet suit la logique BI suivante :

```text
Sources de données → Problématique → ETL → Data Warehouse → Reporting
```

## Problématique métier

Olist veut suivre deux axes importants :

1. La performance de son activité e-commerce : ventes, catégories, vendeurs, paiements, livraison et satisfaction client.
2. La performance de son acquisition de vendeurs : leads marketing, conversion en closed deals, segments business et commerciaux.

## Décision de modélisation

Le projet utilise seulement deux tables de faits afin de rester clair :

- `fact_order_performance`
- `fact_lead_conversion`

Chaque table de faits représente un vrai processus métier. On évite de créer une table de faits pour chaque fichier source.

## Sources utilisées

| Source | Utilisation |
|---|---|
| `olist_orders_dataset.csv` | Commandes, dates et statuts |
| `olist_order_items_dataset.csv` | Articles vendus, prix, frais de port, vendeurs |
| `olist_order_payments_dataset.csv` | Paiements et moyens de paiement |
| `olist_order_reviews_dataset.csv` | Satisfaction client |
| `olist_customers_dataset.csv` | Clients et localisation |
| `olist_products_dataset.csv` | Produits et attributs |
| `product_category_name_translation.csv` | Traduction des catégories |
| `olist_sellers_dataset.csv` | Vendeurs marketplace |
| `olist_marketing_qualified_leads_dataset.csv` | Leads marketing |
| `olist_closed_deals_dataset.csv` | Deals gagnés et acquisition vendeurs |

## Limites assumées

- Le fichier de géolocalisation complet n'est pas utilisé en v1 pour éviter de complexifier le modèle.
- Les paiements sont agrégés au niveau commande puis alloués aux lignes de commande.
- Les avis sont agrégés au niveau commande.
- Le dashboard est analytique, pas opérationnel.
