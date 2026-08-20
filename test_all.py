"""Full end-to-end test of MediRAG AI."""
import httpx, time

BASE = "http://localhost:8000/api/v1"
c = httpx.Client(timeout=120.0)

print("\n" + "="*50)
print("  MEDIRAG AI - FULL SYSTEM TEST")
print("="*50)

# --- Login ---
r = c.post(f"{BASE}/auth/login",
    data="username=admin&password=Admin123!",
    headers={"Content-Type":"application/x-www-form-urlencoded"})
assert r.status_code == 200, f"Login failed: {r.text}"
tok = r.json()["access_token"]
H = {"Authorization": f"Bearer {tok}"}
print("[OK] Login")

# --- Health ---
h = c.get(f"{BASE}/health").json()
print(f"[OK] Database    : {h['components']['database']['status']}")
print(f"[OK] VectorStore : {h['components']['vector_store']['status']}")
print(f"[OK] LLM         : {h['components']['llm']['status']} ({h['components']['llm'].get('message','')})")

# --- Upload medical document ---
medical_txt = b"""WHO Consolidated Guidelines on Tuberculosis Treatment.
First-line drug treatment: Isoniazid 5mg/kg/day, Rifampicin 10mg/kg/day,
Pyrazinamide 25mg/kg/day, Ethambutol 15mg/kg/day.
Standard regimen: 2HRZE/4HR (6 months total duration).
Drug interactions: Rifampicin is a potent CYP450 inducer - reduces efficacy of
warfarin, oral contraceptives, antiretrovirals.
Adverse effects: Hepatotoxicity (monitor liver function tests monthly),
peripheral neuropathy (supplement pyridoxine 25mg daily),
optic neuritis with Ethambutol (monitor visual acuity).
Contraindications: Active hepatic disease, severe renal impairment.
Drug resistance: MDR-TB defined as resistance to Isoniazid and Rifampicin.
Treatment success rate: 85-90% with directly observed therapy (DOT).
Evidence level: Grade A recommendation based on randomized controlled trials.
Clinical guideline source: WHO 2022 TB Treatment Guidelines."""

r = c.post(f"{BASE}/documents/upload-document",
    files={"file": ("who_tb_guidelines.txt", medical_txt, "text/plain")},
    data={"source": "WHO 2022", "title": "TB Treatment Guidelines"},
    headers=H)
print(f"\n[{'OK' if r.status_code == 201 else 'FAIL'}] Upload document: HTTP {r.status_code}")
if r.status_code == 201:
    data = r.json()
    print(f"     Validation  : {data['validation']['status']}")
    print(f"     Specialty   : {data['validation'].get('medical_specialty','N/A')}")
    print(f"     Processing  : {data['processing_status']}")
    doc_id = data['document_id']
else:
    print(f"     Error: {r.text[:300]}")

# Wait for indexing
time.sleep(2)

# --- Medical Query ---
print("\n--- Testing Medical Chat ---")
r = c.post(f"{BASE}/query/medical-query",
    json={"query": "What are the first-line drugs for tuberculosis treatment?", "top_k": 3},
    headers=H)
print(f"[{'OK' if r.status_code == 200 else 'FAIL'}] Medical Query: HTTP {r.status_code}")
if r.status_code == 200:
    d = r.json()
    print(f"     Answer preview : {d['answer'][:150]}...")
    print(f"     Sources        : {len(d['sources'])}")
    print(f"     Confidence     : {d['confidence_score']}")
    print(f"     Agent          : {d['agent_used']}")
else:
    print(f"     Error: {r.text[:300]}")

# --- Drug Interaction ---
print("\n--- Testing Drug Interaction ---")
r = c.post(f"{BASE}/query/drug-interaction",
    json={"drug_a": "Rifampicin", "drug_b": "Warfarin"},
    headers=H)
print(f"[{'OK' if r.status_code == 200 else 'FAIL'}] Drug Interaction: HTTP {r.status_code}")
if r.status_code == 200:
    d = r.json()
    print(f"     Risk Level : {d['overall_risk_level']}")
    print(f"     Sources    : {len(d['sources'])}")
else:
    print(f"     Error: {r.text[:200]}")

# --- Treatment Protocol ---
print("\n--- Testing Treatment Protocol ---")
r = c.post(f"{BASE}/query/treatment-protocol",
    json={"condition": "Tuberculosis"},
    headers=H)
print(f"[{'OK' if r.status_code == 200 else 'FAIL'}] Treatment Protocol: HTTP {r.status_code}")
if r.status_code == 200:
    d = r.json()
    print(f"     Protocol preview : {d['protocol_summary'][:150]}...")
else:
    print(f"     Error: {r.text[:200]}")

# --- KB Stats ---
r = c.get(f"{BASE}/documents/documents/stats", headers=H)
s = r.json()
print(f"\n[OK] KB Stats: {s['total_documents']} docs, {s['total_chunks']} chunks")

c.close()

print("\n" + "="*50)
print("  OPEN: http://localhost:3000")
print("  LOGIN: admin / Admin123!")
print("="*50)
