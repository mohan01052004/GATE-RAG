# Advanced RAG System with Semantic Chunking

A production-grade Retrieval-Augmented Generation (RAG) system for GATE examination preparation with advanced PDF parsing, semantic chunking, and hybrid search capabilities.

## 🚀 Features

- **Advanced PDF Parsing**: Intelligent extraction of PDF structure with heading hierarchy detection
- **Semantic Chunking**: Context-aware document chunking with configurable boundaries and overlap
- **Hybrid Search**: Combine semantic, keyword, and semantic-reranking search methods
- **Vector Storage**: Integration with Pinecone for efficient similarity search
- **LLM Integration**: Google Gemini API for intelligent query responses
- **MCQ Generation**: Automatic generation of GATE-style multiple choice questions
- **Practice Questions**: Interactive practice mode with answer validation
- **Multi-Query Retrieval**: Expand queries to retrieve more relevant context

## 📋 Tech Stack

### Backend
- **Framework**: FastAPI with Python 3.14
- **Vector Store**: Pinecone
- **Database**: PostgreSQL
- **LLM**: Google Gemini 2.5-flash
- **Embeddings**: SentenceTransformer (all-MiniLM-L6-v2)
- **PDF Processing**: pypdf

### Frontend
- **Framework**: React
- **UI Components**: Custom CSS components
- **API Client**: Fetch API

## 🛠️ Installation

### Prerequisites
- Python 3.10+
- Node.js 14+
- PostgreSQL 12+
- Git

### Backend Setup

1. **Clone the repository**
   ```bash
   git clone <your-repo-url>
   cd RAG VS
   ```

2. **Create Python virtual environment**
   ```bash
   cd backend
   python -m venv venv
   venv\Scripts\activate
   ```

3. **Install dependencies**
   ```bash
   pip install -r requirements.txt
   ```

4. **Configure environment variables**
   ```bash
   cp .env.example .env
   # Edit .env with your API keys
   ```

5. **Initialize database**
   ```bash
   python create_tables.py
   ```

6. **Start backend server**
   ```bash
   python -m uvicorn app.main:app --reload --port 8000
   ```

### Frontend Setup

1. **Navigate to frontend directory**
   ```bash
   cd ../my-app
   ```

2. **Install dependencies**
   ```bash
   npm install
   ```

3. **Start frontend development server**
   ```bash
   npm start
   ```

The frontend will open at `http://localhost:3000`

## 🔑 Environment Variables

Create a `.env` file in the `backend/` directory with the following variables:

```env
# Database
DATABASE_URL=postgresql://user:password@localhost:5432/gate_rag

# Pinecone Vector DB
PINECONE_API_KEY=your_pinecone_api_key
PINECONE_INDEX=gate-rag
PINECONE_ENV=us-east-1

# Google Gemini API
GEMINI_API_KEY=your_gemini_api_key
GEMINI_MODEL=gemini-2.5-flash

# HuggingFace (for embeddings)
HUGGINGFACE_API_KEY=your_huggingface_api_key
HUGGINGFACE_EMBEDDING_MODEL=all-MiniLM-L6-v2
HUGGINGFACE_LLM_MODEL=TinyLlama/TinyLlama-1.1B-Chat-v1.0
```

## 📁 Project Structure

```
RAG VS/
├── backend/
│   ├── app/
│   │   ├── __init__.py
│   │   ├── config.py
│   │   ├── database.py
│   │   ├── main.py
│   │   ├── models.py
│   │   ├── schemas.py
│   │   ├── routes/
│   │   │   ├── upload.py      # PDF upload and parsing
│   │   │   ├── query.py       # Query and MCQ endpoints
│   │   │   └── documents.py   # Document management
│   │   └── services/
│   │       ├── advanced_pdf_parser.py    # Structure-aware PDF parsing
│   │       ├── semantic_chunker.py       # Intelligent document chunking
│   │       ├── embeddings.py             # Vector embedding generation
│   │       ├── pinecone_service.py       # Vector store operations
│   │       ├── rag_pipeline.py           # RAG query processing
│   │       ├── rag_pipeline_enhanced.py  # Enhanced RAG with citations
│   │       └── ...other services
│   ├── requirements.txt
│   ├── .env                   # Environment variables (not in git)
│   ├── .env.example          # Example environment variables
│   └── create_tables.py      # Database initialization
│
├── my-app/                    # React frontend
│   ├── src/
│   │   ├── components/
│   │   │   ├── uploadbox.js
│   │   │   ├── chatbox.js
│   │   │   └── answerbox.js
│   │   ├── App.js
│   │   └── index.js
│   ├── public/
│   └── package.json
│
├── .gitignore
├── README.md
└── Documentation files
```

## 🔄 API Endpoints

### Document Upload
- **POST** `/upload` - Upload PDF for processing
  - Form data: `subject` (string), `file` (PDF)
  - Returns: Document ID and chunking statistics

### Query Endpoints
- **POST** `/query` - Ask questions about uploaded documents
  - Body: `{question: string, subject: string}`
  - Returns: Generated answer with sources

- **POST** `/mcq` - Generate multiple choice questions
  - Body: `{subject: string, document_id?: number}`
  - Returns: List of MCQ questions

- **POST** `/check-answer` - Validate MCQ answers
  - Body: `{question_id: string, selected_answer: string}`
  - Returns: Correctness and explanation

### Document Management
- **GET** `/documents` - List uploaded documents
- **DELETE** `/documents/{id}` - Delete a document

## 🎯 Key Features Explained

### Advanced PDF Parser
Extracts PDF content with structure preservation:
- Detects headings, paragraphs, lists, and tables
- Maintains hierarchical relationships
- Assigns semantic levels (1-3) to sections
- Returns `PDFSection` objects with metadata

### Semantic Chunker
Intelligent document chunking:
- Respects paragraph boundaries for semantic coherence
- Configurable chunk size (200-800 characters)
- Overlap between chunks for context preservation
- Preserves metadata (page numbers, section titles, hierarchy)

### Hybrid Search
Multiple search strategies:
- **Semantic Search**: Vector similarity in Pinecone
- **BM25 Search**: Keyword-based retrieval
- **Reranking**: LLM-based result reranking for relevance

### MCQ Generation
GATE-style question generation:
- Extracts important concepts from documents
- Generates distractors using semantic similarity
- Validates answer correctness with LLM
- Provides detailed explanations

## 🚀 Usage Examples

### 1. Upload a Document
```python
# Using curl
curl -X POST "http://localhost:8000/upload" \
  -F "subject=DBMS" \
  -F "file=@DBMS_Questions.pdf"
```

### 2. Query the Document
```python
# Using curl
curl -X POST "http://localhost:8000/query" \
  -H "Content-Type: application/json" \
  -d '{
    "question": "What is normalization in databases?",
    "subject": "DBMS"
  }'
```

### 3. Generate MCQs
```python
curl -X POST "http://localhost:8000/mcq" \
  -H "Content-Type: application/json" \
  -d '{
    "subject": "DBMS",
    "document_id": 1
  }'
```

## 📊 Architecture

```
PDF File
   ↓
Advanced PDF Parser (Structure extraction)
   ↓
Semantic Chunker (Context-aware splitting)
   ↓
Embeddings Service (Vector generation)
   ↓
Pinecone (Vector storage)
   ↓
Query → Multi-Query Retrieval → Hybrid Search
   ↓
Retrieved Context → RAG Pipeline → LLM
   ↓
Generated Response with Citations
```

## 🐛 Debugging

### Check Backend Status
```bash
curl http://localhost:8000/docs  # Swagger UI
```

### View Database
```bash
psql postgresql://postgres:postgres123@localhost:5432/gate_rag
```

### Check Pinecone Index
```bash
# View index stats and vectors
python -c "from app.services.pinecone_service import pc; print(pc.Index('gate-rag').describe_index_stats())"
```

## 📝 Development Tips

1. **Hot Reload**: Backend uses `--reload` flag for automatic restart on file changes
2. **CORS Enabled**: Frontend on port 3000 can communicate with backend on port 8000
3. **Database Migrations**: Modify models in `app/models.py` and run `create_tables.py`
4. **Vector Indexing**: Monitor Pinecone usage in console

## 🤝 Contributing

1. Create a feature branch: `git checkout -b feature/your-feature`
2. Commit changes: `git commit -am 'Add new feature'`
3. Push to branch: `git push origin feature/your-feature`
4. Submit a pull request

## 📄 License

This project is licensed under the MIT License.

## 🙋 Support

For issues and questions:
1. Check the documentation files in the root directory
2. Review the `.env.example` for configuration
3. Check backend logs in terminal
4. Verify all services are running (Postgres, Pinecone API)

## 📚 Documentation

- [EXECUTIVE_SUMMARY.md](EXECUTIVE_SUMMARY.md) - High-level overview
- [SYSTEM_ARCHITECTURE_PHASE_8.md](SYSTEM_ARCHITECTURE_PHASE_8.md) - Detailed architecture
- [IMPLEMENTATION_CHECKLIST.md](IMPLEMENTATION_CHECKLIST.md) - Feature checklist
- [QUICK_REFERENCE.md](QUICK_REFERENCE.md) - Quick command reference

---

**Last Updated**: February 2026
**Version**: 1.0.0
