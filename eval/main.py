import fire
from request import Request
from process_request import ProcessRequest
from wikidata_utils import *
import os
from loguru import logger

def main(
        wikidata_triples_file_path:str,
        wikidata_entities_file_path:str,
        model_name:str,
        seed: str,
        verification_method: str,
        sampling: True,
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
        wikidata_triples_file_path,
        wikidata_entities_file_path, 
        seed, 
        sampling
    )

    ret_triples = process_request.read_triples_file()
    process_request.get_triples_statistics(ret_triples)

    """
    Check if gold triples pasrsed from wikidata api for each entity exists or not
    Local persisted copy will improve the runtime
    """
    if os.path.isfile(gold_triple_file_path) and os.path.getsize(gold_triple_file_path) > 0:
        logger.info("Gold triples file exists ..")
    else:
        logger.info("Gold triples does not exists, it may take a while to create one ...")
        create_gold_triples_file(ret_triples, gold_triple_file_path)


    if verification_method == "web":
        ret_triples_with_snippet = process_request.query_snippets(ret_triples)
        output_dict = process_request.verify_triples(ret_triples_with_snippet)
        print("Output dictionary recording triple verification ... ", output_dict)
    
    

    if verification_method == "wikidata":
        #plausible_triples = soft_match_utils(ret_triples)
        #print(f"Fraction of triples plausible: {len(plausible_triples)/len(ret_triples)}")

        #process_request.compute_wikidata_precision(ret_triples)
        process_request.compute_wikidata_recall(ret_triples)


    
    




if __name__ == "__main__":
    fire.Fire(main)