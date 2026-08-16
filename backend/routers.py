from fastapi import APIRouter, Depends, BackgroundTasks, HTTPException
from sqlalchemy.orm import Session
from typing import List
import json

from database import get_db
import models
import schemas
import ai_agents

router = APIRouter()

# Global dictionary to simulate simple status tracking in memory
pipeline_status = {}

def execute_pipeline(industry_id: int, industry_name: str, db: Session):
    try:
        pipeline_status[industry_id] = "Step 1: Researching value chain stages..."
        stages = ai_agents.research_value_chain(industry_name, db)
        
        for i, stage in enumerate(stages):
            pipeline_status[industry_id] = f"Step 2: Decomposing processes for stage {i+1}/{len(stages)} ({stage.name})..."
            processes = ai_agents.decompose_processes(stage, db)
            
            for j, process in enumerate(processes):
                pipeline_status[industry_id] = f"Step 3-4: Analyzing & scoring process {j+1}/{len(processes)} in stage {i+1} ({process.name})..."
                ai_agents.analyze_process(process, db)
                ai_agents.compute_priority(process, db)
                
        pipeline_status[industry_id] = "Completed successfully."
    except Exception as e:
        pipeline_status[industry_id] = f"Failed: {str(e)}"

@router.post("/industries", response_model=schemas.Industry)
def create_industry(industry: schemas.IndustryCreate, background_tasks: BackgroundTasks, db: Session = Depends(get_db)):
    db_industry = db.query(models.Industry).filter(models.Industry.name == industry.name).first()
    if not db_industry:
        db_industry = models.Industry(name=industry.name)
        db.add(db_industry)
        db.commit()
        db.refresh(db_industry)
    
    pipeline_status[db_industry.id] = "Queued..."
    background_tasks.add_task(execute_pipeline, db_industry.id, db_industry.name, db)
    
    return db_industry

@router.get("/industries/status/{industry_id}")
def get_industry_status(industry_id: int):
    return {"status": pipeline_status.get(industry_id, "Not found")}

@router.get("/industries", response_model=List[schemas.Industry])
def list_industries(db: Session = Depends(get_db)):
    return db.query(models.Industry).all()

@router.get("/industries/{industry_id}/stages", response_model=List[schemas.ValueChainStage])
def get_stages(industry_id: int, db: Session = Depends(get_db)):
    return db.query(models.ValueChainStage).filter(models.ValueChainStage.industry_id == industry_id).order_by(models.ValueChainStage.sequence_order).all()

@router.get("/industries/{industry_id}/processes")
def get_processes(industry_id: int, db: Session = Depends(get_db)):
    processes = db.query(models.Process).join(models.ValueChainStage).filter(models.ValueChainStage.industry_id == industry_id).all()
    # Serialize manually to include basic info
    res = []
    for p in processes:
        score = p.priority_score.final_priority_score if p.priority_score else None
        res.append({
            "id": p.id,
            "name": p.name,
            "stage_id": p.stage_id,
            "stage_name": p.stage.name,
            "score": score
        })
    return res

@router.get("/processes/{process_id}")
def get_process_detail(process_id: int, db: Session = Depends(get_db)):
    p = db.query(models.Process).filter(models.Process.id == process_id).first()
    if not p:
        raise HTTPException(status_code=404, detail="Process not found")
        
    finding = p.finding
    priority = p.priority_score
    
    return {
        "id": p.id,
        "name": p.name,
        "business_purpose": p.business_purpose,
        "finding": {
            "current_challenges": finding.current_challenges if finding else None,
            "ai_opportunity": finding.ai_opportunity if finding else None,
            "relevant_ai_capabilities": finding.relevant_ai_capabilities if finding else None,
            "potential_benefit": finding.potential_benefit if finding else None,
            "risk": finding.risk if finding else None,
            "automation_potential": finding.automation_potential.value if finding else None,
            "confidence_score": finding.confidence_score if finding else None,
        } if finding else None,
        "priority_score": {
            "business_impact_score": priority.business_impact_score if priority else None,
            "feasibility_score": priority.feasibility_score if priority else None,
            "risk_score": priority.risk_score if priority else None,
            "evidence_confidence": priority.evidence_confidence if priority else None,
            "final_priority_score": priority.final_priority_score if priority else None,
            "rank": priority.rank if priority else None
        } if priority else None
    }

@router.get("/processes/{process_id}/evidence", response_model=List[schemas.EvidenceSource])
def get_process_evidence(process_id: int, db: Session = Depends(get_db)):
    return db.query(models.EvidenceSource).filter(models.EvidenceSource.process_id == process_id).all()

@router.get("/industries/{industry_id}/priority")
def get_priorities(industry_id: int, limit: int = 10, db: Session = Depends(get_db)):
    # SELECT ... ORDER BY final_priority_score DESC LIMIT N
    processes = db.query(models.Process).join(models.ValueChainStage).join(models.PriorityScore).filter(
        models.ValueChainStage.industry_id == industry_id
    ).order_by(models.PriorityScore.final_priority_score.desc()).limit(limit).all()
    
    res = []
    for p in processes:
        res.append({
            "process_id": p.id,
            "process_name": p.name,
            "stage_name": p.stage.name,
            "final_priority_score": p.priority_score.final_priority_score if p.priority_score else 0,
            "rank": p.priority_score.rank if p.priority_score else None
        })
    return res

class QuestionRequest(schemas.BaseModel):
    question: str

@router.post("/industries/{industry_id}/ask")
def ask_question(industry_id: int, req: QuestionRequest, db: Session = Depends(get_db)):
    log = ai_agents.answer_query(industry_id, req.question, db)
    return {
        "question": log.question,
        "answer": log.answer,
        "evidence_ids": json.loads(log.retrieved_evidence_ids) if log.retrieved_evidence_ids else []
    }
