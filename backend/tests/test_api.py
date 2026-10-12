from decimal import Decimal

from tests.conftest import upload


def categories_by_name(client):
    return {c["name"]: c["id"] for c in client.get("/api/categories").json()}


def test_health(client):
    assert client.get("/api/health").json() == {"status": "ok"}


def test_new_user_gets_default_categories(client):
    assert {"Income", "Dining", "Transport", "Transfers"} <= set(categories_by_name(client))


def test_upload_imports_and_reupload_is_deduplicated(client):
    resp, _ = upload(client, "chase_checking.csv")
    assert resp.status_code == 201, resp.text
    body = resp.json()
    assert (body["parser_name"], body["rows_imported"], body["rows_duplicate"]) == ("chase_checking", 9, 0)

    resp, _ = upload(client, "chase_checking.csv")
    body = resp.json()
    # Both identical Starbucks rows are kept the first time and skipped the second.
    assert (body["rows_imported"], body["rows_duplicate"]) == (0, 9)
    assert client.get("/api/transactions").json()["total"] == 9


def test_unrecognised_file_is_rejected(client):
    account = client.post("/api/accounts", json={"name": "Checking"}).json()
    resp = client.post(
        "/api/uploads",
        data={"account_id": str(account["id"])},
        files={"file": ("x.csv", b"a,b\n1,2\n", "text/csv")},
    )
    assert resp.status_code == 422
    assert "Unrecognised" in resp.json()["detail"]


def test_rules_categorise_on_import_with_most_specific_match(client):
    upload(client, "chase_checking.csv")
    cats = categories_by_name(client)
    by_desc = {t["description"]: t["category_id"] for t in client.get("/api/transactions").json()["items"]}
    assert by_desc["UBER EATS 8005928996 CA"] == cats["Dining"]
    assert by_desc["UBER TRIP HELP.UBER.COM"] == cats["Transport"]
    assert by_desc["WHOLEFDS MKT 10234"] == cats["Groceries"]
    assert by_desc["ONLINE TRANSFER TO SAV XXXX0000"] == cats["Transfers"]


def test_apply_rules_respects_manual_categories(client):
    upload(client, "chase_checking.csv")
    cats = categories_by_name(client)
    txns = {t["description"]: t for t in client.get("/api/transactions", params={"q": "STARBUCKS"}).json()["items"]}
    assert len(txns) == 1  # both rows share a description

    items = client.get("/api/transactions", params={"q": "WHOLEFDS"}).json()["items"]
    manual = client.patch(f"/api/transactions/{items[0]['id']}", json={"category_id": cats["Shopping"]})
    assert manual.json()["category_locked"] is True

    coffee = client.post("/api/categories", json={"name": "Coffee"}).json()
    client.post("/api/category-rules", json={"category_id": coffee["id"], "pattern": "STARBUCKS", "priority": 10})
    client.post("/api/category-rules", json={"category_id": coffee["id"], "pattern": "WHOLEFDS", "priority": 10})
    assert client.post("/api/category-rules/apply").json() == {"updated": 2}

    starbucks = client.get("/api/transactions", params={"q": "STARBUCKS"}).json()["items"]
    assert {t["category_id"] for t in starbucks} == {coffee["id"]}
    wholefoods = client.get("/api/transactions", params={"q": "WHOLEFDS"}).json()["items"]
    assert wholefoods[0]["category_id"] == cats["Shopping"]


def test_invalid_regex_rule_is_rejected(client):
    cat_id = categories_by_name(client)["Dining"]
    resp = client.post("/api/category-rules", json={"category_id": cat_id, "pattern": "([", "match_type": "regex"})
    assert resp.status_code == 422


def test_analytics_exclude_transfers(client):
    upload(client, "chase_checking.csv")
    summary = client.get("/api/analytics/summary").json()
    # Income: two paychecks. Spending excludes the 500.00 transfer to savings.
    assert Decimal(summary["income"]) == Decimal("5000.00")
    assert Decimal(summary["spending"]) == Decimal("1322.65")
    assert Decimal(summary["net"]) == Decimal("3677.35")

    monthly = client.get("/api/analytics/monthly").json()
    assert [(m["month"], Decimal(m["income"]), Decimal(m["spending"])) for m in monthly] == [
        ("2026-01", Decimal("2500.00"), Decimal("1285.55")),
        ("2026-02", Decimal("2500.00"), Decimal("37.10")),
    ]

    jan = client.get("/api/analytics/summary", params={"date_from": "2026-01-01", "date_to": "2026-01-31"}).json()
    assert Decimal(jan["spending"]) == Decimal("1285.55")

    by_cat = {c["category"]: Decimal(c["spending"]) for c in client.get("/api/analytics/by-category").json()}
    assert by_cat["Housing"] == Decimal("1200.00")
    assert "Transfers" not in by_cat
    assert list(by_cat)[0] == "Housing"


def test_balance_history_is_end_of_day(client):
    upload(client, "chase_checking.csv")
    upload(client, "chase_credit.csv", account_name="Card", account_type="credit")
    series = client.get("/api/analytics/balance").json()
    assert len(series) == 1  # credit card exports have no balance column
    points = {p["date"]: Decimal(p["balance"]) for p in series[0]["points"]}
    assert points["2026-01-31"] == Decimal("1714.00")
    assert points["2026-02-03"] == Decimal("4176.90")


def test_deleting_upload_removes_its_transactions(client):
    resp, _ = upload(client, "chase_checking.csv")
    assert client.delete(f"/api/uploads/{resp.json()['id']}").status_code == 204
    assert client.get("/api/transactions").json()["total"] == 0
    assert client.get("/api/uploads").json() == []


def test_users_cannot_see_or_touch_each_others_data(clients):
    alice, bob = clients("alice"), clients("bob")
    resp, alice_account = upload(alice, "chase_checking.csv")
    alice_upload = resp.json()
    alice_txn = alice.get("/api/transactions").json()["items"][0]
    alice_cat = categories_by_name(alice)["Dining"]
    alice_rule = alice.get("/api/category-rules").json()[0]

    # Bob sees none of Alice's data...
    assert bob.get("/api/accounts").json() == []
    assert bob.get("/api/uploads").json() == []
    assert bob.get("/api/transactions").json()["total"] == 0
    assert Decimal(bob.get("/api/analytics/summary").json()["income"]) == 0
    assert bob.get("/api/analytics/balance").json() == []
    assert alice_cat not in categories_by_name(bob).values()

    # ...and can't use or change it by id.
    bob_file = {"file": ("c.csv", b"x", "text/csv")}
    assert bob.post("/api/uploads", data={"account_id": str(alice_account["id"])}, files=bob_file).status_code == 404
    assert bob.delete(f"/api/uploads/{alice_upload['id']}").status_code == 404
    assert bob.patch(f"/api/transactions/{alice_txn['id']}", json={"category_id": None}).status_code == 404
    assert bob.patch(f"/api/categories/{alice_cat}", json={"name": "Hacked"}).status_code == 404
    assert bob.delete(f"/api/categories/{alice_cat}").status_code == 404
    assert bob.delete(f"/api/category-rules/{alice_rule['id']}").status_code == 404

    # Bob can't assign Alice's category to his own transaction or rule.
    upload(bob, "chase_checking.csv")
    bob_txn = bob.get("/api/transactions").json()["items"][0]
    assert bob.patch(f"/api/transactions/{bob_txn['id']}", json={"category_id": alice_cat}).status_code == 404
    assert bob.post("/api/category-rules", json={"category_id": alice_cat, "pattern": "X"}).status_code == 404

    # The same statement imports independently for each user.
    assert alice.get("/api/transactions").json()["total"] == 9
    assert bob.get("/api/transactions").json()["total"] == 9


def test_profile_defaults_empty_and_can_be_updated(client):
    me = client.get("/api/me").json()
    assert (me["first_name"], me["last_name"]) == (None, None)

    resp = client.patch("/api/me", json={"first_name": "  Ada ", "last_name": "Lovelace"})
    assert resp.status_code == 200
    assert (resp.json()["first_name"], resp.json()["last_name"]) == ("Ada", "Lovelace")

    # Partial update leaves the other field alone; blank clears it.
    client.patch("/api/me", json={"last_name": ""})
    me = client.get("/api/me").json()
    assert (me["first_name"], me["last_name"]) == ("Ada", None)

    assert client.patch("/api/me", json={"first_name": "x" * 101}).status_code == 422


def test_profiles_are_per_user(clients):
    alice, bob = clients("alice"), clients("bob")
    alice.patch("/api/me", json={"first_name": "Alice"})
    assert bob.get("/api/me").json()["first_name"] is None
    assert alice.get("/api/me").json()["first_name"] == "Alice"


def test_theme_preference(client):
    assert client.get("/api/me").json()["theme"] is None  # follow the device by default
    assert client.patch("/api/me", json={"theme": "dark"}).json()["theme"] == "dark"
    # Updating names leaves the theme alone.
    client.patch("/api/me", json={"first_name": "Ada"})
    assert client.get("/api/me").json()["theme"] == "dark"
    assert client.patch("/api/me", json={"theme": None}).json()["theme"] is None
    assert client.patch("/api/me", json={"theme": "blue"}).status_code == 422


def test_default_time_window_preference(client):
    assert client.get("/api/me").json()["default_range"] is None  # all time
    assert client.patch("/api/me", json={"default_range": "12m"}).json()["default_range"] == "12m"
    client.patch("/api/me", json={"theme": "dark"})
    assert client.get("/api/me").json()["default_range"] == "12m"
    assert client.patch("/api/me", json={"default_range": "2y"}).status_code == 422
