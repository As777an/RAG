import time
from openai import OpenAI

client = OpenAI(api_key='???')

# print(client.fine_tuning.jobs.retrieve('???'))

with open("fine.jsonl", "rb") as binary_file:
    response = client.files.create(
        file=binary_file,
        purpose='fine-tune'
    )

tr_file = response.id
print(f"Uploaded file ID: {tr_file}")
print('='*70)

training_model = client.fine_tuning.jobs.create(
    training_file=tr_file, 
    model="gpt-4o-2024-08-06"
)

fine_tuning_job_id = training_model.id
print(f"Fine-tuning job ID: {fine_tuning_job_id}")
print('='*70)

status = training_model.status
while status not in ['succeeded', 'failed']:
    time.sleep(30)
    job_status = client.fine_tuning.jobs.retrieve(fine_tuning_job_id)
    status = job_status.status
    print(f"Current status: {status}")

if status == 'succeeded':
    fine_tuned_model = job_status.fine_tuned_model
    print(f"Fine-tuning succeeded! The fine-tuned model ID is: {fine_tuned_model}")
else:
    print("Fine-tuning failed. Please check the job details for more information.")
