import os
import json
from typing import List, Dict, Any
from pydantic import ValidationError
from groq import Groq
from tavily import TavilyClient
from dotenv import load_dotenv
from sqlalchemy.orm import Session

import schemas
import models
from vector_db import add_evidence_to_vector_store, search_evidence

load_dotenv(override=True)

# Initialize clients
try:
    groq_client = Groq(api_key=os.getenv("GROQ_API_KEY"))
except Exception:
    groq_client = None

try:
    tavily_client = TavilyClient(api_key=os.getenv("TAVILY_API_KEY"))
except Exception:
    tavily_client = None

def _extract_json_from_response(content: str) -> dict:
    try:
        return json.loads(content)
    except json.JSONDecodeError:
        # Sometimes LLMs wrap json in markdown
        if "```json" in content:
            content = content.split("```json")[1].split("```")[0]
        elif "```" in content:
            content = content.split("```")[1].split("```")[0]
        return json.loads(content.strip())

# Step 1 — Value Chain Research Agent
def research_value_chain(industry_name: str, db: Session) -> List[models.ValueChainStage]:
    industry = db.query(models.Industry).filter(models.Industry.name == industry_name).first()
    if not industry:
        industry = models.Industry(name=industry_name)
        db.add(industry)
        db.commit()
        db.refresh(industry)
    
    # If stages already exist, return them (idempotency)
    existing_stages = db.query(models.ValueChainStage).filter(models.ValueChainStage.industry_id == industry.id).order_by(models.ValueChainStage.sequence_order).all()
    if existing_stages:
        return existing_stages

    raw_text = ""
    if tavily_client:
        try:
            search_result = tavily_client.search(query=f"{industry_name} industry value chain stages", search_depth="basic")
            raw_text = "\n".join([res["content"] for res in search_result.get("results", [])])
        except Exception as e:
            print(f"Tavily search failed: {e}")
            raw_text = f"Simulated text: The {industry_name} industry typically involves R&D, Procurement, Manufacturing, Distribution, and Sales."

    system_prompt = """You are an expert business analyst. Extract 5-8 sequential value chain stages from the provided research text.
Respond with ONLY valid JSON — no markdown fences, no explanation, no extra text.
The JSON must be an object with a single key 'stages', containing a list of objects.
Each object must have 'name' (string) and 'description' (string)."""
    
    user_prompt = f"Extract stages for the {industry_name} industry from this text:\n\n{raw_text}"
    
    created_stages = []
    if groq_client:
        response = groq_client.chat.completions.create(
            model="openai/gpt-oss-20b",
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt}
            ],
            response_format={"type": "json_object"},
            temperature=0.1,
        )
        try:
            content = response.choices[0].message.content
            parsed_data = _extract_json_from_response(content)
            stages_list = parsed_data.get("stages", [])
            
            for i, stage_data in enumerate(stages_list):
                stage = models.ValueChainStage(
                    industry_id=industry.id,
                    name=stage_data.get("name", f"Stage {i+1}")[:255],
                    sequence_order=i+1,
                    description=stage_data.get("description", "")
                )
                db.add(stage)
                created_stages.append(stage)
            
            db.commit()
            for stage in created_stages:
                db.refresh(stage)
        except Exception as e:
            print(f"Failed to parse LLM response: {e}, content: {response.choices[0].message.content}")
            db.rollback()
    return created_stages

# Step 2 — Process Decomposition Agent
def decompose_processes(stage: models.ValueChainStage, db: Session) -> List[models.Process]:
    existing_processes = db.query(models.Process).filter(models.Process.stage_id == stage.id).all()
    if existing_processes:
        return existing_processes

    raw_text = ""
    if tavily_client:
        try:
            search_result = tavily_client.search(query=f"processes in {stage.name} stage of {stage.industry.name} industry", search_depth="basic")
            raw_text = "\n".join([res["content"] for res in search_result.get("results", [])])
        except Exception as e:
            print(f"Tavily search failed: {e}")

    system_prompt = """You are an expert business analyst. Identify 3-6 specific real-world processes within the provided value chain stage.
Respond with ONLY valid JSON — no markdown fences, no explanation, no extra text.
The JSON must be an object with a single key 'processes', containing a list of objects.
Each object must have 'name' (string) and 'business_purpose' (string)."""
    
    user_prompt = f"Identify processes for the '{stage.name}' stage in the {stage.industry.name} industry based on this text:\n\n{raw_text}"
    
    created_processes = []
    if groq_client:
        response = groq_client.chat.completions.create(
            model="openai/gpt-oss-20b",
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt}
            ],
            response_format={"type": "json_object"},
            temperature=0.1,
        )
        try:
            content = response.choices[0].message.content
            parsed_data = _extract_json_from_response(content)
            processes_list = parsed_data.get("processes", [])
            
            for p_data in processes_list:
                process = models.Process(
                    stage_id=stage.id,
                    name=p_data.get("name", "Unknown Process")[:255],
                    business_purpose=p_data.get("business_purpose", "")
                )
                db.add(process)
                created_processes.append(process)
            
            db.commit()
            for p in created_processes:
                db.refresh(p)
        except Exception as e:
            print(f"Failed to parse LLM response: {e}")
            db.rollback()
    return created_processes

# Step 3 — Per-Process Analysis Agent
def analyze_process(process: models.Process, db: Session) -> None:
    if process.finding:
        return # Already analyzed

    search_results = []
    if tavily_client:
        try:
            search_query = f"AI opportunities, automation use cases, challenges, and benefits for {process.name} in {process.stage.industry.name} industry"
            search_result = tavily_client.search(query=search_query, search_depth="advanced", max_results=7)
            search_results = search_result.get("results", [])
        except Exception as e:
            print(f"Tavily search failed: {e}")
            
    # Format sources for LLM
    sources_text = ""
    for i, res in enumerate(search_results):
        sources_text += f"[Source {i+1}]: {res['url']}\n{res['content']}\n\n"

    system_prompt = """You are an expert AI implementation consultant. Analyze the process and identify AI opportunities based strictly on the retrieved sources.
Respond with ONLY valid JSON — no markdown fences, no explanation, no extra text.
The JSON must be an object with exactly these keys:
{
  "current_challenges": "string",
  "ai_opportunity": "string",
  "relevant_ai_capabilities": "string",
  "potential_benefit": "string",
  "risk": "string",
  "automation_potential": "low" or "medium" or "high",
  "confidence_score": number between 0.0 and 1.0,
  "evidence_links": [
    {
      "source_url": "url string",
      "source_title": "string",
      "extracted_snippet": "string"
    }
  ]
}
If no evidence supports a claim, use the string 'no supporting evidence found' for that field."""

    user_prompt = f"Process: {process.name}\nIndustry: {process.stage.industry.name}\n\nSources:\n{sources_text}"

    if groq_client:
        response = groq_client.chat.completions.create(
            model="openai/gpt-oss-20b",
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt}
            ],
            response_format={"type": "json_object"},
            temperature=0.1,
        )
        try:
            content = response.choices[0].message.content
            parsed_data = _extract_json_from_response(content)
            
            # Map enum
            auto_pot = parsed_data.get("automation_potential", "medium").lower()
            if auto_pot not in ["low", "medium", "high"]:
                auto_pot = "medium"

            finding = models.ProcessFinding(
                process_id=process.id,
                current_challenges=parsed_data.get("current_challenges", "no supporting evidence found"),
                ai_opportunity=parsed_data.get("ai_opportunity", "no supporting evidence found"),
                relevant_ai_capabilities=parsed_data.get("relevant_ai_capabilities", "no supporting evidence found"),
                potential_benefit=parsed_data.get("potential_benefit", "no supporting evidence found"),
                risk=parsed_data.get("risk", "no supporting evidence found"),
                automation_potential=models.AutomationPotential(auto_pot),
                confidence_score=float(parsed_data.get("confidence_score", 0.5))
            )
            db.add(finding)
            db.commit()
            db.refresh(finding)
            
            # Store evidence
            evidence_links = parsed_data.get("evidence_links", [])
            for link in evidence_links:
                evidence = models.EvidenceSource(
                    process_id=process.id,
                    source_url=link.get("source_url", ""),
                    source_title=link.get("source_title", "Unknown Source"),
                    extracted_snippet=link.get("extracted_snippet", ""),
                    supports_finding_id=finding.id
                )
                db.add(evidence)
                db.commit()
                db.refresh(evidence)
                
                # Embed evidence in ChromaDB
                metadata = {
                    "process_id": process.id,
                    "industry_id": process.stage.industry_id,
                    "source_url": evidence.source_url
                }
                add_evidence_to_vector_store(evidence.id, evidence.extracted_snippet, metadata)
                
        except Exception as e:
            print(f"Failed to parse LLM response in Step 3: {e}")
            db.rollback()

# Step 4 — Prioritization Engine (rule-based, not LLM freeform)
def compute_priority(process: models.Process, db: Session) -> models.PriorityScore:
    # Early return removed to allow updating existing scores if this function is called again
        
    finding = process.finding
    if not finding:
        return None
        
    # Derive scores based on findings
    # business_impact_score (0-10): derive from automation potential + benefit length bonus
    impact_map = {"low": 3.0, "medium": 6.0, "high": 9.0}
    base_impact = impact_map.get(finding.automation_potential.value, 5.0)
    benefit_length_bonus = min(1.0, len(finding.potential_benefit) / 400.0)
    business_impact_score = min(10.0, base_impact + benefit_length_bonus)
    
    # feasibility_score (0-10): evaluate complexity from capabilities
    caps = finding.relevant_ai_capabilities.lower()
    complexity_penalty = 0.0
    if "generative" in caps or "llm" in caps: complexity_penalty += 1.5
    if "robotics" in caps or "hardware" in caps or "autonomous" in caps: complexity_penalty += 2.5
    if "computer vision" in caps or "image processing" in caps: complexity_penalty += 1.0
    if "predictive" in caps or "machine learning" in caps: complexity_penalty += 0.5
    feasibility_score = max(1.0, 9.5 - complexity_penalty)
    
    # risk_score (0-10): semantic keyword scan + length penalty
    risk_text = finding.risk.lower()
    if "high" in risk_text or "critical" in risk_text or "severe" in risk_text:
        base_risk = 8.0
    elif "low" in risk_text or "minor" in risk_text:
        base_risk = 3.0
    else:
        base_risk = 5.5
    risk_length_penalty = min(2.0, len(finding.risk) / 300.0)
    risk_score = min(10.0, base_risk + risk_length_penalty)
    
    # evidence_confidence (0-10)
    evidence_bonus = min(2.0, len(process.evidence) * 0.4)
    evidence_confidence = min(10.0, (finding.confidence_score * 8.0) + evidence_bonus)
    
    final_score = (0.35 * business_impact_score) + (0.30 * feasibility_score) + (0.20 * evidence_confidence) - (0.15 * risk_score)
    
    # Round to 2 decimal places for cleaner sorting
    final_score = round(final_score, 2)
    
    if process.priority_score:
        # Update existing score
        priority = process.priority_score
        priority.business_impact_score = business_impact_score
        priority.feasibility_score = feasibility_score
        priority.risk_score = risk_score
        priority.evidence_confidence = evidence_confidence
        priority.final_priority_score = final_score
    else:
        priority = models.PriorityScore(
            process_id=process.id,
            business_impact_score=business_impact_score,
            feasibility_score=feasibility_score,
            risk_score=risk_score,
            evidence_confidence=evidence_confidence,
            final_priority_score=final_score
        )
        db.add(priority)
        
    db.commit()
    
    # Recompute ranks for the industry
    # We do a simple window function or re-rank in python
    all_scores = db.query(models.PriorityScore).join(models.Process).join(models.ValueChainStage).filter(
        models.ValueChainStage.industry_id == process.stage.industry_id
    ).order_by(models.PriorityScore.final_priority_score.desc()).all()
    
    for i, score in enumerate(all_scores):
        score.rank = i + 1
        
    db.commit()
    db.refresh(priority)
    return priority

# Step 5 — Interrogation / Query Agent
def answer_query(industry_id: int, question: str, db: Session) -> models.QueryLog:
    # Vector Search over ChromaDB
    results = search_evidence(question, n_results=5)
    
    documents = results.get("documents", [[]])[0]
    metadatas = results.get("metadatas", [[]])[0]
    ids = results.get("ids", [[]])[0]
    
    # Filter by industry_id
    valid_docs = []
    valid_ids = []
    for doc, meta, doc_id in zip(documents, metadatas, ids):
        if meta.get("industry_id") == industry_id:
            valid_docs.append(doc)
            valid_ids.append(doc_id)
            
    context = "\n".join(valid_docs)
    
    system_prompt = """You are an AI assistant answering questions about an industry analysis.
Answer the user's question strictly using the provided context (which are evidence snippets from the database).
Do not use outside knowledge. If the context does not contain the answer, say so.
Return plain text — do not wrap your answer in JSON."""

    user_prompt = f"Question: {question}\n\nContext:\n{context}"
    
    answer_text = "Sorry, no answer could be generated."
    if groq_client:
        response = groq_client.chat.completions.create(
            model="openai/gpt-oss-20b",
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt}
            ],
            temperature=0.1,
        )
        answer_text = response.choices[0].message.content

    query_log = models.QueryLog(
        industry_id=industry_id,
        question=question,
        answer=answer_text,
        retrieved_evidence_ids=json.dumps(valid_ids)
    )
    db.add(query_log)
    db.commit()
    db.refresh(query_log)
    
    return query_log
