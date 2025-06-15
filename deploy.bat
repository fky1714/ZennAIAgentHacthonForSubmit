@REM gcloud auth login

cd task_solution
@REM gcloud config set project pctasksolutions

@REM gcloud artifacts repositories create pc-task-solution-repo --repository-format=docker --location=asia-northeast1 --description="Zenn Hackathon"

@REM gcloud projects add-iam-policy-binding pctasksolutions --member="serviceAccount:449349434961-compute@developer.gserviceaccount.com" --role="roles/aiplatform.user" --role="roles/storage.objectAdmin"
@REM gcloud builds submit --tag gcr.io/pctasksolutions/task_solution
gcloud builds submit --tag asia-northeast1-docker.pkg.dev/pctasksolutions/pc-task-solution-repo/task_solution:test 
gcloud run deploy task-solution --image asia-northeast1-docker.pkg.dev/pctasksolutions/pc-task-solution-repo/task_solution:test --platform managed --region asia-northeast1 --allow-unauthenticated