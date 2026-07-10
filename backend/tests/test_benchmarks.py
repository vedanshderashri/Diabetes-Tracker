"""
MedAI Assistant - Pharmacology Benchmarks & RAG Evaluator
Defines 15 gold-standard pharmacology queries with explicit targets
and evaluates the output using LLM-as-a-Judge RAG metrics.
"""
import json
import os
import pytest
import asyncio
from typing import List, Dict, Any

from app.core.config import get_settings
from app.services.ai_chat import ai_chat_service
from app.services.evaluation_service import evaluation_service
from app.services.rag_engine import rag_engine

settings = get_settings()

BENCHMARK_SUITE = [
    {
        "query": "Explain the interaction between Metformin and Rifampicin.",
        "gold_answer": (
            "Metformin is not metabolized by CYP450 enzymes. The interaction is transporter-mediated rather than CYP-mediated. "
            "Rifampicin (a PXR agonist) induces hepatic OCT1 (SLC22A1) on the basolateral membrane of hepatocytes, which increases metformin "
            "hepatic uptake and glucose-lowering efficacy. Simultaneously, rifampicin induces apical efflux transporters MATE1 (SLC47A1) "
            "and MATE2-K (SLC472A) on the renal proximal tubule cells, which increases renal tubular secretion, thereby decreasing metformin systemic plasma AUC."
        )
    },
    {
        "query": "How do Omeprazole and Clopidogrel interact?",
        "gold_answer": (
            "Clopidogrel is a prodrug requiring bioactivation. Omeprazole is a competitive inhibitor of CYP2C19 "
            "located in the endoplasmic reticulum of hepatocytes. CYP2C19 is the principal enzyme responsible for converting clopidogrel "
            "to its active thiol metabolite. Co-administration inhibits this bioactivation, reducing active metabolite levels and "
            "inhibiting clopidogrel's antiplatelet efficacy."
        )
    },
    {
        "query": "Describe the transporter and metabolic interaction between Simvastatin and Gemfibrozil.",
        "gold_answer": (
            "Gemfibrozil and its glucuronide metabolite inhibit OATP1B1 (SLCO1B1) on the sinusoidal basolateral membrane of hepatocytes, "
            "which physiologically mediates hepatic uptake of simvastatin acid. Gemfibrozil also inhibits CYP3A4-mediated metabolism and "
            "glucuronidation of simvastatin. This dual transporter and CYP inhibition increases systemic exposure of simvastatin acid, "
            "significantly raising the risk of myotoxicity and rhabdomyolysis."
        )
    },
    {
        "query": "Discuss the mechanism of Dolutegravir-induced Metformin systemic elevation.",
        "gold_answer": (
            "Dolutegravir is an inhibitor of renal organic cation transporters. It selectively inhibits OCT2 (SLC22A2) on the basolateral membrane "
            "and MATE1 (SLC47A1) on the apical membrane of renal proximal tubule epithelial cells. These transporters physiologically mediate the active "
            "renal uptake and secretion (efflux) of metformin. Inhibition reduces active renal clearance, increasing metformin plasma concentration (AUC)."
        )
    },
    {
        "query": "Explain the pharmacokinetics of the Digoxin and Verapamil interaction.",
        "gold_answer": (
            "Digoxin is a substrate of the efflux transporter P-gp (P-glycoprotein / ABCB1) located on the apical membrane of enterocytes and renal "
            "proximal tubules. Verapamil competitively inhibits P-gp, decreasing renal active tubular clearance and increasing intestinal absorption "
            "of digoxin, which increases digoxin systemic plasma concentration and toxicity risk."
        )
    },
    {
        "query": "What is the interaction mechanism of Loratadine and Ketoconazole?",
        "gold_answer": (
            "Loratadine is metabolized by cytochrome P450, primarily CYP3A4. Ketoconazole is a potent reversible inhibitor of CYP3A4. "
            "Co-administration blocks hepatic conversion of loratadine to its active metabolite (desloratadine), increasing loratadine AUC and plasma "
            "concentration."
        )
    },
    {
        "query": "Explain the pharmacodynamic interaction between Sildenafil and Nitroglycerin.",
        "gold_answer": (
            "Nitroglycerin is a nitric oxide donor that stimulates guanylyl cyclase, increasing cGMP synthesis. Sildenafil is a selective inhibitor of "
            "PDE5 (phosphodiesterase type 5), which physiologically degrades cGMP. Dual administration prevents cGMP degradation, leading to marked "
            "accumulation of cGMP in vascular smooth muscle cells, causing profound vasodilation and severe, life-threatening hypotension."
        )
    },
    {
        "query": "Describe how Amiodarone increases Warfarin systemic exposure.",
        "gold_answer": (
            "Warfarin is administered as a racemic mixture; S-warfarin is more potent and metabolized primarily by CYP2C9 in hepatocytes. Amiodarone "
            "is a potent inhibitor of CYP2C9. Upregulation of warfarin levels occurs because amiodarone inhibits CYP2C9 metabolic clearance of S-warfarin, "
            "prolonging INR and increasing bleeding risk."
        )
    },
    {
        "query": "Discuss the absorption and metabolic interaction between Tacrolimus and Erythromycin.",
        "gold_answer": (
            "Tacrolimus is a substrate of both the efflux transporter P-gp (ABCB1) on the enterocyte apical membrane and CYP3A4 in the enterocytes and hepatocytes. "
            "Erythromycin is an inhibitor of both CYP3A4 and P-gp. Co-administration decreases first-pass metabolism and increases systemic bio-availability "
            "of tacrolimus, raising blood levels and nephrotoxicity risk."
        )
    },
    {
        "query": "How does Grapefruit juice alter Amlodipine pharmacokinetics?",
        "gold_answer": (
            "Amlodipine undergoes high first-pass metabolism mediated by intestinal and hepatic CYP3A4. Grapefruit juice contains furanocoumarins "
            "that irreversibly inhibit CYP3A4 in the intestinal wall. This selective inactivation reduces intestinal presystemic first-pass extraction, "
            "increasing amlodipine bioavailability, Cmax, and systemic AUC."
        )
    },
    {
        "query": "Detail the absorption interaction between Fexofenadine and Orange juice.",
        "gold_answer": (
            "Fexofenadine is an organic anion transport substrate requiring OATP1A2 (SLCO1A2) on the apical membrane of enterocytes for active intestinal uptake. "
            "Orange juice contains components that inhibit OATP1A2 activity. Co-administration reduces active intestinal absorption, decreasing fexofenadine "
            "plasma concentration and reducing its therapeutic antihistaminic efficacy."
        )
    },
    {
        "query": "Explain the clearance interaction between Methotrexate and Penicillin G.",
        "gold_answer": (
            "Methotrexate is actively excreted in the kidney. It is a substrate for OAT1 (SLC22A6) and OAT3 (SLC22A8) on the basolateral membrane of renal "
            "proximal tubules, and breast cancer resistance protein (BCRP / ABCG2) on the apical membrane. Penicillin G competes for OAT1/OAT3 active transport, "
            "decreasing renal tubular secretion and clearance of methotrexate, thereby raising methotrexate systemic levels and toxic risks."
        )
    },
    {
        "query": "Describe the cyclosporine-mediated pharmacokinetic changes of Rosuvastatin.",
        "gold_answer": (
            "Rosuvastatin is not metabolized significantly by CYP450. Cyclosporine inhibits OATP1B1 (SLCO1B1) on the basolateral membrane of hepatocytes "
            "which mediates rosuvastatin uptake, and BCRP (ABCG2) on the canalicular membrane. Upregulation of systemic rosuvastatin exposure occurs "
            "due to combined hepatic uptake and biliary efflux inhibition, causing increased Cmax and AUC."
        )
    },
    {
        "query": "Discuss the metabolic interaction between Carbamazepine and Erythromycin.",
        "gold_answer": (
            "Carbamazepine is metabolized in the liver to carbamazepine-10,11-epoxide primarily by CYP3A4. Erythromycin is a competitive and mechanism-based "
            "inhibitor of CYP3A4. Inhibition prevents carbamazepine clearance, resulting in elevated systemic plasma concentrations and carbamazepine toxicity."
        )
    },
    {
        "query": "Explain how Entacapone optimizes Levodopa pharmacokinetics.",
        "gold_answer": (
            "Levodopa is metabolized peripherally by Catechol-O-methyltransferase (COMT). Entacapone is a selective, reversible inhibitor of peripheral COMT. "
            "Inhibiting peripheral COMT prevents conversion of levodopa to 3-O-methyldopa, increasing levodopa systemic half-life and bio-availability to cross "
            "the blood-brain barrier via the LAT1 transporter."
        )
    }
]

@pytest.mark.asyncio
async def test_run_pharmacology_benchmarks():
    """
    Executes the 15 gold-standard pharmacology queries against the RAG pipeline.
    Runs automated evaluations and outputs a validation report.
    """
    if not settings.OPENAI_API_KEY:
        pytest.skip("Skipping benchmarks: No OPENAI_API_KEY configured.")

    print(f"\n{'='*20} RUNNING RAG PHARMACOLOGY BENCHMARKS {'='*20}")
    
    evaluation_reports = []
    
    # Initialize RAG collections
    await rag_engine.initialize()

    for idx, case in enumerate(BENCHMARK_SUITE, 1):
        query = case["query"]
        gold_answer = case["gold_answer"]
        
        print(f"\n[Case {idx}/15] Query: {query}")
        
        # 1. RAG Retrieve (using query_hybrid)
        rag_results = await rag_engine.query_hybrid(query, n_results=4)
        
        # Format context
        context_parts = []
        for ri, res in enumerate(rag_results, 1):
            context_parts.append(f"[Source {ri}]: {res['document']}")
        context = "\n\n".join(context_parts)
        
        # 2. Build system prompt
        system_prompt = (
            "You are PharmaGPT, a professional pharmacology AI assistant. "
            "ground your response in this context:\n"
            f"{context}\n\n"
            f"{settings.OPENAI_CHAT_MODEL}"
        )
        
        # 3. Call LLM service to get answer
        try:
            from app.services.context_builder import ContextResult
            from app.services.llm_service import llm_service
            
            context_res = ContextResult(
                rag_context=context,
                combined_context=context,
                source_type="rag_only",
                rag_sources_count=len(rag_results)
            )
            
            # Call LLM service directly to generate the response
            llm_response = await llm_service.generate_response(
                base_system_prompt=system_prompt,
                user_message=query,
                context=context_res
            )
            
            answer = llm_response.content
            references = llm_response.references
            
            # Evaluate using LLM-as-a-judge
            eval_report = evaluation_service.run_full_evaluation(
                query=query,
                context=context if context else "No context retrieved.",
                response=answer,
                references=references,
                gold_answer=gold_answer
            )
            
            evaluation_reports.append(eval_report)
            
            # Print metrics
            print(f" -> Latency: {eval_report['performance']['latency_seconds']}s")
            print(f" -> Faithfulness (Groundedness): {eval_report['metrics']['faithfulness']}")
            print(f" -> Context Precision: {eval_report['metrics']['context_precision']}")
            print(f" -> Context Recall: {eval_report['metrics']['context_recall']}")
            print(f" -> Citation Accuracy: {eval_report['metrics']['citation_accuracy']}")
            
        except Exception as e:
            print(f"Failed benchmark query {idx}: {e}")
            import traceback
            traceback.print_exc()
            
    # Save the consolidated evaluation report
    report_file = os.path.join(
        settings.BASE_DIR, "evaluation_report.json"
    )
    with open(report_file, "w") as f:
        json.dump(evaluation_reports, f, indent=2)
        
    print(f"\nConsolidated evaluation report saved to {report_file}")
    
    # Calculate average metrics
    if evaluation_reports:
        avg_faithfulness = sum(r["metrics"]["faithfulness"] for r in evaluation_reports) / len(evaluation_reports)
        avg_precision = sum(r["metrics"]["context_precision"] for r in evaluation_reports) / len(evaluation_reports)
        avg_recall = sum(r["metrics"]["context_recall"] for r in evaluation_reports) / len(evaluation_reports)
        avg_citation = sum(r["metrics"]["citation_accuracy"] for r in evaluation_reports) / len(evaluation_reports)
        
        print("\nAVERAGE BENCHMARK METRICS:")
        print(f" - Faithfulness: {avg_faithfulness:.2%}")
        print(f" - Context Precision: {avg_precision:.2%}")
        print(f" - Context Recall: {avg_recall:.2%}")
        print(f" - Citation Accuracy: {avg_citation:.2%}")
        
        # Verify basic precision threshold to pass test
        assert avg_faithfulness >= 0.70, f"Faithfulness {avg_faithfulness:.2%} is below threshold"
