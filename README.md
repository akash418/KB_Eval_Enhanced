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
    --wikidata_entities_file_path /content/KB_Eval_Enhanced/wikidata_entities.json \
    --wikidata_triples_file_path /content/KB_Eval_Enhanced/wikidata_triples.csv

```

running this command will save triples in the location specified in ```wikidata_triples.csv```

- Fact Verification: 

```bash

cd eval/

python main.py \
    --model_name "gpt-4o-mini" \
    --wikidata_triples_file_path /content/KB_Eval_Enhanced/wikidata_triples.csv \
    --seed 42 \
    --verification_method wikidata \
    --wikidata_entities_file_path /content/KB_Eval_Enhanced/wikidata_entities.json \
    --sampling False

```

verification_method: wikidata or web (Specify the generation source of gold triples: web snippet or wikidata)
sampling: do you want get results for just sampled model generated facts? 

How the evaluation framework works?
- Get a collection of triples with elicitation prompt on handpicked entities from wikidata
- Perform fact verification using LLM as a judge


Output of evaluation framework
- Fraction of triples falling into either of these categories (True, Plausible, Not plausible, False)
