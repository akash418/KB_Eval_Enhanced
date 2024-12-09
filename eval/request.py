from openai import OpenAI

class Request:
    def __init__(self, model_name: str = "gpt-4o-mini", max_tokens = 3000):
        self.model_name = model_name
        self.max_tokens = max_tokens
        self.client = OpenAI() 

    def verify_triple_lm_snippet(self, triple, snippet):
        """

        Get the facts and web parsed snippet, and ask LLM as a judge if the fact
        entails or is plausible

        """

        triple_prompt_str = f"Statement to verify: {triple}."
        snippet_prompt_str = f"Snippet to verify from: {snippet}"
        response = self.client.chat.completions.create(
            messages=[
                {"role": "user",
                    "content": "Can the given RDF be inferred from the given snippet? \
                                Please choose the correct option based on your answer and return only a or b or c or d: \
                                a) The RDF statement is true according to the snippet.\
                                b) The RDF statement is plausible according to the snippet. \
                                c) The RDF statement is implausible according to the snippet. \
                                d) The RDF statement is false according to the snippet."},
                {"role": "user", "content": triple_prompt_str},
                {"role": "user", "content": snippet_prompt_str},
            ],
            model = self.model_name,
            max_tokens = self.max_tokens,
            temperature=0.0,
        )
        return response.choices[0].message.content
    

    def verify_triple_lm_wikidata(self, triple, wikidata_triples):
        """

        Get the facts and wikidata gold triple and ask LLM as a judge if it the fact 
        entails or is plausible

        """

        triple_prompt_str = f"Statement to verify: {triple}."
        wikidata_prompt_str = f"List of triples to verify from :{str(wikidata_triples)}"
        response = self.client.chat.completions.create(
            messages=[
                {"role": "user",
                    "content": "Can the given RDF be inferred from the given list of triples? \
                                Please choose the correct option based on your answer and return only a or b or c or d: \
                                a) The RDF statement is true according to the snippet.\
                                b) The RDF statement is plausible according to the snippet. \
                                c) The RDF statement is implausible according to the snippet. \
                                d) The RDF statement is false according to the snippet."},
                {"role": "user", "content": triple_prompt_str},
                {"role": "user", "content": wikidata_prompt_str},
            ],
            model = self.model_name,
            max_tokens = self.max_tokens,
            temperature=0.0,
        )
        return response.choices[0].message.content