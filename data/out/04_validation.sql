-- 04_validation.sql - anchored-number checks for the Nestle diet demo
USE DATABASE PK_NESTLE_DIET;
USE SCHEMA DIET;

-- A. Catalog size. Expect ingredient=84 (off=18), recipe=168.
SELECT 'ingredients' AS metric, COUNT(*) AS value FROM ingredient
UNION ALL SELECT 'ingredients_off', COUNT(*) FROM ingredient WHERE source = 'off'
UNION ALL SELECT 'recipes', COUNT(*) FROM recipe;

-- B. Diet eligibility. Expect vegan recipes=168, gluten-free recipes=122.
SELECT 'vegan_recipes' AS metric, COUNT(*) AS value FROM recipe WHERE is_vegan
UNION ALL SELECT 'gluten_free_recipes', COUNT(*) FROM recipe WHERE is_gluten_free;

-- C. Q1 problem exposure: the cheapest recipe per slot (1 breakfast,
--    2 mains, 2 snacks) is cheap but misses nutrition targets.
WITH ranked AS (
  SELECT recipe_id, recipe_name, meal_type, cost_usd, kcal, protein_g, b12_ug, vitd_ug, calcium_mg,
         ROW_NUMBER() OVER (PARTITION BY meal_type ORDER BY cost_usd) AS rn
  FROM recipe WHERE is_vegan
),
naive AS (
  SELECT * FROM ranked WHERE (meal_type = 'breakfast' AND rn = 1)
     OR (meal_type = 'main' AND rn <= 2) OR (meal_type = 'snack' AND rn <= 2)
)
SELECT ROUND(SUM(cost_usd),2) AS naive_cost_usd, ROUND(SUM(kcal),0) AS kcal,
       ROUND(SUM(protein_g),0) AS protein_g, ROUND(SUM(b12_ug),1) AS b12_ug,
       ROUND(SUM(vitd_ug),1) AS vitd_ug, ROUND(SUM(calcium_mg),0) AS calcium_mg
FROM naive;  -- expect ~$5.01, protein<98, b12<2.4, vitd<15, kcal<2800 (fails targets)

-- D. Q3 price-shock story: status-quo menu cost baseline vs shock.
--    Expect baseline ~$7.32, shock ~$8.26.
SELECT ROUND(SUM(cost_usd),2) AS status_quo_baseline_usd,
       ROUND(SUM(cost_usd_shock),2) AS status_quo_shock_usd,
       ROUND(SUM(cost_usd_shock) - SUM(cost_usd),2) AS shock_increase_usd
FROM status_quo_menu;

-- E. Marco's nutrient targets present (expect 16 rows).
SELECT COUNT(*) AS nutrient_targets FROM persona_nutrient_target WHERE persona_id = 'marco';

-- F. Referential integrity spot-checks (expect 0 orphans).
SELECT 'orphan_recipe_ingredients' AS check_name, COUNT(*) AS bad FROM recipe_ingredient ri
  LEFT JOIN recipe r ON ri.recipe_id = r.recipe_id WHERE r.recipe_id IS NULL
UNION ALL SELECT 'orphan_ingredient_commodity', COUNT(*) FROM ingredient i
  LEFT JOIN commodity c ON i.commodity_id = c.commodity_id WHERE c.commodity_id IS NULL;