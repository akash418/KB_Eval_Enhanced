import fire
from gpt_kbc import GPTKBCRunner
from  prompter_parser import PromptJSONSchema
import os


def main(
        gpt_model_elicitation:str,
        template_path_dir:str,              
        wikidata_entities_file_path: str,
        wikidata_triples_dir:str,           
        job_type: str
):
    
    """
    Main arguments to perform elicitation with possible different prompts
    

    Arguments:
        gpt_model_elicitation (str): Name of the model to use for elicitation
        template_path_dir (str): Dir which stores multiple jinja files, to be used for elicitation, one batch request per prompt file
        wikidata_entities_file_path (str): File path storing the wikidata entities
        wikidata_triples_dir (str): Dir path for storing the elicted triples
        job_type (str): Either `submit`to submit a new request `verify`to just check and process the status of already submitted batches (default)
    
    """


    """
    prompter_parser_module = PromptJSONSchema(
        template_path_elicitation=template_path_elicitation,
        gpt_model_elicitation=gpt_model_elicitation
    )

    gpt_runner = GPTKBCRunner(
        wikidata_entities_file_path = wikidata_entities_file_path,
        wikidata_triples_file_path = wikidata_triples_file_path,
        prompter_parser_module=prompter_parser_module
    )

    list_of_subjects = gpt_runner.get_list_of_subjects()

    gpt_runner.loop(
        subjects_to_expand=list_of_subjects   
    )

    """

    # Iterate through all files in template_path_dir
    for index, file_name in enumerate(os.listdir(template_path_dir), start=1):
        if file_name: 
            file_path = os.path.join(template_path_dir, file_name)

            # Create the PromptJSONSchema instance for the current file
            prompter_parser_module = PromptJSONSchema(
                template_path_elicitation = file_path,
                gpt_model_elicitation = gpt_model_elicitation
            )

            # Pass the instance to GPTKBCRunner
            gpt_runner = GPTKBCRunner(
                curr_index = index,
                wikidata_entities_file_path = wikidata_entities_file_path,
                wikidata_triples_dir = wikidata_triples_dir,
                prompter_parser_module = prompter_parser_module,
                job_type = job_type
            )

            # Run the GPTKBCRunner loop
            list_of_subjects = gpt_runner.get_list_of_subjects()
            gpt_runner.loop(subjects_to_expand = list_of_subjects)

    


if __name__ == "__main__":
    fire.Fire(main)