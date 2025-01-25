import json
import time
from pathlib import Path
import os
import random
import openai
import csv 
import shutil
from loguru import logger
from openai import OpenAI
from openai.types import Batch as OpenAIBatch
from tqdm import tqdm
from prompter_parser import AbstractPrompterParser

class GPTKBCRunner:
    def __init__(
            self,
            curr_index: int,                # current index needed while submitting the batch request 
            wikidata_entities_file_path:str,
            wikidata_triples_dir:str,  
            job_description: str = "Knowledge Elicitation for Wiki data entities", 
            prompter_parser_module: AbstractPrompterParser = None,
            job_type: str = "verify",
        ):

        """
        Main arguments for GPTKBC runner class

        Arguments:
            curr_index (int): Index used for identifying the current prompt file
            wikidata_entities_file_path (str): File path for handpicked wikidata entities
            wikidata_triples_dir (str): Dir path for storing the elicited triples
            job_description (str): String based description of the current job
            prompter_parser_module: Abstract prompter parser class object
            job_type (str): String type to indicate if its a submit job or verify job

        
        """

        logger.info('Initialize the GPTKC Runner ..')

        if prompter_parser_module is None:
            raise ValueError("Prompter Parser module is not provided")
        
        self.openai_client = OpenAI()
        self.job_description = job_description
        self.prompter_parser_module = prompter_parser_module
        self.job_type = job_type
        self.curr_index = curr_index

        self.tmp_folder = os.getcwd()
        self.wikidata_entities_file_path = wikidata_entities_file_path

        self.in_progress_dir_path = os.getcwd() + "/progress_dir/"
        self.completed_dir_path = os.getcwd() + "/completed_dir/"
        self.batch_results_dir = os.getcwd() + "/results_dir/"
        self.batch_request_dir = os.getcwd() + "/batch_request/"
        self.csv_dir_path = wikidata_triples_dir

        #self.in_progress_file_path = os.getcwd() + "/in_progress.json"
        #self.completed_file_path = os.getcwd() + "/completed.json"
        #self.result_file_path = os.getcwd() + "/batch_results.jsonl"

        # file path used for storing temporary batch json objects until they are submitted
        self.batch_record_file_path = os.getcwd() + "/batch_records.jsonl"
        #self.csv_file_path = wikidata_triples_file_path

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

    # not being used right now (replaced by new one)
    """
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
    """
    

    def loop(self, subjects_to_expand):
        """
        Main loop to handle job submission or verification based on the job type.
        """
        logger.info("Starting the main loop ...")

        if self.job_type == "submit":
            logger.info("Job type is 'submit'. Submitting a new batch directly.")
            self.create_batch_dir(subjects_to_expand)

            if os.path.exists(self.in_progress_dir_path) and os.path.getsize(self.in_progress_dir_path) > 0:
                logger.info("In-progress file exists. Checking batch status...")

                if self.check_batch_status_dir() == True:
                    # Batch has completed, read the batch
                    for file_name in os.listdir(self.completed_dir_path):
                        completed_file_path = os.path.join(self.completed_dir_path, file_name)
                        with open(completed_file_path, 'r') as f:
                            data = json.load(f)
                            batch_file_id = data.get('batch_id')

                        self.process_completed_batch(batch_file_id)
                else:
                    logger.info("Batch is still being processed...")

            elif not os.path.exists(self.in_progress_dir_path) and not os.path.exists(self.completed_dir_path):
                logger.info("No in-progress or completed file found. Submitting a new batch...")
                self.create_batch_dir(subjects_to_expand)

        elif self.job_type == "verify":
            logger.info("Job type is 'verify'. Processing completed batches...")
            for file_name in os.listdir(self.completed_dir_path):
                completed_file_path = os.path.join(self.completed_dir_path, file_name)
                with open(completed_file_path, 'r') as f:
                    data = json.load(f)
                    batch_file_id = data.get('batch_id')

                self.process_completed_batch(batch_file_id)


    # replaced by new method 
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


    # replaced by new method
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
            for line_number, line in enumerate(f, start=1):
                try:
                    raw_triples_from_line = self.prompter_parser_module.parse_elicitation_response(line)
                    raw_triples.extend(raw_triples_from_line)
                except json.JSONDecodeError:
                    logger.error(f"JSONDecodeError at line {line_number}: {line.strip()}")
                except Exception as e:
                    logger.error(f"Unexpected error while parsing line {line_number}: {line.strip()} | Error: {e}")
    
        logger.info(f"Found {len(raw_triples):,} raw triples in the batch results.")
        print("raw_triples", raw_triples)

        self.write_triples_to_csv(raw_triples)


    def process_completed_batch_dir(self, batch_id):
        """
        Input: batch_id that has been completed.
        Processes the completed batch by downloading results, writing them to the batch_results_dir,
        and saving the parsed triples to a CSV file.
        """
        logger.info(f"Processing a newly completed batch: `{batch_id}`. Downloading results.")

        # Retrieve batch details and results
        openai_batch = self.openai_client.batches.retrieve(batch_id)
        input_file_id = openai_batch.input_file_id
        output_file_id = openai_batch.output_file_id
        batch_result = self.openai_client.files.content(output_file_id).content

        # Ensure the batch results directory exists
        os.makedirs(self.batch_results_dir, exist_ok=True)

        # Write batch results to the batch_results_dir
        result_file_path = os.path.join(self.batch_results_dir, f"batch_results_{self.curr_index}.json")
        with open(result_file_path, "wb") as f:
            f.write(batch_result)
        logger.info(f"Batch results written to `{result_file_path}`.")

        # Read the results and process triples
        raw_triples = []
        with open(result_file_path, "r") as f:
            for line_number, line in enumerate(f, start=1):
                try:
                    # Parse elicitation responses
                    raw_triples_from_line = self.prompter_parser_module.parse_elicitation_response(line)
                    raw_triples.extend(raw_triples_from_line)
                except json.JSONDecodeError:
                    logger.error(f"JSONDecodeError at line {line_number}: {line.strip()}")
                except Exception as e:
                    logger.error(f"Unexpected error while parsing line {line_number}: {line.strip()} | Error: {e}")

        logger.info(f"Found {len(raw_triples):,} raw triples in the batch results.")

        if not os.path.exists(self.csv_dir_path):
            os.makedirs(self.csv_dir_path)

        # Define the CSV filename
        csv_filename = os.path.join(self.csv_dir_path, f"wikidata_triples_{self.curr_index}.csv")

        # Write the triples to a CSV file
        self.write_triples_to_csv(raw_triples, csv_filename)
        logger.info(f"Raw triples written to `{csv_filename}`.")


    
    def write_triples_to_csv(self, raw_triples, input_file_path):
        """
        Write the raw triples to the csv file for further processing
        """
        try:
            with open(input_file_path, mode = 'w', newline='', encoding = 'utf-8') as csv_file:
                fieldnames = ["subject", "predicate", "object", "subject_name"]
                writer = csv.DictWriter(csv_file, fieldnames=fieldnames)
                writer.writeheader()
                writer.writerows(raw_triples)
                logger.info("Data written to CSV succesfully ...")

        except Exception as e:
            print("An error occured: {e}")

    # replaced by new method
    def create_batch(self, subjects_to_expand = list[str], max_tries:int=5):
        """
        Push the data to a batch request for openai
        Write the in progress batch id to a json file for recording
        """
        batch_request = []
        for subject in subjects_to_expand:
            req = self.prompter_parser_module.get_elicitation_prompt(subject_name=subject)
            batch_request.append(req)

        with open(self.batch_record_file_path, "w") as f:
            for obj in batch_request:
                f.write(json.dumps(obj) + "\n")
        
        batch_input_file = self.openai_client.files.create(
            file=open(self.batch_record_file_path, "rb"),
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
        

    def create_batch_dir(self, subjects_to_expand: list[str], max_tries: int = 5):
        """
        Push the data to a batch request for OpenAI.
        Write the in-progress batch ID to a JSON file for recording in `self.in_progress_dir_path`
        with a filename format `in_progress_<self.curr_index>.json`.
        """
        batch_request = []
        
        # Generate batch request data
        for subject in subjects_to_expand:
            req = self.prompter_parser_module.get_elicitation_prompt(subject_name=subject)
            batch_request.append(req)

        # Write batch request data to a temporary file
        with open(self.batch_record_file_path, "w") as f:
            for obj in batch_request:
                f.write(json.dumps(obj) + "\n")

        # Upload the batch request file to OpenAI
        batch_input_file = self.openai_client.files.create(
            file=open(self.batch_record_file_path, "rb"),
            purpose="batch"
        )
        batch_input_file_id = batch_input_file.id

        openai_batch = None
        for num_tries in range(max_tries):
            try:
                # Create batch
                openai_batch = self.openai_client.batches.create(
                    input_file_id=batch_input_file_id,
                    endpoint="/v1/chat/completions",
                    completion_window="24h",
                    metadata={
                        "description": self.job_description
                    }
                )
                logger.info(f"Batch file created successfully. Batch ID: `{openai_batch.id}`.")
                break
            except openai.RateLimitError as e:
                logger.error(f"Rate limit error: {e}")
                logger.info("Waiting for 60 seconds before retrying.")
                time.sleep(60)
                continue

        if openai_batch is None:
            raise Exception(f"Failed to create batch file after {max_tries} attempts.")

        # Prepare data for writing to the in-progress directory
        data = {"batch_id": openai_batch.id}

        # Create the in-progress directory if it doesn't exist
        os.makedirs(self.in_progress_dir_path, exist_ok=True)

        # Determine the filename for the current batch
        in_progress_file_path = os.path.join(
            self.in_progress_dir_path,
            f"in_progress_{self.curr_index}.json"
        )

        # Write batch ID to the in-progress file
        with open(in_progress_file_path, "w") as f:
            json.dump(data, f)

        logger.info(f"Batch ID recorded at {in_progress_file_path}")


    def check_batch_status_dir(self):
        """
        Check the current batch status for jobs submitted to OpenAI.
        
        Moves completed files from the in-progress directory to the completed directory while preserving
        the numbered index of the filenames. Returns True if at least one batch has been completed, 
        otherwise False.
        """
        status_in_progress = ["created", "validating", "in_progress", "finalizing", "parsing"]
        any_completed = False

        # Ensure the in-progress directory exists
        if os.path.exists(self.in_progress_dir_path):
            # Iterate over all files in the in-progress directory
            for file_name in os.listdir(self.in_progress_dir_path):
                if file_name.endswith(".json") and file_name.startswith("in_progress_"):
                    file_path = os.path.join(self.in_progress_dir_path, file_name)
                    
                    # Read the JSON file
                    with open(file_path, "r") as f:
                        data = json.load(f)
                    
                    batch_file_id = data.get("batch_id", None)
                    openai_batch = self.openai_client.batches.retrieve(batch_file_id)
                    current_status = openai_batch.status
                    
                    logger.info(f"Current status of batch {batch_file_id} in {file_name}: {current_status}")
                    
                    # Check if the status is completed
                    if current_status == "completed":
                        # Determine the new filename for the completed directory
                        completed_file_name = file_name.replace("in_progress_", "completed_")
                        completed_file_path = os.path.join(self.completed_dir_path, completed_file_name)

                        # Move the file to the completed directory
                        shutil.move(file_path, completed_file_path)
                        logger.info(f"Moved {file_name} to {completed_file_path}")
                        any_completed = True

                    elif current_status in status_in_progress:
                        logger.info(f"Batch {batch_file_id} in {file_name} is still in progress.")
                    else:
                        logger.warning(f"Unexpected status {current_status} for batch {batch_file_id} in {file_name}.")

        return any_completed
