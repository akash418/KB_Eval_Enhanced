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
from tqdm import tqdm

from request import Request
from wikidata_utils import *

class ProcessRequest:
    def __init__(self, 
                model_name, 
                wikidata_triples_file_path,
                wikidata_entities_file_path, 
                seed, 
                sampling
        ):


        self.client = OpenAI()

        # directory to store the snippets downloaded from the search query
        self.snippet_dir = os.getcwd() + "snippets/"
        self.wikidata_triples_file_path = wikidata_triples_file_path
        self.wikidata_entities_file_path = wikidata_entities_file_path
        self.gold_triples_file_path = os.getcwd() + "/gold.json"
        self.seed = seed
        self.model_name = model_name
        self.sampling = sampling
        self.sample_size = 10 if sampling == True else 0


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
                #print('output ...', output)
                results = self.parse_lm_output(each_triple, results, output)
            
            else:
                results['noSnippet'].append(each_triple)
        
        return results
            

    def parse_lm_output(self, current_triple, results, output):
        """
        Parse the lm output to decide, true, plausible, false for the current triple
        """

        if output.startswith("a"):
            results['a'].append(current_triple)
        elif output.startswith("b"):
            results['b'].append(current_triple)
        elif output.startswith("c"):
            results['c'].append(current_triple)
        elif output.startswith("d"):
            results['d'].append(current_triple)
        else:
            logger.info('Results fall into some other category ...')
        
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
        #return randomized_triples
        return raw_triples
    
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
        Approach: Iterate over all triples, get wikidata triples and ask LLM as judge if model generated
        triples entail or are plausible given wikidata triples
        """
        request = Request(self.model_name)
        results = {"a":[], "b":[], "c":[], "d":[]}
        
        if self.sampling:
            raw_triples = random.sample(raw_triples, self.sample_size)


        for each_triple in tqdm(raw_triples, desc = "Computing Precision ..."):
            wikidata_triples = self.read_gold_triples_file()
            wikidata_triples_curr_subject = wikidata_triples[each_triple['subject']]
            wikidata_triples_curr_subject_str = ' '
            for each_subj_triple in wikidata_triples_curr_subject:
                wikidata_triples_curr_subject_str+= '(' + each_subj_triple['subject'] + each_subj_triple['predicate'] +  each_subj_triple['object'] + ')' + ','


            #all_triples_wikidata_str = ", ".join(all_triples_wikidata)

            each_triple_str = f"({each_triple['subject'].replace('_', ' ')}, {each_triple['predicate'].replace('_', ' ')}, {each_triple['object'].replace('_', ' ')})"
            output = request.verify_triple_lm_wikidata(each_triple_str, wikidata_triples_curr_subject_str)
            #print("output", output)
            results = self.parse_lm_output(each_triple_str, results, output)
        

        print("Precision results ....")
        print("Total # triples", len(raw_triples))
        print("Fraction of triples true", len(results['a'])/len(raw_triples))
        print("Fraction of triples plausible", len(results['b'])/len(raw_triples))    
        print("Fraction of triples implausble", len(results['c'])/len(raw_triples))
        print("Fraction of triples false", len(results['d'])/len(raw_triples))
        print(results)
        
        self.entity_based_stats(raw_triples, results)

    def subject_based_lookup(self, current_subject, raw_triples):

        """
        Select all the triples for a given subject from the list of raw triples
        """
        subject_list_triple = []
        for each_triple in raw_triples:
            if each_triple['subject'] == current_subject:
                each_triple_str = f"({current_subject}, {each_triple['predicate']}, {each_triple['object']})"
                subject_list_triple.append(each_triple_str)

        
        return subject_list_triple

    def entity_based_stats(self, raw_triples, results):

        """
        Process some entity wise statistics
        """

        # dict for recording subject to count of a,b,c ... (true, plausible, implausible, false) etc
        subject_to_key_counts = {}

        for key, triples in results.items():
            for triple in triples:
                
                triple_split = triple.strip("()").split(", ")
                if len(triple_split) != 3:
                    print(f"Skipping invalid triple: {triple}")
                    continue

                subject,b,c = triple_split
                
                # Initialize nested dictionary for the subject if it doesn't exist
                if subject not in subject_to_key_counts:
                    subject_to_key_counts[subject] = {}
                
                # Increment the count for the current key
                if key not in subject_to_key_counts[subject]:
                    subject_to_key_counts[subject][key] = 0
                subject_to_key_counts[subject][key] += 1

        print(subject_to_key_counts)
        subjects_true_or_plausible = []
        subjects_false_or_implausible = []

        for subject, freq_count in subject_to_key_counts.items():
            if "a" not in freq_count and "b" not in freq_count:
                if "c" in freq_count or "d" in freq_count:
                    subjects_false_or_implausible.append(subject)
            

            if "a" in freq_count or "b" in freq_count:
                if "c" not in freq_count and "d" not in freq_count:
                    subjects_true_or_plausible.append(subject)
        

        print("Subjects true or plausible ...", subjects_true_or_plausible)
        print("count subjects true or plausible ..", len(subjects_true_or_plausible))
        print("\n")
        print("Subjects false or implausible ...", subjects_false_or_implausible)
        print("Subjects false or implausible  ...", len(subjects_false_or_implausible))


    def read_gold_triples_file(self):

        with open(self.gold_triples_file_path, "r") as json_file:
            wikidata_triples = json.load(json_file)
        
        return wikidata_triples


    def compute_wikidata_recall(self, raw_triples):
        """
        Approach: Iterate over all wikidata generated triples for entities and ask LLM as a judge if wikidata generated
        triples entail or plausible given model generated triples
        """
        fact_count = dict()
        request = Request(self.model_name)
        results = {"a":[], "b":[], "c":[], "d":[]}

        # dict for recording wikidata facts per subject
        wikidata_facts_per_subject = dict()

        for each_triple in raw_triples:
            if each_triple['subject'] in fact_count:
                fact_count[each_triple['subject']]+=1
            else:
                fact_count[each_triple['subject']] = 1
                wikidata_triples = self.read_gold_triples_file()
                wikidata_facts_per_subject[each_triple['subject']] = wikidata_triples[each_triple['subject']]
        

        print('Yield ...')
        total_facts = sum(fact_count.values())
        num_subjects = len(fact_count)
        print(f"Average count of facts per subject in the sample set: {total_facts/num_subjects}")

        all_wikidata_facts = [item for value_list in wikidata_facts_per_subject.values() for item in value_list]

        if self.sampling:
            all_wikidata_facts = random.sample(all_wikidata_facts, self.sample_size)


        for each_wikidata_fact in tqdm(all_wikidata_facts, desc = "Computing Recall ..."):
            subject_based_facts = self.subject_based_lookup(each_wikidata_fact['subject'], raw_triples)
            subject_based_facts_str = ", ".join(subject_based_facts)
            each_triple_str = f"({each_wikidata_fact['subject']}, {each_wikidata_fact['predicate']}, {each_wikidata_fact['object']})"
            output = request.verify_triple_lm_wikidata(each_triple_str, subject_based_facts_str)
            results = self.parse_lm_output(each_triple_str, results, output)


        print("Recall results ....")
        print("Total # triples", len(all_wikidata_facts))
        print("Fraction of triples true", len(results['a'])/len(all_wikidata_facts))
        print("Fraction of triples plausible", len(results['b'])/len(all_wikidata_facts))    
        print("Fraction of triples implausble", len(results['c'])/len(all_wikidata_facts))
        print("Fraction of triples false", len(results['d'])/len(all_wikidata_facts))
        print(results)

        self.entity_based_stats(raw_triples, results)


        
