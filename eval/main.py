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
    
    process_request = ProcessRequest(
        model_name, 
        wikidata_triples_dir,
        wikidata_entities_file_path, 
        seed, 
        sample_size,
        results_dir_path,
    )

    ret_triples = process_request.read_triples_dir()

    #ret_triples = process_request.read_triples_file()
    #process_request.get_triples_statistics(ret_triples)

    """
    Check if gold triples pasrsed from wikidata api for each entity exists or not
    Local persisted copy will improve the runtime
    """
    if os.path.isfile(gold_triple_file_path) and os.path.getsize(gold_triple_file_path) > 0:
        logger.info("Gold triples file exists ..")
    else:
        logger.info("Gold triples does not exists, it may take a while to create one ...")
        # get the rows from the first file
        first_file_data = next(iter(ret_triples.values()))
        create_gold_triples_file(first_file_data, gold_triple_file_path)


    if verification_method == "web":
        ret_triples_with_snippet = process_request.query_snippets(ret_triples)
        output_dict = process_request.verify_triples(ret_triples_with_snippet)
        print("Output dictionary recording triple verification ... ", output_dict)
    
    

    if verification_method == "wikidata":
        #plausible_triples = soft_match_utils(ret_triples)
        #print(f"Fraction of triples plausible: {len(plausible_triples)/len(ret_triples)}")

        if metric == "precision":
            process_request.compute_precision_dir(ret_triples)
        else:
            process_request.compute_recall_dir(ret_triples)


    




if __name__ == "__main__":
    fire.Fire(main)