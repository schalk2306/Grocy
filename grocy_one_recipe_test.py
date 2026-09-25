import json
import urllib.request
import urllib.error

# ============================================================
# GROCY ONE-RECIPE TEST
# ============================================================
# 1. Put your Grocy demo URL below (no trailing slash).
# 2. Put a NEW/TEMPORARY API key below.
# 3. First run with DRY_RUN = True.
# 4. If the read-only checks look correct, change DRY_RUN to False.
#
# IMPORTANT: This test intentionally uses products/units that ALREADY
# exist in Grocy. It does NOT create master-data products automatically.
# That keeps the first test safe and easy to undo.
# ============================================================

BASE_URL = "https://test-9kwvh5llgqigdinx3k553d.demo.grocy.info"
API_KEY = "PASTE_A_FRESH_TEMP_API_KEY_HERE"
DRY_RUN = True

# Replace this with the recipe we choose after the connection test.
# Product names and unit names must already exist in your Grocy demo.
RECIPE = {
    "name": "IMPORT TEST - Scrambled Eggs",
    "description": """TEST IMPORT FROM RECIPE KEEPER

Method:
1. Beat the eggs with the milk.
2. Melt the butter in a pan over medium-low heat.
3. Add the eggs and stir gently until just set.
4. Season to taste.""",
    "servings": 2,
    "ingredients": [
        {"product": "Egg", "amount": 4, "unit": "piece", "note": ""},
        {"product": "Milk", "amount": 60, "unit": "ml", "note": ""},
        {"product": "Butter", "amount": 15, "unit": "g", "note": ""},
    ],
}


def api(method, path, payload=None):
    url = BASE_URL.rstrip("/") + "/api" + path
    headers = {
        "GROCY-API-KEY": API_KEY,
        "Accept": "application/json",
    }
    data = None
    if payload is not None:
        headers["Content-Type"] = "application/json"
        data = json.dumps(payload).encode("utf-8")
    req = urllib.request.Request(url, data=data, headers=headers, method=method)
    try:
        with urllib.request.urlopen(req, timeout=30) as response:
            body = response.read().decode("utf-8")
            return json.loads(body) if body else None
    except urllib.error.HTTPError as e:
        detail = e.read().decode("utf-8", errors="replace")
        raise RuntimeError(f"Grocy API error {e.code} on {method} {path}\n{detail}") from e


def norm(s):
    return str(s).strip().casefold()


def get_all(entity):
    return api("GET", f"/objects/{entity}")


def find_by_name(rows, name):
    target = norm(name)
    exact = [r for r in rows if norm(r.get("name", "")) == target]
    return exact[0] if exact else None


def main():
    if "PASTE_A_FRESH" in API_KEY:
        raise SystemExit("Paste a fresh temporary Grocy API key into API_KEY first.")

    print("1) Testing API connection...")
    info = api("GET", "/system/info")
    version = (info or {}).get("grocy_version", {}).get("Version", "unknown")
    print(f"   Connected successfully. Grocy version: {version}")

    print("\n2) Reading existing master data...")
    products = get_all("products")
    units = get_all("quantity_units")
    recipes = get_all("recipes")
    print(f"   Products: {len(products)}")
    print(f"   Quantity units: {len(units)}")
    print(f"   Recipes: {len(recipes)}")

    print("\n3) Checking the test recipe dependencies...")
    resolved = []
    problems = []

    for ing in RECIPE["ingredients"]:
        p = find_by_name(products, ing["product"])
        u = find_by_name(units, ing["unit"])
        if not p:
            problems.append(f'Missing product: "{ing["product"]}"')
        if not u:
            problems.append(f'Missing quantity unit: "{ing["unit"]}"')
        if p and u:
            resolved.append((ing, p, u))
            print(f'   OK: {ing["amount"]} {ing["unit"]} {ing["product"]} '
                  f'(product_id={p["id"]}, qu_id={u["id"]})')

    if problems:
        print("\nSTOPPED SAFELY. Nothing was created.")
        print("Please create/rename these in Grocy, or edit the names in this script:")
        for x in problems:
            print("  -", x)
        print("\nAvailable quantity units in your Grocy demo:")
        print("  " + ", ".join(sorted([str(x.get("name", "")) for x in units])))
        return

    existing = find_by_name(recipes, RECIPE["name"])
    if existing:
        print(f'\nSTOPPED: A recipe named "{RECIPE["name"]}" already exists (id={existing["id"]}).')
        print("Delete it in Grocy or change RECIPE['name'] before trying again.")
        return

    if DRY_RUN:
        print("\nDRY RUN PASSED. Nothing has been changed.")
        print("Open the script, change DRY_RUN = True to DRY_RUN = False, save, and run it again.")
        return

    print("\n4) Creating recipe...")
    recipe_payload = {
        "name": RECIPE["name"],
        "description": RECIPE["description"],
        "base_servings": RECIPE["servings"],
        "desired_servings": RECIPE["servings"],
        "not_check_shoppinglist": 0,
        "type": "normal",
    }
    created = api("POST", "/objects/recipes", recipe_payload)
    recipe_id = created.get("created_object_id")
    print(f"   Recipe created: id={recipe_id}")

    print("\n5) Adding linked inventory ingredients...")
    for ing, p, u in resolved:
        payload = {
            "recipe_id": recipe_id,
            "product_id": p["id"],
            "amount": ing["amount"],
            "qu_id": u["id"],
            "note": ing.get("note", ""),
            "only_check_single_unit_in_stock": 0,
            "not_check_stock_fulfillment": 0,
            "variable_amount": "",
            "price_factor": 1,
        }
        result = api("POST", "/objects/recipes_pos", payload)
        print(f'   Added: {ing["amount"]} {ing["unit"]} {ing["product"]} '
              f'(recipe_pos_id={result.get("created_object_id")})')

    print("\nSUCCESS.")
    print(f'Open: {BASE_URL.rstrip("/")}/recipes')
    print(f'Look for: {RECIPE["name"]}')
    print("\nThis recipe is linked to real Grocy products, so Grocy can use stock")
    print("fulfilment/missing-ingredient logic rather than treating ingredients as plain text.")


if __name__ == "__main__":
    main()
