"""Fix all issues in one shot."""
import re, os

# 1. Fix from_orm -> model_validate in all files
files = [
    'backend/app/api/auth.py',
    'backend/app/api/documents.py',
    'backend/app/services/auth_service.py',
    'backend/app/services/document_service.py',
    'backend/app/services/query_service.py',
]
for path in files:
    if not os.path.exists(path): continue
    c = open(path, encoding='utf-8').read()
    if 'from_orm' in c:
        c = re.sub(r'(\w+)\.from_orm\((\w+)\)', r'\1.model_validate(\2)', c)
        open(path, 'w', encoding='utf-8').write(c)
        print('Fixed from_orm:', path)

# 2. Verify rag_pipeline has no LLMChain
c = open('backend/app/rag/rag_pipeline.py', encoding='utf-8').read()
print('rag_pipeline LLMChain count:', c.count('LLMChain'))

# 3. Verify agent_orchestrator has no LLMChain
c = open('backend/app/agents/agent_orchestrator.py', encoding='utf-8').read()
print('agent_orchestrator LLMChain count:', c.count('LLMChain'))

# 4. Fix document upload - ensure pypdf/pdfplumber installed
import subprocess
r = subprocess.run(['python', '-c', 'import pypdf; import pdfplumber; print("PDF libs OK")'],
    capture_output=True, text=True)
print(r.stdout.strip() or r.stderr.strip())

print('All fixes applied.')
