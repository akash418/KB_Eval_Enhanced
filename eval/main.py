import fire
from eval.request import Request
from eval.process_request import ProcessRequest
from eval.wikidata_utils import *


def main(
        wikidata_triples_file_path:str,
        model_name:str,
        seed: str,
        verification_method: str      
):
    valid_methods = ["web", "wikidata"]
    if verification_method not in valid_methods:
        raise ValueError(f"Invalid verification method. Choose from {valid_methods}")
    
    process_request = ProcessRequest(model_name, wikidata_triples_file_path, seed)
    ret_triples = process_request.read_triples_file()

    if verification_method == "web":
        ret_triples_with_snippet = process_request.query_snippets(ret_triples)
        output_dict = process_request.verify_triples(ret_triples_with_snippet)
        print("Output dictionary recording triple verification ... ", output_dict)
    
    if verification_method == "wikidata":
        plausible_triples = soft_match_utils(ret_triples)
        print(f"Fraction of triples plausible: {len(plausible_triples)/len(ret_triples)}")




if __name__ == "__main__":
    fire.Fire(main)