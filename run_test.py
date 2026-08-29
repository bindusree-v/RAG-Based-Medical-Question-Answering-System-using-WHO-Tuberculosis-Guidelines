import httpx, time

BASE = "http://localhost:8000/api/v1"
c = httpx.Client(timeout=180.0)

# Login
tok = c.post(f"{BASE}/auth/login",
    data="username=admin&password=Admin123!",
    headers={"Content-Type":"application/x-www-form-urlencoded"}).json()["access_token"]
H = {"Authorization": f"Bearer {tok}"}
print("[OK] Login")

# Upload
txt = b"""WHO Tuberculosis Treatment Guidelines 2022.
First-line regimen: Isoniazid 5mg/kg + Rifampicin 10mg/kg + Pyrazinamide 25mg/kg + Ethambutol 15mg/kg.
Duration: 6 months (2HRZE/4HR). Drug interactions: Rifampicin induces CYP450 enzymes reducing
warfarin efficacy. Adverse effects: hepatotoxicity, peripheral neuropathy.
Contraindications: active hepatic disease. Evidence level A, randomized controlled trials."""

r = c.post(f"{BASE}/documents/upload-document",
    files={"file": ("tb_who.txt", txt, "text/plain")},
    data={"source":"WHO 2022","title":"TB Guidelines"}, headers=H)
print(f"[{'OK' if r.status_code==201 else 'FAIL'}] Upload: {r.status_code} - {r.json().get('validation',{}).get('status','')}")

time.sleep(2)

# Medical Query
print("\nRunning medical query (LLM inference - may take 30-60s)...")
t0 = time.time()
r = c.post(f"{BASE}/query/medical-query",
    json={"query":"What is the treatment for tuberculosis?","top_k":3}, headers=H)
elapsed = round(time.time()-t0, 1)
if r.status_code == 200:
    d = r.json()
    print(f"[OK] Medical Query ({elapsed}s)")
    print(f"     Answer: {d['answer'][:200]}...")
    print(f"     Sources: {len(d['sources'])} | Confidence: {d['confidence_score']}")
else:
    print(f"[FAIL] Query: {r.status_code} - {r.text[:200]}")

# Drug Interaction
print("\nRunning drug interaction check...")
t0 = time.time()
r = c.post(f"{BASE}/query/drug-interaction",
    json={"drug_a":"Rifampicin","drug_b":"Warfarin"}, headers=H)
elapsed = round(time.time()-t0, 1)
if r.status_code == 200:
    d = r.json()
    print(f"[OK] Drug Interaction ({elapsed}s) - Risk: {d['overall_risk_level']}")
else:
    print(f"[FAIL] Drug Interaction: {r.text[:200]}")

# KB Stats
s = c.get(f"{BASE}/documents/documents/stats", headers=H).json()
print(f"\n[OK] KB: {s['total_documents']} docs, {s['total_chunks']} chunks")
c.close()

print("\n========================================")
print(" Frontend  -> http://localhost:3000")
print(" Backend   -> http://localhost:8000")
print(" API Docs  -> http://localhost:8000/docs")
print(" Login     -> admin / Admin123!")
print("========================================")
