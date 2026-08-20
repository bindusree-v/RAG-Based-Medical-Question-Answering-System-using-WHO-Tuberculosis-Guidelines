"""Fix all blocking LLM calls in query_service to use run_in_executor."""
with open('backend/app/services/query_service.py', encoding='utf-8') as f:
    c = f.read()

# Fix drug_interaction_query - wrap orchestrator.run with executor
old1 = '''        state = self._orchestrator.run(
            query=f"drug interaction {request.drug_a} and {request.drug_b}",
            query_type="drug_interaction",
            drug_a=request.drug_a,
            drug_b=request.drug_b,
            top_k=5,
        )'''

new1 = '''        loop = asyncio.get_event_loop()
        state = await loop.run_in_executor(
            _executor,
            lambda: self._orchestrator.run(
                query=f"drug interaction {request.drug_a} and {request.drug_b}",
                query_type="drug_interaction",
                drug_a=request.drug_a,
                drug_b=request.drug_b,
                top_k=5,
            )
        )'''

# Fix symptom_query
old2 = '''        state = self._orchestrator.run(
            query=" ".join(request.symptoms),
            query_type="symptom",
            symptoms=request.symptoms,
            top_k=5,
        )'''

new2 = '''        loop = asyncio.get_event_loop()
        state = await loop.run_in_executor(
            _executor,
            lambda: self._orchestrator.run(
                query=" ".join(request.symptoms),
                query_type="symptom",
                symptoms=request.symptoms,
                top_k=5,
            )
        )'''

# Fix treatment_protocol_query
old3 = '''        state = self._orchestrator.run(
            query=f"treatment protocol guidelines {request.condition}",
            query_type="treatment",
            condition=request.condition,
            top_k=5,
        )'''

new3 = '''        loop = asyncio.get_event_loop()
        state = await loop.run_in_executor(
            _executor,
            lambda: self._orchestrator.run(
                query=f"treatment protocol guidelines {request.condition}",
                query_type="treatment",
                condition=request.condition,
                top_k=5,
            )
        )'''

c = c.replace(old1, new1)
c = c.replace(old2, new2)
c = c.replace(old3, new3)

with open('backend/app/services/query_service.py', 'w', encoding='utf-8') as f:
    f.write(c)

print("Fixed query_service.py - all LLM calls now run in executor")
