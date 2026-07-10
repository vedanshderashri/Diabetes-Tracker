"""
MedAI Assistant - RAG Engine
Retrieval Augmented Generation using ChromaDB, BM25, and OpenAI embeddings.
Implements in-memory hybrid search (Dense + Lexical) with RRF and rerankers.
"""
import json
import logging
import re
from typing import List, Optional
from pathlib import Path

from app.core.config import get_settings

logger = logging.getLogger(__name__)
settings = get_settings()


class RAGEngine:
    """Manages the medical knowledge vector store, BM25 lexical index, and retrieval pipeline."""

    def __init__(self):
        self._client = None
        self._collection = None
        self._embeddings = None
        self._initialized = False
        self._bm25 = None
        self._bm25_docs = []

    async def initialize(self):
        """Initialize ChromaDB client, collection, and BM25 index."""
        if self._initialized:
            return

        try:
            import chromadb
            from chromadb.config import Settings as ChromaSettings

            persist_dir = str(settings.chroma_path)
            self._client = chromadb.PersistentClient(
                path=persist_dir,
                settings=ChromaSettings(anonymized_telemetry=False),
            )
            self._collection = self._client.get_or_create_collection(
                name=settings.CHROMA_COLLECTION_NAME,
                metadata={"hnsw:space": "cosine"},
            )
            self._initialized = True
            logger.info(
                f"ChromaDB initialized with {self._collection.count()} documents"
            )

            # Build in-memory BM25 index
            self._build_bm25_index()
        except Exception as e:
            logger.error(f"Failed to initialize ChromaDB: {e}")
            self._initialized = False

    def _build_bm25_index(self):
        """Build the in-memory BM25 index from all documents currently in ChromaDB."""
        if not self._collection or self._collection.count() == 0:
            self._bm25 = None
            self._bm25_docs = []
            return

        try:
            from rank_bm25 import BM25Okapi

            # Retrieve all documents from collection
            all_data = self._collection.get()
            docs = all_data.get("documents", [])
            metadatas = all_data.get("metadatas", [])
            ids = all_data.get("ids", [])

            self._bm25_docs = []
            tokenized_corpus = []

            for i in range(len(docs)):
                doc_text = docs[i]
                meta = metadatas[i] if metadatas else {}
                doc_id = ids[i]

                self._bm25_docs.append({
                    "document": doc_text,
                    "metadata": meta,
                    "id": doc_id
                })

                # Simple tokenization for BM25
                tokens = [w.lower() for w in re.findall(r"\b[a-zA-Z0-9-]+\b", doc_text)]
                tokenized_corpus.append(tokens)

            if tokenized_corpus:
                self._bm25 = BM25Okapi(tokenized_corpus)
                logger.info(f"In-memory BM25 index built successfully with {len(tokenized_corpus)} docs.")
            else:
                self._bm25 = None
        except Exception as e:
            logger.error(f"Failed to build BM25 index: {e}")
            self._bm25 = None
            self._bm25_docs = []

    def _get_openai_embedding(self, texts: List[str]) -> List[List[float]]:
        """Generate embeddings using OpenAI API."""
        if not settings.OPENAI_API_KEY:
            logger.warning("No OpenAI API key configured, using mock embeddings")
            return [[0.0] * 1536 for _ in texts]

        from openai import OpenAI

        extra_headers = {}
        if settings.OPENAI_API_BASE and "openrouter.ai" in settings.OPENAI_API_BASE:
            extra_headers = {
                "HTTP-Referer": "https://github.com/Vedansh/Diabetes-Chatbot",
                "X-Title": "MedAI Assistant"
            }

        client = OpenAI(
            api_key=settings.OPENAI_API_KEY,
            base_url=settings.OPENAI_API_BASE if settings.OPENAI_API_BASE else None,
            default_headers=extra_headers if extra_headers else None
        )
        response = client.embeddings.create(
            input=texts,
            model=settings.OPENAI_EMBEDDING_MODEL,
        )
        return [item.embedding for item in response.data]

    async def add_documents(
        self,
        documents: List[str],
        metadatas: Optional[List[dict]] = None,
        ids: Optional[List[str]] = None,
    ):
        """Add documents to the vector store and rebuild BM25 index."""
        await self.initialize()

        if not self._collection:
            logger.error("ChromaDB collection not available")
            return

        if not ids:
            import uuid
            ids = [str(uuid.uuid4()) for _ in documents]

        # Process in batches of 100
        batch_size = 100
        for i in range(0, len(documents), batch_size):
            batch_docs = documents[i : i + batch_size]
            batch_ids = ids[i : i + batch_size]
            batch_meta = metadatas[i : i + batch_size] if metadatas else None

            try:
                embeddings = self._get_openai_embedding(batch_docs)
                self._collection.add(
                    documents=batch_docs,
                    embeddings=embeddings,
                    metadatas=batch_meta,
                    ids=batch_ids,
                )
                logger.info(f"Added batch of {len(batch_docs)} documents to vector store")
            except Exception as e:
                logger.error(f"Failed to add documents to vector store: {e}")

        # Rebuild BM25 index to reflect new changes
        self._build_bm25_index()

    async def query(
        self, query_text: str, n_results: int = 5, filter_metadata: Optional[dict] = None
    ) -> List[dict]:
        """
        Query the vector store for relevant documents (dense retrieval only).

        Returns list of dicts with 'document', 'metadata', 'distance' keys.
        """
        await self.initialize()

        if not self._collection or self._collection.count() == 0:
            return []

        try:
            query_embedding = self._get_openai_embedding([query_text])[0]

            results = self._collection.query(
                query_embeddings=[query_embedding],
                n_results=min(n_results, self._collection.count()),
                where=filter_metadata,
            )

            documents = []
            if results and results["documents"]:
                for i, doc in enumerate(results["documents"][0]):
                    documents.append(
                        {
                            "document": doc,
                            "metadata": (
                                results["metadatas"][0][i]
                                if results["metadatas"]
                                else {}
                            ),
                            "distance": (
                                results["distances"][0][i]
                                if results["distances"]
                                else 0.0
                            ),
                        }
                    )

            return documents

        except Exception as e:
            logger.error(f"RAG query failed: {e}")
            return []

    async def query_hybrid(
        self, query_text: str, n_results: int = 5, filter_metadata: Optional[dict] = None
    ) -> List[dict]:
        """
        Query RAG using hybrid search: Dense vector search + BM25 lexical search,
        fused with Reciprocal Rank Fusion (RRF) and reranked.
        """
        await self.initialize()

        # 1. Fetch dense results
        dense_results = await self.query(query_text, n_results=n_results * 3, filter_metadata=filter_metadata)

        # 2. Fetch BM25 lexical results
        lexical_results = []
        if self._bm25:
            query_tokens = [w.lower() for w in re.findall(r"\b[a-zA-Z0-9-]+\b", query_text)]
            scores = self._bm25.get_scores(query_tokens)
            
            scored_docs = []
            for i, score in enumerate(scores):
                if score > 0:
                    scored_docs.append((score, self._bm25_docs[i]))
            
            # Sort by BM25 score descending
            scored_docs.sort(key=lambda x: x[0], reverse=True)
            lexical_results = [item[1] for item in scored_docs[:n_results * 3]]

        # 3. Apply Reciprocal Rank Fusion (RRF)
        # RRF_score = sum( 1 / (60 + rank) )
        rrf_scores = {}
        doc_map = {}

        # Dense ranking processing
        for rank, doc in enumerate(dense_results):
            doc_id = doc.get("metadata", {}).get("id", doc.get("document", ""))
            key = doc_id if doc_id else doc["document"]
            rrf_scores[key] = rrf_scores.get(key, 0.0) + (1.0 / (60.0 + rank + 1))
            doc_map[key] = doc

        # Lexical ranking processing
        for rank, doc in enumerate(lexical_results):
            doc_id = doc.get("id", doc.get("document", ""))
            key = doc_id if doc_id else doc["document"]
            
            if key not in doc_map:
                doc_map[key] = {
                    "document": doc["document"],
                    "metadata": doc["metadata"],
                    "distance": 1.0  # default neutral cosine distance
                }
            rrf_scores[key] = rrf_scores.get(key, 0.0) + (1.0 / (60.0 + rank + 1))

        # Sort doc keys by RRF score descending
        sorted_keys = sorted(rrf_scores.keys(), key=lambda k: rrf_scores[k], reverse=True)
        combined_results = [doc_map[k] for k in sorted_keys]

        # 4. Rerank using lexical overlap + semantic score
        from app.services.reranker import reranker
        reranked_results = reranker.rerank(query_text, combined_results)

        return reranked_results[:n_results]

    async def seed_medical_knowledge(self, datasets_dir: str):
        """
        Seed the vector store with medical knowledge from datasets.
        Processes symptom-disease mappings and diabetes indicators.
        Uses semantic chunking for content ingestion.
        """
        import pandas as pd
        from app.services.chunker import chunker

        datasets_path = Path(datasets_dir)
        documents = []
        metadatas = []
        ids = []

        # ── Load symptom-disease mapping from dataset.csv ──
        dataset_file = datasets_path / "dataset.csv"
        if dataset_file.exists():
            try:
                df = pd.read_csv(dataset_file)
                cols = df.columns.tolist()
                disease_col = cols[0]

                for _, row in df.iterrows():
                    disease = str(row[disease_col]).strip()
                    symptoms = [
                        str(s).strip().replace("_", " ")
                        for s in row[1:].dropna().values
                        if str(s).strip() and str(s).strip() != "nan"
                    ]

                    if disease and symptoms:
                        doc = (
                            f"Disease: {disease}\n"
                            f"Associated Symptoms: {', '.join(symptoms)}\n"
                            f"When a patient presents with symptoms such as {', '.join(symptoms[:5])}, "
                            f"one possible condition to consider is {disease}. "
                            f"This condition is associated with {len(symptoms)} known symptoms."
                        )
                        # Route through semantic chunker
                        chunks = chunker.chunk_document(
                            doc, 
                            {"source": "symptom_disease_dataset", "disease": disease, "type": "disease_info"}
                        )
                        for chunk in chunks:
                            documents.append(chunk["text"])
                            metadatas.append(chunk["metadata"])
                            ids.append(f"disease_{disease.replace(' ', '_').lower()}_{len(documents)}")

                logger.info(f"Prepared {len(documents)} disease-symptom documents")
            except Exception as e:
                logger.error(f"Error processing dataset.csv: {e}")

        # ── Load diabetes risk factors ──
        diabetes_file = datasets_path / "diabetes_prediction_dataset.csv"
        if diabetes_file.exists():
            try:
                df = pd.read_csv(diabetes_file)
                risk_docs = [
                    (
                        "Diabetes Risk Factors Overview: Key risk factors for diabetes include "
                        "age, BMI (Body Mass Index), HbA1c levels, blood glucose levels, "
                        "hypertension history, heart disease history, and smoking history. "
                        "Higher BMI, elevated HbA1c (above 6.5%), and high blood glucose "
                        "levels (above 200 mg/dL) significantly increase diabetes risk."
                    ),
                    (
                        "HbA1c Levels and Diabetes: Normal HbA1c is below 5.7%. "
                        "Prediabetes range is 5.7% to 6.4%. Diabetes is diagnosed at 6.5% or above. "
                        "Regular monitoring of HbA1c is essential for diabetes management."
                    ),
                    (
                        "Blood Glucose Levels: Fasting blood glucose below 100 mg/dL is normal. "
                        "100-125 mg/dL indicates prediabetes. 126 mg/dL or above indicates diabetes. "
                        "Random blood glucose of 200 mg/dL or above with symptoms suggests diabetes."
                    ),
                    (
                        "BMI and Diabetes Risk: BMI of 18.5-24.9 is normal weight. "
                        "25-29.9 is overweight. 30 or above is obese. "
                        "Obesity significantly increases the risk of Type 2 diabetes. "
                        "Even modest weight loss of 5-10% can reduce diabetes risk."
                    ),
                    (
                        "Smoking and Diabetes: Smokers are 30-40% more likely to develop "
                        "Type 2 diabetes than nonsmokers. Smoking increases inflammation and "
                        "oxidative stress, contributing to insulin resistance."
                    ),
                ]

                for i, doc in enumerate(risk_docs):
                    chunks = chunker.chunk_document(doc, {"source": "diabetes_knowledge", "type": "diabetes_info"})
                    for chunk in chunks:
                        documents.append(chunk["text"])
                        metadatas.append(chunk["metadata"])
                        ids.append(f"diabetes_info_{i}_{len(documents)}")

                logger.info(f"Added diabetes knowledge documents")
            except Exception as e:
                logger.error(f"Error processing diabetes dataset: {e}")

        # ── General medical safety documents ──
        safety_docs = [
            (
                "Medical Safety Disclaimer: AI-generated health assessments are for "
                "informational purposes only and should not replace professional medical advice. "
                "Always consult a qualified healthcare provider for diagnosis and treatment. "
                "In case of emergency, call your local emergency number immediately."
            ),
            (
                "When to Seek Emergency Care: Seek immediate medical attention for: "
                "chest pain or pressure, difficulty breathing, sudden numbness or weakness, "
                "severe bleeding, loss of consciousness, seizures, severe allergic reactions, "
                "suicidal thoughts, poisoning or overdose, and high fever with stiff neck."
            ),
            (
                "Common Lab Test Reference Ranges: Hemoglobin (Male: 13.5-17.5 g/dL, Female: 12-16 g/dL), "
                "WBC (4,500-11,000/mcL), Platelets (150,000-400,000/mcL), "
                "Fasting Glucose (70-100 mg/dL), Creatinine (0.7-1.3 mg/dL), "
                "Total Cholesterol (below 200 mg/dL), ALT (7-56 U/L), AST (10-40 U/L), "
                "TSH (0.4-4.0 mIU/L), Uric Acid (3.4-7.0 mg/dL)."
            ),
        ]

        for i, doc in enumerate(safety_docs):
            chunks = chunker.chunk_document(doc, {"source": "medical_safety", "type": "safety_info"})
            for chunk in chunks:
                documents.append(chunk["text"])
                metadatas.append(chunk["metadata"])
                ids.append(f"safety_info_{i}_{len(documents)}")

        # ── Pharmacology knowledge documents (DDIs, Transporters, enzymes) ──
        pharma_docs = [
            (
                "Metformin Pharmacokinetic Profile and Transporter Pathways: "
                "Metformin is not metabolized by CYP450 enzymes. "
                "Its transport is mediated by organic cation transporters (OCTs) and multidrug and toxin extrusion (MATE) proteins. "
                "OCT1 (SLC22A1) is located on the basolateral (sinusoidal) membrane of hepatocytes and facilitates hepatic uptake. "
                "OCT2 (SLC22A2) is located on the basolateral membrane of renal proximal tubule cells and mediates renal tubular uptake. "
                "MATE1 (SLC47A1) and MATE2-K (SLC47A2) are located on the apical membrane of renal proximal tubule cells and mediate active urinary secretion."
            ),
            (
                "Metformin and Rifampicin Interaction: "
                "The interaction between metformin and rifampicin is transporter-mediated rather than CYP-mediated. "
                "Rifampicin, acting via the nuclear receptor PXR, induces the expression of hepatic OCT1. "
                "Increased OCT1 expression leads to increased hepatic uptake of metformin, enhancing its intracellular concentration and glucose-lowering efficacy. "
                "The effect of rifampicin on renal efflux transporters like MATE1 is variable and less clinically significant, though it may alter systemic exposure."
            ),
            (
                "Clopidogrel and Omeprazole Interaction: "
                "Clopidogrel is a prodrug requiring bioactivation. Omeprazole is a competitive inhibitor of CYP2C19 "
                "located in the endoplasmic reticulum of hepatocytes. CYP2C19 is the principal enzyme responsible for converting clopidogrel "
                "to its active thiol metabolite. Co-administration inhibits this bioactivation, reducing active metabolite levels and "
                "inhibiting clopidogrel's antiplatelet efficacy."
            ),
            (
                "Simvastatin and Gemfibrozil Interaction: "
                "Gemfibrozil and its glucuronide metabolite inhibit OATP1B1 (SLCO1B1) on the sinusoidal basolateral membrane of hepatocytes, "
                "which physiologically mediates hepatic uptake of simvastatin acid. Gemfibrozil also inhibits CYP3A4-mediated metabolism and "
                "glucuronidation of simvastatin. This dual transporter and CYP inhibition increases systemic exposure of simvastatin acid, "
                "significantly raising the risk of myotoxicity and rhabdomyolysis."
            ),
            (
                "Dolutegravir and Metformin Interaction: "
                "Dolutegravir is an inhibitor of renal organic cation transporters. It selectively inhibits OCT2 (SLC22A2) on the basolateral membrane "
                "and MATE1 (SLC47A1) on the apical membrane of renal proximal tubule epithelial cells. These transporters physiologically mediate the active "
                "renal uptake and secretion (efflux) of metformin. Inhibition reduces active renal clearance, increasing metformin plasma concentration (AUC)."
            ),
            (
                "Digoxin and Verapamil Interaction: "
                "Digoxin is a substrate of the efflux transporter P-gp (P-glycoprotein / ABCB1) located on the apical membrane of enterocytes and renal "
                "proximal tubules. Verapamil competitively inhibits P-gp, decreasing renal active tubular clearance and increasing intestinal absorption "
                "of digoxin, which increases digoxin systemic plasma concentration and toxicity risk."
            ),
            (
                "Loratadine and Ketoconazole Interaction: "
                "Loratadine is metabolized by cytochrome P450, primarily CYP3A4. Ketoconazole is a potent reversible inhibitor of CYP3A4. "
                "Co-administration blocks hepatic conversion of loratadine to its active metabolite (desloratadine), increasing loratadine AUC and plasma "
                "concentration."
            ),
            (
                "Sildenafil and Nitroglycerin Interaction: "
                "Nitroglycerin is a nitric oxide donor that stimulates guanylyl cyclase, increasing cGMP synthesis. Sildenafil is a selective inhibitor of "
                "PDE5 (phosphodiesterase type 5), which physiologically degrades cGMP. Dual administration prevents cGMP degradation, leading to marked "
                "accumulation of cGMP in vascular smooth muscle cells, causing profound vasodilation and severe, life-threatening hypotension."
            ),
            (
                "Amiodarone and Warfarin Interaction: "
                "Warfarin S-enantiomer is S-warfarin, which is metabolized primarily by hepatic CYP2C9. Amiodarone is a potent inhibitor of CYP2C9. "
                "Co-administration inhibits CYP2C9-mediated metabolic clearance of S-warfarin, prolonging INR and increasing bleeding risk."
            ),
            (
                "Tacrolimus and Erythromycin Interaction: "
                "Tacrolimus is a substrate of enterocyte apical efflux transporter P-gp (ABCB1) and metabolic enzyme CYP3A4 in enterocytes and hepatocytes. "
                "Erythromycin inhibits both CYP3A4 and P-gp. Co-administration decreases first-pass metabolism and efflux, increasing tacrolimus bioavailability "
                "and systemic concentration."
            ),
            (
                "Amlodipine and Grapefruit Juice Interaction: "
                "Amlodipine undergoes high first-pass metabolism mediated by intestinal and hepatic CYP3A4. Grapefruit juice contains furanocoumarins "
                "that selectively and irreversibly inhibit CYP3A4 in the intestinal wall, reducing presystemic first-pass extraction and increasing systemic AUC."
            ),
            (
                "Fexofenadine and Orange Juice Interaction: "
                "Fexofenadine is an OATP1A2 (SLCO1A2) substrate on the enterocyte apical membrane for active intestinal uptake. "
                "Orange juice inhibits apical enterocyte OATP1A2 activity, reducing active absorption and fexofenadine plasma AUC."
            ),
            (
                "Methotrexate and Penicillin G Interaction: "
                "Methotrexate is excreted renal-wise. It is a substrate for OAT1 (SLC22A6) and OAT3 (SLC22A8) on the basolateral membrane of renal "
                "proximal tubules, and BCRP (ABCG2) on the apical membrane. Penicillin G competes for OAT1/OAT3 active transport, "
                "decreasing renal tubular secretion and clearance of methotrexate, thereby raising methotrexate systemic levels and toxic risks."
            ),
            (
                "Rosuvastatin and Cyclosporine Interaction: "
                "Rosuvastatin is not metabolized significantly by CYP450. Cyclosporine inhibits OATP1B1 (SLCO1B1) on the basolateral membrane of hepatocytes "
                "which mediates rosuvastatin uptake, and BCRP (ABCG2) on the canalicular membrane. Rosuvastatin exposure is increased due to "
                "combined hepatic uptake and biliary efflux inhibition, causing increased Cmax and AUC."
            ),
            (
                "Carbamazepine and Erythromycin Interaction: "
                "Carbamazepine is metabolized in the liver to carbamazepine-10,11-epoxide primarily by CYP3A4. Erythromycin is a competitive and mechanism-based "
                "inhibitor of CYP3A4. Inhibition prevents carbamazepine clearance, resulting in elevated systemic plasma concentrations and carbamazepine toxicity."
            ),
            (
                "Levodopa and Entacapone Interaction: "
                "Levodopa is metabolized peripherally by Catechol-O-methyltransferase (COMT). Entacapone is a selective, reversible inhibitor of peripheral COMT. "
                "Inhibiting peripheral COMT prevents conversion of levodopa to 3-O-methyldopa, increasing levodopa systemic half-life and bio-availability to cross "
                "the blood-brain barrier via the LAT1 transporter."
            )
        ]

        for i, doc in enumerate(pharma_docs):
            chunks = chunker.chunk_document(doc, {"source": "pharmacology_reference", "type": "pharma_info"})
            for chunk in chunks:
                documents.append(chunk["text"])
                metadatas.append(chunk["metadata"])
                ids.append(f"pharma_info_{i}_{len(documents)}")

        # ── Add all documents to vector store ──
        if documents:
            await self.add_documents(documents, metadatas, ids)
            logger.info(
                f"Seeded vector store with {len(documents)} total medical knowledge documents"
            )

    def get_collection_stats(self) -> dict:
        """Get statistics about the vector store collection."""
        if not self._collection:
            return {"status": "not_initialized", "count": 0}
        return {
            "status": "active",
            "count": self._collection.count(),
            "name": settings.CHROMA_COLLECTION_NAME,
        }


# Singleton instance
rag_engine = RAGEngine()
