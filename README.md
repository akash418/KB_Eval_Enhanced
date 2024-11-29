This project serves as evaluation framework for GPTKBC, builds on the new eliciation pipeline

Please use **Python 3.11**. You can install the required packages by running:

```bash
pip install -r requirements.txt
```

List of entities handpicked from Wikidata - ```wikidata_entities.json```

Steps to use:
- Knowledge elicitation from wikidata entities using the prompt in templates folder, executable example

```bash
python main.py \
    --template_path_elicitation templates/prompts/prompt_elicitation.json.jinja \
    --gpt_model_elicitation "gpt-4o-mini" \
```

running this command will save triples in ```wikidata_triples.csv```

- Fact Verification: (web search snippet generation +  LLM fact verification) or soft matching from wikidata

```bash

cd eval/

python main.py \
    --model_name "gpt-4o-mini" \
    --wikidata_triples_file_path KB_Eval_Enhanced/wikidata_triples.csv \
    --seed 42 \
    --verification_method wikidata
```


How the evaluation framework works?
- Get a collection of triples with elicitation prompt on handpicked entities from wikidata
- Perform fact verification on sampled triples

Output of evaluation framework
- Web verification paradigm gives fraction of triples falling into either of these categories (True, Plausible, Not plausible, Snippet cannot be collected)
- Soft matching from wikidata, fraction of triples that can be semantically matched by parsed claims from wikidata api