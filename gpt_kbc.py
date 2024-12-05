import json
import time
from pathlib import Path
import os
import random
import openai
import csv 

from loguru import logger
from openai import OpenAI
from openai.types import Batch as OpenAIBatch
from tqdm import tqdm
from prompter_parser import AbstractPrompterParser

class GPTKBCRunner:
    def __init__(self, job_description: str = "Knowledge Elicitation for Wiki data entities", prompter_parser_module: AbstractPrompterParser = None,):
        logger.info('Initialize the GPTKC Runner ..')

        if prompter_parser_module is None:
            raise ValueError("Prompter Parser module is not provided")
        
        self.openai_client = OpenAI()
        self.job_description = job_description
        self.prompter_parser_module = prompter_parser_module

        self.tmp_folder = os.getcwd()
        self.wikidata_entities_file_path = os.getcwd() + "/wikidata_entities.json"
        self.in_progress_file_path = os.getcwd() + "/in_progress.json"
        self.completed_file_path = os.getcwd() + "/completed.json"
        self.result_file_path = os.getcwd() + "/batch_results.jsonl"
        self.batch_request_file_path = os.getcwd() + "/batch_requests.jsonl"
        self.csv_file_path = os.getcwd() + "/wikidata_triples.csv"

    def get_list_of_subjects(self) -> list[str]:
        """
        Read the wikidata entities file and get a list of subjects
        """
        with open(self.wikidata_entities_file_path, 'r') as file:
            json_content = json.load(file)

        all_values = [item for key, values in json_content.items() for item in values]
        random_entities = random.sample(all_values, 3)

        # for now just sample 3 entities
        return all_values

    def loop(self, subjects_to_expand):
        logger.info("Starting the main loop ...")
        
        if os.path.exists(self.in_progress_file_path) and os.path.getsize(self.in_progress_file_path)>0:
            logger.info("...")
            if self.check_batch_status() == True:
                # batch as completed, read the batch
                with open(self.completed_file_path, 'r') as f:
                    data = json.load(f)
                    batch_file_id = data
                    #batch_file_id = data.get("batch_id", None)
            
                self.process_completed_batch(batch_file_id)
            
            else:
                logger.info("Batch is still bring processed ..")

        elif os.path.exists(self.in_progress_file_path) == False and os.path.exists(self.completed_file_path) == False:
            logger.info("Need to submit a new batch")
            self.create_batch(subjects_to_expand)
        
        logger.info('The loop has succesfully finished ...')

    
    def check_batch_status(self):
        """
        Check the current batch status for job subimitted to openai

        returns: True is the batch has been completed (write it to completed records), 
        else False in any other intermediate status
        """
        status_in_progress = ["created", "validating", "in_progress", "finalizing", "parsing"]

        if os.path.exists(self.in_progress_file_path):
            with open(self.in_progress_file_path, "r") as f:
                data = json.load(f)
            
            batch_file_id = data.get("batch_id", None)
            openai_batch = self.openai_client.batches.retrieve(batch_file_id)
            current_status = openai_batch.status
            logger.info(f"Current status of the batch ..{current_status}")
            if current_status == "completed":
                #write the batch id to completed.json
                with open(self.completed_file_path, "w") as f:
                    f.write(json.dumps(batch_file_id) + "\n")
                    return True
            elif current_status in status_in_progress:
                return False


    def process_completed_batch(self, batch_id):
        """
        Input: batch_id that has been completed
        Batch has been completed, read the batch_id and get the data, write the data to csv file
        """
        logger.info(f"Processing a newly completed batch: `{batch_id}`. Downloading results.")
        openai_batch = self.openai_client.batches.retrieve(batch_id)
        input_file_id = openai_batch.input_file_id
        output_file_id = openai_batch.output_file_id
        batch_result = self.openai_client.files.content(output_file_id).content

        with open(self.result_file_path, "wb") as f:
            f.write(batch_result)
        
        raw_triples = []
        with open(self.result_file_path, "r") as f:
            for line in f:
                raw_triples_from_line = []
                try:
                    raw_triples_from_line = self.prompter_parser_module.parse_elicitation_response(line)
                
                except json.JSONDecodeError:
                    logger.error(f"Failed to parse OpenAI response: {line.strip()}")
                
                raw_triples.extend(raw_triples_from_line)
        
        logger.info(f"Found {len(raw_triples):,} raw triples in the batch results.")
        print("raw_triples", raw_triples)
        self.write_triples_to_csv(raw_triples)

    
    def write_triples_to_csv(self, raw_triples):
        """
        Write the raw triples to the csv file for further processing
        """
        try:
            with open(self.csv_file_path, mode = 'w', newline='', encoding = 'utf-8') as csv_file:
                fieldnames = ["subject", "predicate", "object", "subject_name"]
                writer = csv.DictWriter(csv_file, fieldnames=fieldnames)
                writer.writeheader()
                writer.writerows(raw_triples)
                logger.info("Data written to CSV succesfully ...")

        except Exception as e:
            print("An error occured: {e}")


    def create_batch(self, subjects_to_expand = list[str], max_tries:int=5):
        """
        Push the data to a batch request for openai
        Write the in progress batch id to a json file for recording
        """
        batch_request = []
        for subject in subjects_to_expand:
            req = self.prompter_parser_module.get_elicitation_prompt(subject_name=subject)
            batch_request.append(req)

        with open(self.batch_request_file_path, "w") as f:
            for obj in batch_request:
                f.write(json.dumps(obj) + "\n")
        
        batch_input_file = self.openai_client.files.create(
            file=open(self.batch_request_file_path, "rb"),
            purpose="batch"
        )

        batch_input_file_id = batch_input_file.id
        openai_batch = None
        for num_tries in range(max_tries):
            try:
                # create batch
                openai_batch = self.openai_client.batches.create(
                    input_file_id=batch_input_file_id,
                    endpoint="/v1/chat/completions",
                    completion_window="24h",
                    metadata={
                        "description": self.job_description
                    }
                )
                logger.info(
                    f"Batch file created successfully. Batch ID: `{openai_batch.id}`.")
                break
            except openai.RateLimitError as e:
                logger.error(f"Rate limit error: {e}")
                logger.info("Waiting for 60 seconds before retrying.")
                time.sleep(60)
                continue

        if openai_batch is None:
            raise Exception(
                f"Failed to create batch file after {max_tries} attempts.")
        
        data = {"batch_id": openai_batch.id}

        with open(self.in_progress_file_path, "w") as f:
            json.dump(data, f)
        
        logger.info("Batch ID recored at in_progress.json")
        