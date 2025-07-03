import logging
import azure.functions as func
from .pipeline_logic import update_tokens_and_fetch_activities

def main(mytimer: func.TimerRequest) -> None:
    logging.info('Python timer trigger function is starting the Strava pipeline.')
    
    try:
        update_tokens_and_fetch_activities()
        logging.info('Strava data pipeline completed successfully.')
    except Exception as e:
        logging.error(f'Pipeline failed with an unhandled error: {e}', exc_info=True)

    logging.info('Python timer trigger function execution finished.')