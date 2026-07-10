# 🏥 MedAI Assistant

AI-powered healthcare platform combining conversational AI, medical report analysis, disease prediction, patient health management, and retrieval-augmented medical knowledge.

## ✨ Features

| Feature | Description |
|---------|-------------|
| **AI Medical Chatbot** | Natural language conversations with symptom analysis, follow-up questions, and medical safety guardrails |
| **Medical Report Analysis** | Upload PDF/JPG/PNG reports → OCR extraction → AI-powered lab value analysis |
| **Disease Prediction** | ML models trained on real datasets for symptom→disease and diabetes risk prediction |
| **RAG Engine** | ChromaDB vector store with medical knowledge for grounded, source-cited responses |
| **Patient Health Profile** | Complete health records: medical history, medications, allergies, chronic conditions |
| **Emergency Detection** | Real-time detection of 8 emergency categories (cardiac, respiratory, stroke, etc.) |
| **Doctor Summary Generator** | AI-generated clinical summaries for healthcare providers |
| **Patient Dashboard** | Health score, risk indicators, trends, and AI health insights |
| **Admin Panel** | User management, analytics, system monitoring |
| **Multi-language** | English and Hindi (हिंदी) support |

## 🏗️ Tech Stack

- **Frontend**: Next.js 15 · TypeScript · Tailwind CSS
- **Backend**: FastAPI · Python 3.11+
- **Database**: SQLite (dev) / PostgreSQL (production)
- **Vector DB**: ChromaDB
- **AI**: OpenAI GPT-4o-mini · LangChain
- **ML**: Scikit-learn · Pandas · NumPy
- **OCR**: PyMuPDF · Pytesseract
- **Auth**: JWT · bcrypt
- **Deployment**: Docker · Docker Compose

## 🚀 Quick Start

### Prerequisites
- Python 3.11+
- Node.js 20+
- (Optional) OpenAI API key for AI features

### 1. Clone & Setup Backend

```bash
cd backend
python -m venv venv
venv\Scripts\activate  # Windows
# source venv/bin/activate  # macOS/Linux

pip install -r requirements.txt
```

### 2. Configure Environment

```bash
# Copy and edit the .env file
cp .env.example .env
# Add your OPENAI_API_KEY in .env
```

### 3. Train ML Models

```bash
cd backend
python -m app.ml.train_models
```

### 4. Start Backend

```bash
cd backend
uvicorn app.main:app --reload --port 8000
```

### 5. Start Frontend

```bash
cd frontend
npm install
npm run dev
```

### 6. Open Application

Visit **http://localhost:3000** in your browser.

## 🐳 Docker Deployment

```bash
# Set your OpenAI API key
export OPENAI_API_KEY=your-key-here

# Build and run all services
docker-compose up --build
```

Services:
- Frontend: http://localhost:3000
- Backend API: http://localhost:8000
- API Docs: http://localhost:8000/docs

## 📡 API Endpoints

| Method | Endpoint | Description |
|--------|----------|-------------|
| POST | `/api/v1/auth/register` | Register new user |
| POST | `/api/v1/auth/login` | Login |
| GET | `/api/v1/auth/me` | Current user |
| POST | `/api/v1/chat/sessions` | Create chat session |
| POST | `/api/v1/chat/sessions/{id}/messages` | Send message |
| POST | `/api/v1/reports/upload` | Upload medical report |
| GET | `/api/v1/reports/{id}` | Get report analysis |
| POST | `/api/v1/prediction/symptoms` | Symptom prediction |
| POST | `/api/v1/prediction/diabetes-risk` | Diabetes risk |
| GET | `/api/v1/dashboard` | Patient dashboard |
| GET/PUT | `/api/v1/patients/profile` | Patient profile |
| POST | `/api/v1/summary/generate` | Doctor summary |
| GET | `/api/v1/admin/analytics` | Admin analytics |

Full API docs: http://localhost:8000/docs

## 📊 Datasets Used

| Dataset | Records | Purpose |
|---------|---------|---------|
| `Training.csv` | 4,920 | Symptom → Disease mapping (132 symptoms) |
| `Testing.csv` | 41 | Model validation |
| `dataset.csv` | 4,920 | Disease-symptom name mapping |
| `diabetes_prediction_dataset.csv` | 100,000 | Diabetes risk prediction |
| `diabetes_012_health_indicators_BRFSS2015.csv` | ~250K | BRFSS health indicators |

## ⚠️ Medical Safety

- **Never provides definitive diagnoses** — only possible conditions with confidence levels
- **Never prescribes medication dosages**
- **Always includes safety disclaimers**
- **Emergency detection** with immediate safety alerts
- **Always recommends consulting qualified healthcare professionals**

## 📁 Project Structure

```
medai-assistant/
├── backend/
│   ├── app/
│   │   ├── api/v1/          # API endpoints
│   │   ├── core/            # Config, DB, security
│   │   ├── models/          # SQLAlchemy models
│   │   ├── schemas/         # Pydantic schemas
│   │   ├── services/        # Business logic (AI, RAG, ML)
│   │   └── ml/              # Model training
│   └── tests/               # Test suite
├── frontend/
│   └── src/app/             # Next.js pages
├── docker/                  # Docker configs
├── docker-compose.yml
└── README.md
```

## 🧪 Running Tests

```bash
cd backend
python -m pytest tests/ -v
```

## 📄 License

This project is for educational and research purposes. Not intended for production medical use without proper clinical validation and regulatory compliance.
