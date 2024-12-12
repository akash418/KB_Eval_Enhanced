import fire
from gpt_kbc import GPTKBCRunner
from  prompter_parser import PromptJSONSchema


def main(
        gpt_model_elicitation:str,
        template_path_elicitation:str,
):
    
    prompter_parser_module = PromptJSONSchema(
        template_path_elicitation=template_path_elicitation,
        gpt_model_elicitation=gpt_model_elicitation
    )

    gpt_runner = GPTKBCRunner(
        prompter_parser_module=prompter_parser_module
    )

    list_of_subjects = gpt_runner.get_list_of_subjects()

    gpt_runner.loop(
        subjects_to_expand=list_of_subjects   
    )
    
    


if __name__ == "__main__":
    fire.Fire(main)