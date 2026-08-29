"""Fix stale imports in backend files."""
import re

# --- Fix security.py ---
with open('backend/app/utils/security.py', encoding='utf-8') as f:
    sec = f.read()

# Only patch if still has passlib
if 'passlib' in sec:
    # Remove passlib lines
    sec = re.sub(r'from passlib\.context import CryptContext\n', '', sec)
    sec = re.sub(r'pwd_context = CryptContext\(.*?\)\n', '', sec)
    # Add bcrypt import after the existing imports if not there
    if 'import bcrypt' not in sec:
        sec = sec.replace('from jose import JWTError, jwt', 'import bcrypt\nfrom jose import JWTError, jwt')
    with open('backend/app/utils/security.py', 'w', encoding='utf-8') as f:
        f.write(sec)
    print("Fixed security.py")
else:
    print("security.py already clean")

# --- Fix rag_pipeline.py ---
with open('backend/app/rag/rag_pipeline.py', encoding='utf-8') as f:
    rag = f.read()

if 'langchain.chains' in rag:
    rag = rag.replace('from langchain.chains import LLMChain\n', '')
    if 'StrOutputParser' not in rag:
        rag = rag.replace(
            'from langchain_core.prompts import PromptTemplate',
            'from langchain_core.prompts import PromptTemplate\nfrom langchain_core.output_parsers import StrOutputParser'
        )
    with open('backend/app/rag/rag_pipeline.py', 'w', encoding='utf-8') as f:
        f.write(rag)
    print("Fixed rag_pipeline.py")
else:
    print("rag_pipeline.py already clean")

print("Done.")
