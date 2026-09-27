"""Held-out evaluation set: harder, ambiguous cases written AFTER the rules
were frozen and NOT used to tune them. This is the honest number."""
import json
from pathlib import Path
D = Path(__file__).parent / "eval_sets"
held = {
 "routing": [
  ("Connexion refusée au serveur depuis ce matin", "FR", "Nous ne pouvons pas nous connecter, merci de nous aider.", 3, False, "server", "L1-EMEA-EN"),
  ("Query about our invoice and license true-up", "US", "Finance asked about the invoice.", 4, False, "licensing", "LICENSING"),
  ("Workflow fails in Portuguese locale", "BR", "O fluxo falha ao executar no servidor.", 3, False, "server", "L1-AMER-EN"),
  ("Server slow", "IN", "slow since yesterday", 3, False, "server", "L1-APAC-EN"),
  ("Help with renewing the SSL cert on our server", "US", "Our certificate renewal broke login.", 3, False, "server", "L1-AMER-EN"),
  ("Datenexport fehlerhaft", "AT", "Der Export ist nicht vollständig und die Werte fehlen.", 3, False, "connectors", "L1-EMEA-DE"),
 ],
 "knowledge_queries": [
  ("our nightly refresh never kicks off since we patched the box", "on_prem", "KB-1001"),
  ("sign-in page loops back, identity provider changed keys", "any", "KB-1003"),
  ("snowflake-type warehouse pull dies at the 5 minute mark", "cloud", "KB-1005"),
  ("some records vanish when headers have accents like é", "cloud", "JIRA-4411"),
  ("setup wizard rolls back at the end", "on_prem", "KB-1006"),
  ("personal access token expired automated flow broken", "cloud", "KB-1008"),
 ],
 "repeat_asks": [
  (["fiddler trace"], "Thanks for the HAR file. Could you also grab the server logs?", False),
  (["server logs"], "Could you re-send the service log from the worker node?", True),
  (["product version"], "Which build number are you running?", True),
  (["screenshot"], "I reviewed the screenshot you shared; the error points to the proxy.", False),
 ],
 "statuses": [
  ("I've looped in a senior engineer and will come back to you today.", False, False, "Pending Customer", "Pending Internal"),
  ("Once you've applied the patch, please confirm if the schedule runs.", False, False, "Pending Customer", "Pending Customer"),
  ("As you asked, we'll pause this until your change window next week.", True, False, "Hold", "Hold"),
  ("We're reproducing this in our lab.", False, False, "Hold", "Pending Internal"),
 ],
 "logs": [
  ("har", '{"entries":[{"response":{"status":503}}]}', None),
  ("server", "2026-09-02 ERROR java.lang.OutOfMemoryError: Java heap space", "MEMORY_OOM"),
  ("connector", "[Microsoft][ODBC Driver Manager] Data source name not found (IM002)", "ODBC_IM002"),
  ("eventlog", "Event 7000: The Worker service failed to start: Logon failure", None),
 ],
 "scripts": [
  ("Get-ChildItem C:\\Temp | Remove-Item -Force", "BLOCK"),
  ("find /opt/app/logs -mtime +30 -delete", "BLOCK"),
  ("Stop-Service Worker; Start-Service Worker", "REVIEW"),
  ("TRUNCATE TABLE staging_jobs; -- backup taken in step 1", "REVIEW"),
 ],
 "compose": [
  ("Please do the needful at the earliest.", ["non_native_phrasing"]),
  ("Great question! Here are a few things that might help: clear your cache, update to the latest version, and contact your administrator.", ["generic_ai_text"]),
  ("The HAR you sent shows a 503 from the load balancer, so the request never reaches the server. Can your network team check the health probe?", []),
 ],
}
for k, v in held.items():
    (D / f"heldout_{k}.json").write_text(json.dumps(v, indent=1, ensure_ascii=False))
print("held-out written")
