import fire
from request import Request
from process_request import ProcessRequest
from wikidata_utils import *


def main(
        wikidata_triples_file_path:str,
        model_name:str,
        seed: str,      
):

    process_request = ProcessRequest(model_name, wikidata_triples_file_path, seed)
    ret_triples = process_request.read_triples_file()
    #ret_triples_with_snippet = process_request.query_snippets(ret_triples)
    #output_dict = process_request.verify_triples(ret_triples_with_snippet)
    #print("output_dict", output_dict)

    plausible_claims = soft_match_utils(ret_triples)



if __name__ == "__main__":
    fire.Fire(main)