# Modèle de données

## Vue générale

Le Data Warehouse SQLite reste volontairement simple. Il contient deux processus métier principaux :

1. ventes, livraison et satisfaction ;
2. acquisition et conversion des vendeurs.

```text
                         dim_date
                            |
dim_customer ----           |          ---- dim_seller
                 \          |         /
                  \         |        /
                   fact_order_performance
                  /    |       |      \
                 /     |       |       \
        dim_product  dim_payment_type  dim_order_status
             |
             |
     dim_product_category


dim_date -------- fact_lead_conversion -------- dim_seller
                    |       |       |
             dim_lead_origin
             dim_business_segment
             dim_lead_type
             dim_lead_profile
             dim_sales_team
```

## `fact_order_performance`

Grain : une ligne par article vendu dans une commande.

Ce grain permet d'analyser les revenus par produit, catégorie et vendeur. Comme une commande peut contenir plusieurs articles, les volumes de commandes doivent être calculés avec `COUNT(DISTINCT order_id)`.

Mesures principales :

- `price`
- `freight_value`
- `item_total_value`
- `payment_value_total`
- `allocated_payment_value`
- `review_score_avg`
- `delivery_delay_days`
- `delivery_difference_days`
- `is_late_delivery`
- `approval_delay_hours`

Les paiements sont agrégés au niveau commande, puis alloués aux lignes d'articles proportionnellement à leur valeur. Les reviews sont agrégées au niveau commande.

## `fact_lead_conversion`

Grain : une ligne par marketing qualified lead.

Ce grain conserve les leads non convertis, indispensables pour calculer correctement le taux de conversion.

Mesures principales :

- `is_converted`
- `conversion_delay_days`
- `declared_monthly_revenue`
- `declared_product_catalog_size`
- `average_stock`

## Dimensions

| Dimension | Rôle |
|---|---|
| `dim_date` | Analyse temporelle commune |
| `dim_customer` | Client, ville et État |
| `dim_seller` | Vendeur, ville et État |
| `dim_product` | Produit et caractéristiques |
| `dim_product_category` | Catégorie produit, avec traduction si disponible |
| `dim_payment_type` | Mode de paiement |
| `dim_order_status` | Statut de commande |
| `dim_lead_origin` | Origine marketing du lead |
| `dim_business_segment` | Segment business |
| `dim_lead_type` | Type de lead |
| `dim_lead_profile` | Profil comportemental du lead |
| `dim_sales_team` | Équipe commerciale SDR/SR |

## Vues SQL utiles

- `vw_sales_monthly`
- `vw_category_performance`
- `vw_lead_funnel`
