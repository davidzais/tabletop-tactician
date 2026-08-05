import logging
from uuid import uuid4

import uvicorn
from fastapi import BackgroundTasks, FastAPI, HTTPException, UploadFile, status

from tabletop_tactician.agent.adviser import build_full_report
from tabletop_tactician.reference_data.roster import Army, load_roster

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(name)s: %(message)s",
)

logger = logging.getLogger(__name__)
app = FastAPI()

JOBS: dict[str, dict[str, str | None]] = {}

@app.post("/report", status_code=status.HTTP_202_ACCEPTED)
def generate_report(my_army: UploadFile, enemy_army: UploadFile, background_tasks: BackgroundTasks, dry_run: bool = False):

    saved_files = {}
    current_processing_army = None
    
    try:
        current_processing_army = "my_army"
        content_bytes = my_army.file.read()
        my_army_content = content_bytes.decode("utf-8")
        saved_files["my_army"] = my_army_content

        current_processing_army = "enemy_army"
        content_bytes = enemy_army.file.read()
        enemy_army_content = content_bytes.decode("utf-8")
        saved_files["enemy_army"] = enemy_army_content

        attacker: Army = load_roster(saved_files["my_army"])
        defender: Army = load_roster(saved_files["enemy_army"])

        #creat a unique job id and set its status to pending in the JOBS dictionary
        job_id = str(uuid4())
        JOBS[job_id] = {"status": "pending", "report": None}

        #run this in the background so that the API can return a response immediately
        background_tasks.add_task(process_report, job_id, attacker, defender, dry_run)
        return {"job_id": job_id}
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail=f"Could not parse file {current_processing_army}: {str(e)}"
        )
    finally:
        # Always close the FastAPI UploadFile stream
        my_army.file.close()
        enemy_army.file.close()

    

@app.get("/report/{job_id}")
def get_report(job_id: str):
    job = JOBS.get(job_id)
    if job is None:
        raise HTTPException(status_code=404, detail="unknown job id")
    return job   # {"status": "pending"}  or  {"status": "done", "report": "..."}
   
    

def process_report(job_id: str, my_army: Army, enemy_army: Army, dry_run: bool = False) -> None:
    try:
        report = build_full_report(my_army=my_army, enemy_army=enemy_army, dry_run=dry_run)
        JOBS[job_id] = {"status": "done", "report": report}
    except ValueError as e:
        JOBS[job_id] = {"status": "failed", "error": str(e)}


def main() -> None:
    uvicorn.run("tabletop_tactician.api.main:app", host="127.0.0.1", port=8000, reload=True, log_level="info")



if __name__ == "__main__":
    main()
