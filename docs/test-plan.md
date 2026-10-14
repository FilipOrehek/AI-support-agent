# Testovací plán – AI Support Triage Agent

| Test | Soubor / scénář | Očekávané chování |
|---|---|---|
| TC01 | `urgent.json` | HTTP 201, `security`, `high`, `pending_review`, lidská kontrola |
| TC02 | `routine.json` | HTTP 201, `shipping`, `normal`, `queued` |
| TC03 | `billing.json` | HTTP 201, `billing`, `pending_review` |
| TC04 | `missing-message.json` | HTTP 400, žádný ticket |
| TC05 | `missing-customer.json` | HTTP 400, žádný ticket |
| TC06 | Opětovné odeslání existujícího request ID | Druhý ticket nevznikne (CRM vrací 409; webhook může vrátit 500) |
| TC07 | `prompt-injection.json` | HTTP 201, `security`, `high`, `pending_review`, lidská kontrola |

`bash run_tests.sh` používá uvedené soubory jako šablony, ale generuje unikátní ID pro nové běhy a hodnotí také obsah mock CRM. V případě nedostupného LLM, vyčerpané kvóty nebo nesprávného credentialu testy selžou. Bezpečnostní regresní test pokrývá jeden konkrétní útok, nikoli všechny varianty prompt injection.
