This project serves as evaluation framework for GPTKBC, builds on the new eliciation pipeline

Please use **Python 3.11**. You can install the required packages by running:

```bash
pip install -r requirements.txt
```

List of entities handpicked from Wikidata - ```wikidata_entities.json```

Functionalities of this framework:
- Designed to work with multiple prompt files
- Produce precision and recall numbers in different settings


Contents of various prompts
```
prompt_elicitation.json.jinja: Standard elicitation files with expected cardinality and other behaviours.

```

Make changes to jinja file to record elicitaton with different cardinality or instructions in the directory ```templates/prompts/``` to produce different prompts.


Steps to use:
- Knowledge elicitation from wikidata entities using the prompt in templates folder, executable example (Submitting new batches)

```bash

cd elicitation/

INFO: Showing help with the command 'main.py -- --help'.

NAME
    main.py - Main arguments to perform elicitation with possible different prompts

SYNOPSIS
    main.py GPT_MODEL_ELICITATION TEMPLATE_PATH_DIR WIKIDATA_ENTITIES_FILE_PATH WIKIDATA_TRIPLES_DIR JOB_TYPE

DESCRIPTION
    Main arguments to perform elicitation with possible different prompts

POSITIONAL ARGUMENTS
    GPT_MODEL_ELICITATION
        Type: str
        Name of the model to use for elicitation
    TEMPLATE_PATH_DIR
        Type: str
        Dir which stores multiple jinja files, to be used for elicitation, one batch request per prompt file
    WIKIDATA_ENTITIES_FILE_PATH
        Type: str
        File path storing the wikidata entities
    WIKIDATA_TRIPLES_DIR
        Type: str
        Dir path for storing the elicted triples
    JOB_TYPE
        Type: str
        Either `submit`to submit a new request `verify`to just check and process the status of already submitted batches (default)

NOTES
    You can also use flags syntax for POSITIONAL ARGUMENTS



python main.py \
--template_path_dir templates/prompts/ \
--gpt_model_elicitation "gpt-4o-mini" \
--wikidata_entities_file_path /content/KB_Eval_Enhanced/wikidata_entities.json \
--wikidata_triples_dir /content/KB_Eval_Enhanced/elicited_triples \
--job_type "submit"

```

This command will submit batch jobs. It will create all the necessary directories, along with a file named ```jinja_index_mapping.txt```that records mappings from jinja used as prompts to indexes for producing csv during elicitation. 

For eg if directory ```templates/prompts```contains two prompt files, ```prompt_a.json.jinja``` and ```prompt_b.json_jinja```, then appropriating index will be assigned where first file will be index 1 and second one will be index 2.

Note: Please wait for time of approx 2 hrs (standard waiting time for completing the batch jobs)

Run this command to produce the elicited triples for all the prompts 
````
python main.py \
--template_path_dir templates/prompts/ \
--gpt_model_elicitation "gpt-4o-mini" \
--wikidata_entities_file_path /content/KB_Eval_Enhanced/wikidata_entities.json \
--wikidata_triples_dir /content/KB_Eval_Enhanced/elicited_triples \
--job_type "verify"

````

It will save the parsed triples in the directory specified. Files will be named as ```wikidata_triples_<unique_index>.csv```



- Evaluation: 

The evaluation is just a follow-up on the previous steps.

```bash

cd eval/

INFO: Showing help with the command 'main.py -- --help'.

NAME
    main.py - Main function to perform eval on multiple elicited triples with specified parameters

SYNOPSIS
    main.py WIKIDATA_TRIPLES_DIR WIKIDATA_ENTITIES_FILE_PATH MODEL_NAME SEED VERIFICATION_METHOD SAMPLE_SIZE METRIC RESULTS_DIR_PATH

DESCRIPTION
    Main function to perform eval on multiple elicited triples with specified parameters

POSITIONAL ARGUMENTS
    WIKIDATA_TRIPLES_DIR
        Type: str
        Directory path storing the collection of elicited csv triples files
    WIKIDATA_ENTITIES_FILE_PATH
        Type: str
        File path storing the manually curated wikidata entity files
    MODEL_NAME
        Type: str
        Name of the LLM that will be used for evaluation
    SEED
        Type: str
        Seed value that will be used to identify the snippet directory for storing web instances
    VERIFICATION_METHOD
        Type: str
        Either wikidata or web
    SAMPLE_SIZE
        Type: int
        Size of the random sample. Select -1 if you dont want to sample
    METRIC
        Type: str
        Type precision or recall
    RESULTS_DIR_PATH
        Type: str
        Directory path for storing the eval results as csv format

NOTES
    You can also use flags syntax for POSITIONAL ARGUMENTS


python python main.py --model_name "gpt-4o-mini" \
--wikidata_triples_dir /content/KB_Eval_Enhanced/elicited_triples/ \
--seed 42 \
--verification_method wikidata \
--wikidata_entities_file_path /content/KB_Eval_Enhanced/wikidata_entities.json \
--sample_size 20 \
--metric "recall" \
--results_dir_path /content/KB_Eval_Enhanced/results/

```

Running this command will save the output as csv with naming convention ``` wikidata_triples_<unique_index>_<precision/recall>_results.csv``` in the directory specified as CLI argument ```results_dir_path```. The contents of one results CSV file looks like this.
|True|Plausible|Implausible|False|Total \#Triples|
|---|---|---|---|---|
|0\.4864864864864865|0\.13513513513513514|0\.2972972972972973|0\.08108108108108109|37|
