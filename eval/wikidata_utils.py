import requests
from tqdm import tqdm 
import torch
from sentence_transformers import SentenceTransformer, util
from loguru import logger
import json

"""

py file containing helper methods for fetching data from wikidata for entities
"""

def get_wikidata_entity_id(entity_name, language = 'en'):

    """
    Fetches the Wikidata entity ID for a given entity string.
    
    Args:
        entity_name (str): The name of the entity to search for.
        language (str): The language of the entity (default is "en").
    
    Returns:
        str: The Wikidata entity ID (e.g., "Q937") or None if not found.
    """

    url = "https://www.wikidata.org/w/api.php"
    params = {
        "action": "wbsearchentities",
        "search": entity_name,
        "language": language,
        "format": "json"
    }

    response = requests.get(url, params=params)
    
    if response.status_code == 200:
        results = response.json().get("search", [])
        if results:
            # Return the first matching entity ID
            return results[0].get("id")
        else:
            logger.info(f"No matches found for entity: {entity_name}")
            return None
    else:
        logger.info(f"Failed to fetch data. HTTP Status Code: {response.status_code}")
        return None


def sanity_check_entity(entity_name, language = 'en'):
    """
    Given an entity string check if it exists on wikidata
    """

    if get_wikidata_entity_id(entity_name)!= None:
        return True
    else:
        return False


def fetch_wikidata_claims(entity_id):
    """
    Fetches properties for claims given a Wikidata entity using its ID.
    """
    url = f"https://www.wikidata.org/wiki/Special:EntityData/{entity_id}.json"
    response = requests.get(url)
    if response.status_code != 200:
        raise Exception(f"Failed to fetch entity data for {entity_id}")
    data = response.json()
    claims = data['entities'][entity_id]['claims']
    properties = {}
    for prop, values in claims.items():
        properties[prop] = [v['mainsnak']['datavalue']['value'] for v in values if 'datavalue' in v['mainsnak']]

    return properties


def get_wikidata_entity_name(entity_id, language="en"):
    """
    Fetches the name (label) of a Wikidata entity given its ID.
    
    Args:
        entity_id (str): The Wikidata entity ID (e.g., "Q42").
        language (str): The language code for the label (default is "en").
    
    Returns:
        str: The name (label) of the entity or None if not found.
    """
    url = "https://www.wikidata.org/w/api.php"
    params = {
        "action": "wbgetentities",
        "ids": entity_id,
        "languages": language,
        "props": "labels",
        "format": "json"
    }
    
    response = requests.get(url, params=params)
    
    if response.status_code == 200:
        data = response.json()
        entities = data.get("entities", {})
        if entity_id in entities:
            labels = entities[entity_id].get("labels", {})
            if language in labels:
                return labels[language].get("value")
        logger.info(f"No label found for entity ID: {entity_id}")
        return None
    else:
        logger.info(f"Failed to fetch data. HTTP Status Code: {response.status_code}")
        return None



def get_wikidata_property_label(property_id, language="en"):
    """
    Fetches the label of a Wikidata property given its ID.
    
    Args:
        property_id (str): The Wikidata property ID (e.g., "P31").
        language (str): The language code for the label (default is "en").
    
    Returns:
        str: The label of the property or None if not found.
    """
    url = "https://www.wikidata.org/w/api.php"
    params = {
        "action": "wbgetentities",
        "ids": property_id,
        "languages": language,
        "props": "labels",
        "format": "json"
    }
    
    response = requests.get(url, params=params)
    
    if response.status_code == 200:
        data = response.json()
        entities = data.get("entities", {})
        if property_id in entities:
            labels = entities[property_id].get("labels", {})
            if language in labels:
                return labels[language].get("value")
        logger.info(f"No label found for property ID: {property_id}")
        return None
    else:
        logger.info(f"Failed to fetch data. HTTP Status Code: {response.status_code}")
        return None


def convert_wikidata_claims_to_triples(wikidata_claims, current_subject, exp_output_type = 'str'):
    all_triple_wikidata_claims = []
    for prop, values in tqdm(wikidata_claims.items(), desc = "Matching triples"):
        for value in values:
            if type(value) == dict:
                prop_label = get_wikidata_property_label(prop)
                if 'id' in value:
                    referred_entity = get_wikidata_entity_name(value['id'])
                    if prop_label!=None and referred_entity!=None:
                        #curr_wikidata_claim_triple = [current_subject, prop_label, referred_entity]
                        curr_wikidata_claim_triple = {'subject': current_subject, 'predicate': prop_label, 'object': referred_entity}
                        curr_wikidata_claim_string = f"({current_subject}, {prop_label}, {referred_entity})"
                        if exp_output_type == 'str':
                            all_triple_wikidata_claims.append(curr_wikidata_claim_string)
                        else:
                            all_triple_wikidata_claims.append(curr_wikidata_claim_triple)

    
    return all_triple_wikidata_claims



def soft_match_triples_with_claims(current_triple, wikidata_claims, threshold_score = 0.8):
    """
    Matches a list of triples with Wikidata claims using semantic similarity.
    If the asked triple matches if any of the wikidata claims then it can be considered plausible
    return True else False

    """
    device = torch.device("cuda" if torch.cuda.is_available() else "cpu") 
    model = SentenceTransformer('all-MiniLM-L6-v2').to(device)
    triple_texts = [f"{current_triple['subject']} {current_triple['predicate']} {current_triple['object']}"]
    triple_embeddings = model.encode(triple_texts, convert_to_tensor=True, device = device)

    # variable for storing all wikidata claims converted to triple format
    all_triple_wikidata_claims = []

    for prop, values in tqdm(wikidata_claims.items(), desc = "Matching triples"):
        for value in values:
            if type(value) == dict:
                prop_label = get_wikidata_property_label(prop)
                if 'id' in value:
                    referred_entity = get_wikidata_entity_name(value['id'])
                    if prop_label!=None and referred_entity!=None:
                        curr_wikidata_claim_triple = [current_triple['subject'], prop_label, referred_entity]
                        curr_wikidata_claim_string = f"{current_triple['subject']} {prop_label} {referred_entity}"
                        all_triple_wikidata_claims.append(curr_wikidata_claim_string)
    

    claim_embedding = model.encode(all_triple_wikidata_claims, convert_to_tensor=True, device = device)
    similarities = util.pytorch_cos_sim(triple_embeddings, claim_embedding)

    # record indices for matching triples semantically
    indices = (similarities > threshold_score).nonzero(as_tuple=True)
    values = similarities[indices]

    if len(values) > 0:
        return True
    
    return False


def soft_match_utils(raw_triples):
    """
    Perform soft matching for triples generated with elicitation prompt on claims scraped from wikidata
    """ 

    # list recording plausible claims 
    plausible_triples = []

    for each_triple in raw_triples:
        subject_entity_id = get_wikidata_entity_id(each_triple['subject'])
        wikidata_collection_claims = fetch_wikidata_claims(subject_entity_id)
        if soft_match_triples_with_claims(each_triple, wikidata_collection_claims) == True:
            plausible_triples.append(each_triple)
    

    print(f"Collection of plausible triples: {plausible_triples}")
    return plausible_triples


def create_gold_triples_file(raw_triples, gold_file_path):

    """
    Create gold triples file so that every time eval framework is used, web api lookup can be prevented
    """
    
    gold_triples = dict()
    for each_triple in raw_triples:
        if each_triple['subject'] not in gold_triples:
            subject_entity_id = get_wikidata_entity_id(each_triple['subject'])
            if subject_entity_id is not None:
                wikidata_claims = fetch_wikidata_claims(subject_entity_id)
                all_triples_wikidata = convert_wikidata_claims_to_triples(wikidata_claims, each_triple['subject'], 'dict')
                gold_triples[each_triple['subject']] = all_triples_wikidata
    
    with open(gold_file_path, "w") as json_file:
        json.dump(gold_triples, json_file, indent=4)

    print(f"Data has been written to {gold_file_path}")

