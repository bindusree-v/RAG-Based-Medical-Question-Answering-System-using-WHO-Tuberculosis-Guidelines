"""Fix LLMChain -> LCEL in rag_pipeline.py"""

with open('backend/app/rag/rag_pipeline.py', encoding='utf-8') as f:
    c = f.read()

# Add StrOutputParser import
if 'StrOutputParser' not in c:
    c = c.replace(
        'from langchain_core.prompts import PromptTemplate',
        'from langchain_core.prompts import PromptTemplate\nfrom langchain_core.output_parsers import StrOutputParser'
    )

# Replace each LLMChain+chain.run pair with LCEL
fixes = [
    (
        'chain = LLMChain(llm=self._get_llm(), prompt=MEDICAL_QA_PROMPT)\n        answer = chain.run(context=context, question=query)',
        'answer = (MEDICAL_QA_PROMPT | self._get_llm() | StrOutputParser()).invoke({"context": context, "question": query})'
    ),
    (
        'chain = LLMChain(llm=self._get_llm(), prompt=DRUG_INTERACTION_PROMPT)\n        answer = chain.run(context=context, drug_a=drug_a, drug_b=drug_b)',
        'answer = (DRUG_INTERACTION_PROMPT | self._get_llm() | StrOutputParser()).invoke({"context": context, "drug_a": drug_a, "drug_b": drug_b})'
    ),
    (
        'chain = LLMChain(llm=self._get_llm(), prompt=SYMPTOM_QUERY_PROMPT)\n        answer = chain.run(context=context, symptoms=symptoms_text)',
        'answer = (SYMPTOM_QUERY_PROMPT | self._get_llm() | StrOutputParser()).invoke({"context": context, "symptoms": symptoms_text})'
    ),
    (
        'chain = LLMChain(llm=self._get_llm(), prompt=TREATMENT_PROTOCOL_PROMPT)\n        answer = chain.run(context=context, condition=condition)',
        'answer = (TREATMENT_PROTOCOL_PROMPT | self._get_llm() | StrOutputParser()).invoke({"context": context, "condition": condition})'
    ),
]

for old, new in fixes:
    c = c.replace(old, new)

with open('backend/app/rag/rag_pipeline.py', 'w', encoding='utf-8') as f:
    f.write(c)

remaining = c.count('LLMChain')
print('Done. LLMChain refs remaining:', remaining)
print('FIXED!' if remaining == 0 else 'ERROR - still has LLMChain')
