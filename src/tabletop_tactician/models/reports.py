from pydantic import BaseModel, ConfigDict


class ReportModel(BaseModel):
    job_id: str
    user_id: str
    attacking_army: str
    defending_army: str
    status: str
    error_msg: str | None
    result: str | None
    model_config = ConfigDict(from_attributes=True)

class UserModel(BaseModel):
    user_id: str
    email: str | None 
    enabled: bool
    num_reports_run: int  
    model_config = ConfigDict(from_attributes=True)