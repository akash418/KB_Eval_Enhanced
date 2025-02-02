import fire
from request import Request
from process_request import ProcessRequest
from wikidata_utils import *
import os
from loguru import logger

def main(
        wikidata_triples_dir:str,
        wikidata_entities_file_path:str,
        model_name:str,
        seed: str,
        verification_method: str,
        sample_size: int,
        metric: str,
        results_dir_path:str
):  
    """
    Main function to perform eval on multiple elicited triples with specified parameters

    Arguments:
        wikidata_triples_str (str): Directory path storing the collection of elicited csv triples files
        wikidata_entities_file_path (str): File path storing the manually curated wikidata entity files
        model_name (str): Name of the LLM that will be used for evaluation
        seed (str): Seed value that will be used to identify the snippet directory for storing web instances
        verification_method (str): Either wikidata or web
        sample_size (int): Size of the random sample. Select -1 if you dont want to sample
        metric (str): Type precision or recall
        results_dir_path (str): Directory path for storing the eval results
    
    
    """
    # path where all wikidata parsed facts will be stored for each entity
    gold_triple_file_path = os.getcwd() + "/gold.json"
    

    # basic sanity check to make sure all entities exist on wikidata
    with open(wikidata_entities_file_path, 'r') as file:
        json_content = json.load(file)
    all_entities = [item for key, values in json_content.items() for item in values]
    for each_entity in all_entities:
        if sanity_check_entity(each_entity) == False:
            print(f"Entity {each_entity} does not exist on wikidata ...")
            
    
    valid_methods = ["web", "wikidata"]
    if verification_method not in valid_methods:
        raise ValueError(f"Invalid verification method. Choose from {valid_methods}")

    if not os.path.exists(results_dir_path):
        os.makedirs(results_dir_path)
    
    process_request = ProcessRequest(
        model_name, 
        wikidata_triples_dir,
        wikidata_entities_file_path, 
        seed, 
        sample_size,
        results_dir_path,
    )

    ret_triples = process_request.read_triples_dir()

    """
    Check if gold triples pasrsed from wikidata api for each entity exists or not
    Local persisted copy will improve the runtime
    """
    if os.path.isfile(gold_triple_file_path) and os.path.getsize(gold_triple_file_path) > 0:
        logger.info("Gold triples file exists ..")
    else:
        logger.info("Gold triples does not exists, it may take a while to create one ...")
        # get the data from the first file
        first_file_data = next(iter(ret_triples.values()))
        create_gold_triples_file(first_file_data, gold_triple_file_path)

    # need to verify if it works fine with the new changes
    if verification_method == "web":
        ret_triples_with_snippet = process_request.query_snippets(ret_triples)
        output_dict = process_request.verify_triples(ret_triples_with_snippet)
        print("Output dictionary recording triple verification ... ", output_dict)
    

    if verification_method == "wikidata":

        if metric == "precision":
            process_request.compute_precision_dir(ret_triples)
        else:
            process_request.compute_recall_dir(ret_triples)

        output_filename = os.path.join(results_dir_path, f"results.csv")    
        process_request.write_to_csv(output_filename, process_request.aggregated_data)



if __name__ == "__main__":
    fire.Fire(main)