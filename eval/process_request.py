import os
import time
import sys
import pickle
import random
from openai import OpenAI
import json
import pandas as pd
import requests
from loguru import logger
import csv

from request import Request
from wikidata_utils import *

class ProcessRequest:
    def __init__(self, model_name, wikidata_triples_file_path, seed):
        self.client = OpenAI()

        # directory to store the snippets downloaded from the search query
        self.snippet_dir = os.getcwd() + "snippets/"
        self.wikidata_triples_file_path = wikidata_triples_file_path
        self.wikidata_entities_file_path = os.getcwd() + "/wikidata_entities.json"
        self.seed = seed
        self.model_name = model_name


    def verify_triples(self, raw_triples):

        """
        Process raw triples, verify from language model, as to which of the four categories the response falls into
        
        """
        request = Request(self.model_name)

        # this dict just stores results which fall into either of categories (a, b, c, d) --> see content in verify_triples, Request class
        results = {"a":[], "b":[], "c":[], "d":[], "noSnippet": []}
        for each_triple in raw_triples:
            if len(each_triple['snippet']) > 0:
                each_triple_str = f"({each_triple['subject'].replace('_', ' ')}, {each_triple['predicate'].replace('_', ' ')}, {each_triple['object'].replace('_', ' ')})"
                #print('each_triple_str', each_triple_str)

                snippet_str = ""
                for each_snippet in each_triple['snippet']:
                    snippet_str += each_snippet
                    snippet_str += " | "
                
                output = request.verify_triple_language_model(each_triple_str, snippet_str)
                print('output ...', output)

                if output.startswith("a"):
                    results['a'].append(each_triple)
                elif output.startswith("b"):
                    results['b'].append(each_triple)
                elif output.startswith("c"):
                    results['c'].append(each_triple)
                elif output.startswith("d"):
                    results['d'].append(each_triple)
                else:
                    logger.info('Results fall into some other category ...')
            
            else:
                results['noSnippet'].append(each_triple)
        

        return results
            

    def read_triples_file(self):
        """
        Read the wikidata triples file, get some random ones (if needed) and 
        """
        raw_triples = []
        with open(self.wikidata_triples_file_path, mode='r', newline='', encoding='utf-8') as f:
            csv_reader = csv.DictReader(f)
            for row in csv_reader:
                raw_triples.append(row)
        
        randomized_triples = random.sample(raw_triples, 10)
        return randomized_triples
    
    def get_triples_statistics(self, raw_triples):
        """
        Read the wikidata triples file and get some basic stastics
        """

        unique_subjects = set(entry["subject"] for entry in raw_triples)
        print("Unique Subjects:", unique_subjects)


    def query_snippets(self, raw_triples):
        """
        Process raw triples, make the query to the search engine and get the snippets
        Wait for 2 seconds before making a new query (using free subscription for now that it requires min 1 sec wait time)
        """
        for each_triple in raw_triples:
            returned_snippet = self.get_brave_results(each_triple['subject'].replace("_", " ") + " " + each_triple['object'].replace("_", " "))
            # get the snippet returned by api search call and add a new key to the triple dict
            each_triple['snippet'] = returned_snippet
            time.sleep(2)

        if not os.path.exists(self.snippet_dir):
            os.makedirs(self.snippet_dir)
            print(f"Directory created: {self.snippet_dir}")
        else:
            print(f"Directory already exists: {self.snippet_dir}")

        file_path = os.path.join(self.snippet_dir, f"{self.seed}.pkl")

        with open(file_path, "wb") as f:
            pickle.dump(raw_triples, f)
        
        return raw_triples

    def get_brave_results(self, search_term):
        
        """
        Hit the brave web search API given a search term, get the response and return the snippets
        """

        logger.info(f"Processing the search query .. {search_term}")
        url = "https://api.search.brave.com/res/v1/web/search"
        headers = {
            "Accept": "application/json",
            "Accept-Encoding": "gzip",
            "X-Subscription-Token": os.getenv("BRAVE_SUBSCRIPTION_TOKEN", "")
        }

        params = {
            "q": search_term,
        }
        response = requests.get(url, headers = headers, params = params)
        data = response.json()

        # dict_keys(['query', 'mixed', 'type', 'web'])
        snippets = []
        try:
            for item in data['web']['results'][:5]:
                snippets.append(item['description'])
        except Exception as e:
            print(e)
            logger.info(f"parsing error ... {data}")
        
        return snippets


    def compute_wikidata_precision(self, raw_triples):
        """
        Approach: Iterate over all triples, get wikidata facts and ask LLM as judge if model generated
        triples entail or are plausible
        """
        request = Request(self.model_name)

        for each_triple in raw_triples:
            subject_entity_id = get_wikidata_entity_id(each_triple['subject'])
            wikidata_claims = fetch_wikidata_claims(subject_entity_id)
            all_triples_wikidata = convert_wikidata_claims_to_triples(wikidata_claims, each_triple['subject'])
            all_triples_wikidata_str = ", ".join(all_triples_wikidata)
            each_triple_str = f"({each_triple['subject'].replace('_', ' ')}, {each_triple['predicate'].replace('_', ' ')}, {each_triple['object'].replace('_', ' ')})"
            output = request.verify_triple_lm_wikidata(each_triple_str, all_triples_wikidata_str)
            print("output", output)
