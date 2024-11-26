import fire
from .request import Request
from .process_request import ProcessRequest


def main(
        wikidata_triples_file_path:str,
        model_name:str,
        seed: str,      
):

    process_request = ProcessRequest(model_name, wikidata_triples_file_path, seed)
    ret_triples = process_request.fact_verify_wikidata_triples()
    ret_triples_with_snippet = process_request.query_snippets(ret_triples)
    output_dict = process_request.verify_triples(ret_triples_with_snippet)
    print("output_dict", output_dict)



if __name__ == "__main__":
    fire.Fire(main)