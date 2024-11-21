import json
import time
from pathlib import Path
import os
import random
import openai
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
        
        self.openai_client = OpenAI(api_key = "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")
        self.job_description = job_description
        self.tmp_folder = os.getcwd()
        self.wikidata_entities_file_path = os.getcwd() + "/wikidata_entities.json"

    def get_list_of_subjects(self) -> list[str]:
        """
        Read the wikidata entities file and get a list of subjects
        """
        with open(self.wikidata_entities_file_path, 'r') as file:
            json_content = json.load(file)

        all_values = [item for key, values in json_content.items() for item in values]
        random_entities = random.sample(all_values, 3)
        # for now just sample 3 entities
        return random_entities

    def loop(self, subjects_to_expand):
        logger.info("Starting the main loop ...")
        in_progress_file_path = self.tmp_folder / "in_progress.json"
        completed_file_path = self.tmp_folder / "completed.json"

        if os.path.exists(in_progress_file_path) and os.path.getsize(in_progress_file_path)>0:
            logger.info("...")
            if self.check_batch_status == True:
                # batch as completed, read the batch
                with open(completed_file_path, 'r') as f:
                    data = json.loads(f)
                    batch_file_id = data.get("batch_file_id", None)
            
                self.process_completed_batch(batch_file_id)
            
            else:
                logger.info("Batch is still bring processed ..")

        elif os.path.exists(in_progress_file_path) == False and os.path.exists(completed_file_path) == False:
            logger.info("Need to submit a new batch")
            self.create_batch(subjects_to_expand)

    
    def check_batch_status(self):
        """
        Check the current batch status for job subimitted to openai

        returns: True is the batch has been completed (write it to completed records), 
        else False in any other intermediate status
        """
        status_in_progress = ["created", "validating", "in_progress", "finalizing", "parsing"]

        #read the in_progress file ID to get the batch id submitted to openai
        in_progress_file_path = self.tmp_folder / "in_progress.json"
        completed_file_path = self.tmp_folder / "completed.json"

        if os.path.exists(in_progress_file_path):
            with open(in_progress_file_path, "r") as f:
                data = json.loads(f)
            
            batch_file_id = data.get("batch_file_id", None)
            openai_batch = self.openai_client.batches.retrieve(batch_file_id)
            current_status = openai_batch.status
            if current_status == "completed":
                #write the batch id to completed.json
                with open(completed_file_path, "w") as f:
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

        result_file_path = self.tmp_folder/"batch_results.jsonl"
        with open(result_file_path, "wb") as f:
            f.write(batch_result)
        
        raw_triples = []
        with open(result_file_path, "r") as f:
            for line in f:
                raw_triples_from_line = []
                try:
                    raw_triples_from_line = self.prompter_parser_module.parse_elicitation_response(line)
                
                except json.JSONDecodeError:
                    logger.error(f"Failed to parse OpenAI response: {line.strip()}")
                
                raw_triples.extend(raw_triples_from_line)
        
        logger.info(f"Found {len(raw_triples):,} raw triples in the batch results.")
        print("raw_triples", raw_triples)



    def create_batch(self, subjects_to_expand = list[str], max_tries:int=5):
        """
        Push the data to a batch request for openai
        Write the in progress batch id to a json file for recording
        """
        batch_request = []
        for subject in subjects_to_expand:
            req = self.prompter_parser_module.get_elicitation_prompt(subject_name=subject)
            batch_request.append(req)

        with open(self.tmp_folder/"batch_requests.jsonl", "w") as f:
            for obj in batch_request:
                f.write(json.dumps(obj) + "\n")
        
        batch_input_file = self.openai_client.files.create(
            file=open(self.tmp_folder / "batch_requests.jsonl", "rb"),
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
        
        data = {"batch_file_id": "your_batch_file_id_here"}

        with open(self.tmp_folder / "in_progress.json", "w") as f:
            json.dump(data, f)
        
        logger.info("Batch ID recored at in_progress.json")
        