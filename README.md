This project serves as evaluation framework for GPTKBC, builds on the new eliciation pipeline

Please use **Python 3.11**. You can install the required packages by running:

```bash
pip install -r requirements.txt
```

List of entities handpicked from Wikidata - wikidata_entities.json

Steps to use:
- Knowledge elicitation from wikidata entities using the prompt in templates folder, executable example

```bash
python main.py \
    --template_path_elicitation templates/prompts/prompt_elicitation.json.jinja \
    --gpt_model_elicitation "gpt-4o-mini" \
```

- Fact Verification: web search snippet generation +  LLM fact verification

```bash

cd eval/

python main.py \
    --model_name "gpt-4o-mini" \
    --wikidata_triples_file_path KB_Eval_Enhanced/wikidata_triples.csv \
    --seed 42

```
