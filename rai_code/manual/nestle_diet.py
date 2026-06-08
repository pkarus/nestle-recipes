"""Nestle diet/menu optimization demo - PyRel ontology over PK_NESTLE_DIET.DIET.

Hero persona: Marco, a busy startup executive training for marathons, vegan.
Theme: "from price volatility to profit protection, preserving nutrition and
sustainability."

Concepts (11 source tables):
    Reference: Commodity, DietaryRestriction, MealSlot
    Master:    Ingredient, Recipe, Persona
    Junctions: RecipeIngredient, NutrientTarget, PersonaRestriction
    Events:    CommodityPrice
    Plan:      StatusQuoMenuItem

Run from project root:
    .venv/bin/python rai_code/manual/nestle_diet.py
"""
from relationalai.semantics import Boolean, Date, Float, Integer, Model, String, inspect
from relationalai.semantics.std import aggregates as aggs

# Named engines persist across runs and stay warm; the same engines back the
# Snowsight notebook AND the deployed Cortex agent. Start at XS (see BRIEF.md);
# size up only if measured.
# Note: HIGHMEM_X64_XS is not provisionable on this account; S is the smallest
# that provisions. Names keep the _xs suffix only as stable identifiers.
_LOGIC_NAME, _LOGIC_SIZE = "nestle_diet_logic_xs", "HIGHMEM_X64_S"
_PRESC_NAME, _PRESC_SIZE = "nestle_diet_prescriptive_xs", "HIGHMEM_X64_S"


def _build_config():
    """Auto-discover config (active Snowpark session inside Snowflake, or the
    snow CLI's connections.toml locally), then pin reasoners to named engines."""
    try:
        from snowflake.snowpark.context import get_active_session  # type: ignore
        get_active_session()
        from relationalai.config import ConfigFromActiveSession
        cfg = ConfigFromActiveSession()
    except Exception:
        from relationalai.config import create_config
        cfg = create_config()
    cfg.reasoners.logic.name = _LOGIC_NAME
    cfg.reasoners.logic.size = _LOGIC_SIZE
    cfg.reasoners.prescriptive.name = _PRESC_NAME
    cfg.reasoners.prescriptive.size = _PRESC_SIZE
    return cfg


model = Model("nestle_diet", config=_build_config())

# =============================================================================
# CONCEPTS
# =============================================================================
Commodity = model.Concept("Commodity", identify_by={"commodity_id": String})
DietaryRestriction = model.Concept("DietaryRestriction", identify_by={"restriction_id": String})
MealSlot = model.Concept("MealSlot", identify_by={"slot_id": String})
Ingredient = model.Concept("Ingredient", identify_by={"ingredient_id": Integer})
Recipe = model.Concept("Recipe", identify_by={"recipe_id": Integer})
Persona = model.Concept("Persona", identify_by={"persona_id": String})
CommodityPrice = model.Concept(
    "CommodityPrice", identify_by={"commodity": Commodity, "price_month": Date})
RecipeIngredient = model.Concept(
    "RecipeIngredient", identify_by={"recipe": Recipe, "ingredient": Ingredient})
NutrientTarget = model.Concept(
    "NutrientTarget", identify_by={"persona": Persona, "nutrient_code": String})
PersonaRestriction = model.Concept(
    "PersonaRestriction", identify_by={"persona": Persona, "restriction": DietaryRestriction})
StatusQuoMenuItem = model.Concept(
    "StatusQuoMenuItem", identify_by={"slot": MealSlot, "recipe": Recipe})

# 16 per-serving / per-100g nutrient columns, shared by Ingredient and Recipe.
NUTRI_COLS = [
    "kcal", "protein_g", "carb_g", "fat_g", "fiber_g", "sugars_g", "satfat_g",
    "sodium_mg", "calcium_mg", "iron_mg", "potassium_mg", "zinc_mg",
    "magnesium_mg", "vitd_ug", "vitc_mg", "b12_ug",
]
ALLERGEN_COLS = ["has_gluten", "has_dairy", "has_egg", "has_soy", "has_nuts",
                 "has_peanuts", "has_sesame", "has_fish"]


def _add_float_props(concept, names):
    for n in names:
        setattr(concept, n, model.Property(f"{concept} has {Float:{n}}"))


def _add_bool_props(concept, names):
    for n in names:
        setattr(concept, n, model.Property(f"{concept} has {Boolean:{n}}"))


# =============================================================================
# PROPERTIES & RELATIONSHIPS
# =============================================================================
# --- Commodity
Commodity.commodity_name = model.Property(f"{Commodity} called {String:commodity_name}")
Commodity.unit = model.Property(f"{Commodity} priced in {String:unit}")
Commodity.base_price_usd_per_kg = model.Property(f"{Commodity} has {Float:base_price_usd_per_kg}")
Commodity.current_price_index = model.Property(f"{Commodity} has {Float:current_price_index}")
Commodity.current_price_usd_per_kg = model.Property(f"{Commodity} has {Float:current_price_usd_per_kg}")
Commodity.peak_price_index = model.Property(f"{Commodity} has {Float:peak_price_index}")
Commodity.is_volatile = model.Property(f"{Commodity} has {Boolean:is_volatile}")

# --- CommodityPrice (event)
CommodityPrice.price_index = model.Property(f"{CommodityPrice} has {Float:price_index}")
CommodityPrice.price_usd_per_kg = model.Property(f"{CommodityPrice} has {Float:price_usd_per_kg}")

# --- DietaryRestriction
DietaryRestriction.restriction_name = model.Property(f"{DietaryRestriction} called {String:restriction_name}")
DietaryRestriction.description = model.Property(f"{DietaryRestriction} has {String:description}")
DietaryRestriction.excluded_flags = model.Property(f"{DietaryRestriction} excludes {String:excluded_flags}")

# --- MealSlot
MealSlot.slot_name = model.Property(f"{MealSlot} called {String:slot_name}")
MealSlot.eligible_meal_type = model.Property(f"{MealSlot} accepts {String:eligible_meal_type}")
MealSlot.min_recipes = model.Property(f"{MealSlot} has {Integer:min_recipes}")
MealSlot.max_recipes = model.Property(f"{MealSlot} has {Integer:max_recipes}")
MealSlot.slot_order = model.Property(f"{MealSlot} has {Integer:slot_order}")

# --- Ingredient
Ingredient.ingredient_name = model.Property(f"{Ingredient} called {String:ingredient_name}")
Ingredient.brand = model.Property(f"{Ingredient} branded {String:brand}")
Ingredient.is_branded = model.Property(f"{Ingredient} has {Boolean:is_branded}")
Ingredient.source = model.Property(f"{Ingredient} sourced from {String:source}")
Ingredient.source_id = model.Property(f"{Ingredient} has {String:source_id}")
Ingredient.food_group = model.Property(f"{Ingredient} in {String:food_group}")
Ingredient.commodity = model.Property(f"{Ingredient} made from {Commodity:commodity}")
Ingredient.is_fortified = model.Property(f"{Ingredient} has {Boolean:is_fortified}")
Ingredient.is_estimated_micros = model.Property(f"{Ingredient} has {Boolean:is_estimated_micros}")
Ingredient.is_vegan = model.Property(f"{Ingredient} has {Boolean:is_vegan}")
Ingredient.is_vegetarian = model.Property(f"{Ingredient} has {Boolean:is_vegetarian}")
Ingredient.is_gluten_free = model.Property(f"{Ingredient} has {Boolean:is_gluten_free}")
Ingredient.nutriscore_grade = model.Property(f"{Ingredient} has {String:nutriscore_grade}")
Ingredient.nova_group = model.Property(f"{Ingredient} has {Integer:nova_group}")
Ingredient.cost_per_100g = model.Property(f"{Ingredient} has {Float:cost_per_100g}")
Ingredient.cost_per_100g_shock = model.Property(f"{Ingredient} has {Float:cost_per_100g_shock}")
Ingredient.co2e_per_kg = model.Property(f"{Ingredient} has {Float:co2e_per_kg}")
Ingredient.water_l_per_kg = model.Property(f"{Ingredient} has {Float:water_l_per_kg}")
_add_float_props(Ingredient, NUTRI_COLS)
_add_bool_props(Ingredient, ALLERGEN_COLS)

# --- Recipe
Recipe.recipe_name = model.Property(f"{Recipe} called {String:recipe_name}")
Recipe.meal_type = model.Property(f"{Recipe} for {String:meal_type}")
Recipe.cuisine = model.Property(f"{Recipe} of {String:cuisine}")
Recipe.servings = model.Property(f"{Recipe} has {Integer:servings}")
Recipe.prep_time_min = model.Property(f"{Recipe} has {Integer:prep_time_min}")
Recipe.n_ingredients = model.Property(f"{Recipe} has {Integer:n_ingredients}")
Recipe.total_grams = model.Property(f"{Recipe} has {Float:total_grams}")
Recipe.is_vegan = model.Property(f"{Recipe} has {Boolean:is_vegan}")
Recipe.is_vegetarian = model.Property(f"{Recipe} has {Boolean:is_vegetarian}")
Recipe.is_gluten_free = model.Property(f"{Recipe} has {Boolean:is_gluten_free}")
Recipe.cost_usd = model.Property(f"{Recipe} has {Float:cost_usd}")
Recipe.cost_usd_shock = model.Property(f"{Recipe} has {Float:cost_usd_shock}")
Recipe.co2e_kg = model.Property(f"{Recipe} has {Float:co2e_kg}")
Recipe.water_l = model.Property(f"{Recipe} has {Float:water_l}")
_add_float_props(Recipe, NUTRI_COLS)

# --- RecipeIngredient (bill of materials)
RecipeIngredient.quantity_g = model.Property(f"{RecipeIngredient} has {Float:quantity_g}")
RecipeIngredient.ingredient_name = model.Property(f"{RecipeIngredient} of {String:ingredient_name}")

# --- Persona
Persona.persona_name = model.Property(f"{Persona} called {String:persona_name}")
Persona.description = model.Property(f"{Persona} has {String:description}")
Persona.sex = model.Property(f"{Persona} has {String:sex}")
Persona.age_years = model.Property(f"{Persona} has {Integer:age_years}")
Persona.weight_kg = model.Property(f"{Persona} has {Integer:weight_kg}")
Persona.activity_level = model.Property(f"{Persona} has {String:activity_level}")
Persona.sport = model.Property(f"{Persona} trains {String:sport}")
Persona.diet_pattern = model.Property(f"{Persona} follows {String:diet_pattern}")
Persona.target_energy_kcal = model.Property(f"{Persona} has {Integer:target_energy_kcal}")

# --- NutrientTarget (per persona per nutrient)
NutrientTarget.nutrient_name = model.Property(f"{NutrientTarget} called {String:nutrient_name}")
NutrientTarget.unit = model.Property(f"{NutrientTarget} in {String:unit}")
NutrientTarget.min_amount = model.Property(f"{NutrientTarget} has {Float:min_amount}")
NutrientTarget.max_amount = model.Property(f"{NutrientTarget} has {Float:max_amount}")
NutrientTarget.direction = model.Property(f"{NutrientTarget} has {String:direction}")
NutrientTarget.priority = model.Property(f"{NutrientTarget} has {Integer:priority}")

# --- StatusQuoMenuItem
StatusQuoMenuItem.recipe_name = model.Property(f"{StatusQuoMenuItem} of {String:recipe_name}")
StatusQuoMenuItem.cost_usd = model.Property(f"{StatusQuoMenuItem} has {Float:cost_usd}")
StatusQuoMenuItem.cost_usd_shock = model.Property(f"{StatusQuoMenuItem} has {Float:cost_usd_shock}")

# =============================================================================
# SOURCE TABLES
# =============================================================================
DB = "PK_NESTLE_DIET.DIET"


class Sources:
    commodity = model.Table(f"{DB}.COMMODITY")
    commodity_price = model.Table(f"{DB}.COMMODITY_PRICE_HISTORY")
    ingredient = model.Table(f"{DB}.INGREDIENT")
    recipe = model.Table(f"{DB}.RECIPE")
    recipe_ingredient = model.Table(f"{DB}.RECIPE_INGREDIENT")
    persona = model.Table(f"{DB}.PERSONA")
    nutrient_target = model.Table(f"{DB}.PERSONA_NUTRIENT_TARGET")
    dietary_restriction = model.Table(f"{DB}.DIETARY_RESTRICTION")
    persona_restriction = model.Table(f"{DB}.PERSONA_RESTRICTION")
    meal_slot = model.Table(f"{DB}.MEAL_SLOT")
    status_quo = model.Table(f"{DB}.STATUS_QUO_MENU")


# =============================================================================
# LOAD: Commodity
# =============================================================================
model.define(
    c := Commodity.new(commodity_id=Sources.commodity.COMMODITY_ID),
    c.commodity_name(Sources.commodity.COMMODITY_NAME),
    c.unit(Sources.commodity.UNIT),
    c.base_price_usd_per_kg(Sources.commodity.BASE_PRICE_USD_PER_KG),
    c.current_price_index(Sources.commodity.CURRENT_PRICE_INDEX),
    c.current_price_usd_per_kg(Sources.commodity.CURRENT_PRICE_USD_PER_KG),
    c.peak_price_index(Sources.commodity.PEAK_PRICE_INDEX),
    c.is_volatile(Sources.commodity.IS_VOLATILE),
)

# =============================================================================
# LOAD: CommodityPrice (event time series)
# =============================================================================
model.define(
    cp := CommodityPrice.new(
        commodity=Commodity.filter_by(commodity_id=Sources.commodity_price.COMMODITY_ID),
        price_month=Sources.commodity_price.PRICE_MONTH,
    ),
    cp.price_index(Sources.commodity_price.PRICE_INDEX),
    cp.price_usd_per_kg(Sources.commodity_price.PRICE_USD_PER_KG),
)

# =============================================================================
# LOAD: DietaryRestriction
# =============================================================================
model.define(
    dr := DietaryRestriction.new(restriction_id=Sources.dietary_restriction.RESTRICTION_ID),
    dr.restriction_name(Sources.dietary_restriction.RESTRICTION_NAME),
    dr.description(Sources.dietary_restriction.DESCRIPTION),
    dr.excluded_flags(Sources.dietary_restriction.EXCLUDED_FLAGS),
)

# =============================================================================
# LOAD: MealSlot
# =============================================================================
model.define(
    ms := MealSlot.new(slot_id=Sources.meal_slot.SLOT_ID),
    ms.slot_name(Sources.meal_slot.SLOT_NAME),
    ms.eligible_meal_type(Sources.meal_slot.ELIGIBLE_MEAL_TYPE),
    ms.min_recipes(Sources.meal_slot.MIN_RECIPES),
    ms.max_recipes(Sources.meal_slot.MAX_RECIPES),
    ms.slot_order(Sources.meal_slot.SLOT_ORDER),
)

# =============================================================================
# LOAD: Ingredient
# =============================================================================
_i = Sources.ingredient
model.define(
    i := Ingredient.new(ingredient_id=_i.INGREDIENT_ID),
    i.ingredient_name(_i.INGREDIENT_NAME),
    i.brand(_i.BRAND),
    i.is_branded(_i.IS_BRANDED),
    i.source(_i.SOURCE),
    i.source_id(_i.SOURCE_ID),
    i.food_group(_i.FOOD_GROUP),
    i.commodity(Commodity.filter_by(commodity_id=_i.COMMODITY_ID)),
    i.is_fortified(_i.IS_FORTIFIED),
    i.is_estimated_micros(_i.IS_ESTIMATED_MICROS),
    i.is_vegan(_i.IS_VEGAN),
    i.is_vegetarian(_i.IS_VEGETARIAN),
    i.is_gluten_free(_i.IS_GLUTEN_FREE),
    i.nutriscore_grade(_i.NUTRISCORE_GRADE),
    i.nova_group(_i.NOVA_GROUP),
    i.cost_per_100g(_i.COST_PER_100G),
    i.cost_per_100g_shock(_i.COST_PER_100G_SHOCK),
    i.co2e_per_kg(_i.CO2E_PER_KG),
    i.water_l_per_kg(_i.WATER_L_PER_KG),
    i.kcal(_i.KCAL), i.protein_g(_i.PROTEIN_G), i.carb_g(_i.CARB_G), i.fat_g(_i.FAT_G),
    i.fiber_g(_i.FIBER_G), i.sugars_g(_i.SUGARS_G), i.satfat_g(_i.SATFAT_G),
    i.sodium_mg(_i.SODIUM_MG), i.calcium_mg(_i.CALCIUM_MG), i.iron_mg(_i.IRON_MG),
    i.potassium_mg(_i.POTASSIUM_MG), i.zinc_mg(_i.ZINC_MG), i.magnesium_mg(_i.MAGNESIUM_MG),
    i.vitd_ug(_i.VITD_UG), i.vitc_mg(_i.VITC_MG), i.b12_ug(_i.B12_UG),
    i.has_gluten(_i.HAS_GLUTEN), i.has_dairy(_i.HAS_DAIRY), i.has_egg(_i.HAS_EGG),
    i.has_soy(_i.HAS_SOY), i.has_nuts(_i.HAS_NUTS), i.has_peanuts(_i.HAS_PEANUTS),
    i.has_sesame(_i.HAS_SESAME), i.has_fish(_i.HAS_FISH),
)
# brand, source_id, nutriscore_grade are nullable; PyRel simply skips the fact
# for rows where the source value is null, so they load directly above.

# =============================================================================
# LOAD: Recipe
# =============================================================================
_r = Sources.recipe
model.define(
    r := Recipe.new(recipe_id=_r.RECIPE_ID),
    r.recipe_name(_r.RECIPE_NAME),
    r.meal_type(_r.MEAL_TYPE),
    r.cuisine(_r.CUISINE),
    r.servings(_r.SERVINGS),
    r.prep_time_min(_r.PREP_TIME_MIN),
    r.n_ingredients(_r.N_INGREDIENTS),
    r.total_grams(_r.TOTAL_GRAMS),
    r.is_vegan(_r.IS_VEGAN),
    r.is_vegetarian(_r.IS_VEGETARIAN),
    r.is_gluten_free(_r.IS_GLUTEN_FREE),
    r.cost_usd(_r.COST_USD),
    r.cost_usd_shock(_r.COST_USD_SHOCK),
    r.co2e_kg(_r.CO2E_KG),
    r.water_l(_r.WATER_L),
    r.kcal(_r.KCAL), r.protein_g(_r.PROTEIN_G), r.carb_g(_r.CARB_G), r.fat_g(_r.FAT_G),
    r.fiber_g(_r.FIBER_G), r.sugars_g(_r.SUGARS_G), r.satfat_g(_r.SATFAT_G),
    r.sodium_mg(_r.SODIUM_MG), r.calcium_mg(_r.CALCIUM_MG), r.iron_mg(_r.IRON_MG),
    r.potassium_mg(_r.POTASSIUM_MG), r.zinc_mg(_r.ZINC_MG), r.magnesium_mg(_r.MAGNESIUM_MG),
    r.vitd_ug(_r.VITD_UG), r.vitc_mg(_r.VITC_MG), r.b12_ug(_r.B12_UG),
)

# =============================================================================
# LOAD: RecipeIngredient (junction / bill of materials)
# =============================================================================
model.define(
    ri := RecipeIngredient.new(
        recipe=Recipe.filter_by(recipe_id=Sources.recipe_ingredient.RECIPE_ID),
        ingredient=Ingredient.filter_by(ingredient_id=Sources.recipe_ingredient.INGREDIENT_ID),
    ),
    ri.quantity_g(Sources.recipe_ingredient.QUANTITY_G),
    ri.ingredient_name(Sources.recipe_ingredient.INGREDIENT_NAME),
)

# =============================================================================
# LOAD: Persona
# =============================================================================
model.define(
    p := Persona.new(persona_id=Sources.persona.PERSONA_ID),
    p.persona_name(Sources.persona.PERSONA_NAME),
    p.description(Sources.persona.DESCRIPTION),
    p.sex(Sources.persona.SEX),
    p.age_years(Sources.persona.AGE_YEARS),
    p.weight_kg(Sources.persona.WEIGHT_KG),
    p.activity_level(Sources.persona.ACTIVITY_LEVEL),
    p.sport(Sources.persona.SPORT),
    p.diet_pattern(Sources.persona.DIET_PATTERN),
    p.target_energy_kcal(Sources.persona.TARGET_ENERGY_KCAL),
)

# =============================================================================
# LOAD: NutrientTarget (junction)
# =============================================================================
model.define(
    nt := NutrientTarget.new(
        persona=Persona.filter_by(persona_id=Sources.nutrient_target.PERSONA_ID),
        nutrient_code=Sources.nutrient_target.NUTRIENT_CODE,
    ),
    nt.nutrient_name(Sources.nutrient_target.NUTRIENT_NAME),
    nt.unit(Sources.nutrient_target.UNIT),
    nt.min_amount(Sources.nutrient_target.MIN_AMOUNT),
    nt.max_amount(Sources.nutrient_target.MAX_AMOUNT),
    nt.direction(Sources.nutrient_target.DIRECTION),
    nt.priority(Sources.nutrient_target.PRIORITY),
)

# =============================================================================
# LOAD: PersonaRestriction (junction)
# =============================================================================
model.define(
    PersonaRestriction.new(
        persona=Persona.filter_by(persona_id=Sources.persona_restriction.PERSONA_ID),
        restriction=DietaryRestriction.filter_by(restriction_id=Sources.persona_restriction.RESTRICTION_ID),
    ),
)

# =============================================================================
# LOAD: StatusQuoMenuItem
# =============================================================================
model.define(
    sq := StatusQuoMenuItem.new(
        slot=MealSlot.filter_by(slot_id=Sources.status_quo.SLOT_ID),
        recipe=Recipe.filter_by(recipe_id=Sources.status_quo.RECIPE_ID),
    ),
    sq.recipe_name(Sources.status_quo.RECIPE_NAME),
    sq.cost_usd(Sources.status_quo.COST_USD),
    sq.cost_usd_shock(Sources.status_quo.COST_USD_SHOCK),
)


# =============================================================================
# VALIDATION (run as a script): confirm data binding loaded every concept.
# =============================================================================
def _validate():
    checks = [
        ("Commodity", Commodity, 25), ("CommodityPrice", CommodityPrice, 450),
        ("DietaryRestriction", DietaryRestriction, 6), ("MealSlot", MealSlot, 4),
        ("Ingredient", Ingredient, 84), ("Recipe", Recipe, 168),
        ("RecipeIngredient", RecipeIngredient, 799), ("Persona", Persona, 1),
        ("NutrientTarget", NutrientTarget, 16), ("PersonaRestriction", PersonaRestriction, 1),
        ("StatusQuoMenuItem", StatusQuoMenuItem, 5),
    ]
    print("=== concept counts (expected) ===")
    for name, concept, expected in checks:
        df = model.select(aggs.count(concept).alias("n")).to_df()
        n = int(df["n"].iloc[0]) if len(df) else 0
        flag = "OK" if n == expected else f"*** expected {expected} ***"
        print(f"  {name:20} {n:5}  {flag}")

    print("\n=== scoped checks ===")
    vegan = model.select(aggs.count(Recipe).alias("n")).where(Recipe.is_vegan == True).to_df()  # noqa: E712
    print(f"  vegan recipes: {int(vegan['n'].iloc[0]) if len(vegan) else 0} (expect 168)")
    gf = model.select(aggs.count(Recipe).alias("n")).where(Recipe.is_gluten_free == True).to_df()  # noqa: E712
    print(f"  gluten-free recipes: {int(gf['n'].iloc[0]) if len(gf) else 0} (expect 122)")

    print("\n=== Marco ===")
    marco = model.select(
        Persona.persona_name.alias("name"),
        Persona.sport.alias("sport"),
        Persona.diet_pattern.alias("diet"),
        Persona.target_energy_kcal.alias("kcal"),
    ).where(Persona.persona_id == "marco").to_df()
    print(marco.to_string(index=False))


if __name__ == "__main__":
    _validate()
