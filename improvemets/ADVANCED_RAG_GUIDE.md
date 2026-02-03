# Advanced RAG Techniques - Implementation Guide

## Overview

This document describes three advanced retrieval-augmented generation techniques implemented in the system:

1. **Self-Query RAG** - Extract structured filters from natural language queries
2. **Hypothetical Document Embeddings (HyDE)** - Generate hypothetical answers for better retrieval
3. **RAG Fusion** - Combine multiple retrieval strategies using Reciprocal Rank Fusion

---

## 1. Self-Query RAG

### Purpose
Automatically extract structured metadata and filters from natural language queries to enable precise routing and filtering.

### Features
- **Automatic Filter Extraction**: Identifies difficulty level, topic, question type, chapter, concepts
- **Dual Extraction Strategy**: LLM-based (precise) + Rule-based fallback (fast)
- **Database Routing**: Converts natural language constraints to database query filters

### Usage

```python
from app.services.self_query import extract_filters, route_query

# Extract filters from query
query = "Show me hard MCQ problems on algorithms from chapter 3"
result = extract_filters(query)

print(result)
# Output:
# {
#   "core_query": "Show me MCQ problems on algorithms",
#   "filters": {
#     "difficulty": "hard",
#     "type": "mcq",
#     "topic": "algorithms",
#     "chapter": "chapter 3"
#   },
#   "confidence": 0.85
# }

# Or use route_query for one-step processing
processed_query, db_filters = route_query(query)
# processed_query: "Show me MCQ problems on algorithms"
# db_filters: {"difficulty": "hard", "question_type": "mcq", ...}
```

### Supported Filters

| Filter | Examples | Extracted As |
|--------|----------|--------------|
| Difficulty | easy, basic, medium, intermediate, hard, advanced | `difficulty` |
| Question Type | mcq, theory, numerical, coding | `type` |
| Chapter/Topic | chapter on algorithms, module basics | `chapter` |
| Time Limit | 30 minutes, within 5 mins | `time_limit` |
| Concepts | graph, sorting, searching | `concepts` |

### Configuration

In `app/services/self_query.py`:

```python
# Use LLM for extraction (more accurate but slower)
extract_filters(query, use_llm=True)

# Use rule-based fallback (faster)
extract_filters(query, use_llm=False)
```

### How It Works

1. **Rule-Based Stage** (fast):
   - Uses regex patterns to identify common difficulty/type/topic terms
   - Removes matched patterns from core query
   - Returns extracted filters

2. **LLM Stage** (optional, more precise):
   - Sends structured prompt to Gemini
   - Asks LLM to identify filters and core query
   - Returns JSON with filters and confidence score
   - Falls back to rule-based if LLM fails or confidence < 0.5

---

## 2. Hypothetical Document Embeddings (HyDE)

### Purpose
Generate hypothetical documents/answers that could answer a user's query to improve retrieval quality by bridging the gap between query language and document language.

### Key Insight
- **Problem**: User queries often use different language than documents
  - Query: "optimize database access"
  - Document: "caching strategies to prevent redundant queries"
  
- **Solution**: Generate hypothetical answers in document-like language, then retrieve using those embeddings

### Usage

```python
from app.services.hyde import generate_hypothetical_documents, get_hyde_embeddings

# Generate hypothetical documents
query = "How to optimize database queries?"
docs = generate_hypothetical_documents(query, num_docs=5)

print(docs)
# [
#   "Use indexing on frequently queried columns to speed up retrieval...",
#   "Query optimization involves analyzing execution plans...",
#   "Caching query results prevents redundant database accesses...",
#   ...
# ]

# Get embeddings of hypothetical documents
hyde_docs, embeddings = get_hyde_embeddings(query, num_docs=5)

# Get average HyDE embedding for combined retrieval
avg_embedding = get_average_hyde_embedding(query)

# Combine query and HyDE embeddings for retrieval
combined_emb = hybrid_query_embedding(
    query, 
    original_query_embedding,
    hyde_weight=0.3
)
```

### Document Generation Strategies

HyDE uses adaptive generation based on query type:

| Query Pattern | Generated Doc Type |
|---------------|------------------|
| What/How/Explain | Explanatory documents with detailed concepts |
| Best/Improve/Optimize | Best-practice and optimization guides |
| Example/Case/Real | Practical examples and case studies |
| Error/Problem/Fix | Troubleshooting and debugging guides |

### Performance Tips

- **Fast Mode** (Rule-based): Use for real-time queries
- **Accurate Mode** (LLM): Use for complex or ambiguous queries
- **Hybrid Weight**: Default 0.3 (30% HyDE, 70% original query)
  - Lower weights (0.1-0.2): Trust original query more
  - Higher weights (0.4-0.5): Trust hypothetical documents more

---

## 3. RAG Fusion

### Purpose
Combine results from multiple retrieval strategies using Reciprocal Rank Fusion (RRF) to get the best of all approaches.

### Key Techniques

#### a) Reciprocal Rank Fusion (RRF)
Combines multiple ranked lists by assigning scores based on rank position.

**Formula**: 
```
score(doc) = Σ 1 / (k + rank)
```
where k=60 (default) and rank starts from 1

**Advantage**: Works with different score ranges, emphasizes consensus among methods

#### b) Weighted Score Fusion
Normalizes scores from each method and combines with weights.

**Advantage**: Direct control over method importance

#### c) Deduplication
Removes near-duplicate results to ensure diversity.

#### d) Diversity Ranking (Optional)
Promotes documents covering different concepts/topics.

### Usage

```python
from app.services.rag_fusion import (
    fuse_retrieval_results,
    apply_rag_fusion,
    reciprocal_rank_fusion
)

# Method 1: Direct RRF with rank lists
bm25_results = [("doc1", 0.95), ("doc2", 0.87)]
semantic_results = [("doc3", 0.92), ("doc1", 0.88)]
hyde_results = [("doc1", 0.90), ("doc2", 0.85)]

fused = reciprocal_rank_fusion(
    [bm25_results, semantic_results, hyde_results]
)
# Returns: [("doc1", 0.0484), ("doc3", 0.0323), ...]

# Method 2: Using helper function
bm25_docs = [("doc1", 0.95, {"text": "..."}), ...]
semantic_docs = [("doc1", 0.88, {"text": "..."}), ...]

fused = fuse_retrieval_results(
    bm25_results=bm25_docs,
    semantic_results=semantic_docs,
    hyde_results=hyde_results_docs,
    strategy="rrf"  # or "weighted"
)

# Method 3: Complete pipeline
result_dict = {
    "bm25": bm25_results,
    "semantic": semantic_results,
    "hyde": hyde_results,
    "self_query": self_query_results
}

final = apply_rag_fusion(
    result_dict,
    deduplicate=True,
    promote_diversity=False
)
```

### Fusion Strategies Comparison

| Strategy | Pros | Cons | Use Case |
|----------|------|------|----------|
| **RRF** | Works with any score range, emphasizes consensus | Sensitive to result set sizes | Most scenarios |
| **Weighted** | Direct control, interpretable | Requires tuning weights | When you know method reliability |
| **Diversity** | Promotes variety, prevents redundancy | Slower computation | Broad topic coverage needed |

### Score Interpretation

After fusion:
- **High Score (0.04+)**: Appears in multiple retrieval methods, high confidence
- **Medium Score (0.02-0.04)**: Appears in some methods or mid-ranking
- **Low Score (<0.02)**: Appears in single method or low-ranking

---

## 4. Integrated Advanced RAG Pipeline

### Architecture

```
User Query
    ↓
Self-Query: Extract Filters
    ↓
Parallel Retrieval:
    ├─ BM25 Search (keyword-based)
    ├─ Semantic Search (embedding-based)
    ├─ HyDE Retrieval (hypothetical embeddings)
    └─ Self-Query Filtering (metadata-based)
    ↓
RAG Fusion: Combine Using RRF
    ↓
Deduplication: Remove Duplicates
    ↓
Optional: Diversity Ranking
    ↓
Return Top-K Results with Metadata
```

### API Endpoint

```python
@router.post("/advanced-retrieve")
async def advanced_retrieve(req: QueryRequest):
    """
    Advanced RAG retrieval with all three techniques.
    
    QueryRequest fields:
    - question: User query
    - document_ids: Restrict to specific documents
    - use_self_query: Enable Self-Query (default: True)
    - use_hyde: Enable HyDE (default: True)
    - use_fusion: Enable RAG Fusion (default: True)
    - enable_advanced_rag: Activate advanced pipeline (default: False)
    """
    results = await advanced_retrieval(
        query=req.question,
        document_ids=req.document_ids,
        use_self_query=req.use_self_query,
        use_hyde=req.use_hyde,
        use_fusion=req.use_fusion
    )
    
    return {
        "results": results,
        "stats": get_retrieval_stats(results),
        "count": len(results)
    }
```

### Usage Example

```bash
curl -X POST http://localhost:8000/query/advanced-retrieve \
  -H "Content-Type: application/json" \
  -d '{
    "question": "Show me hard MCQ problems on sorting algorithms",
    "document_ids": [1, 2, 3],
    "use_self_query": true,
    "use_hyde": true,
    "use_fusion": true,
    "enable_advanced_rag": true
  }'
```

### Response Format

```json
{
  "results": [
    {
      "id": "doc1",
      "fusion_score": 0.0484,
      "text": "...",
      "topic": "sorting",
      "difficulty": "hard",
      "concepts": ["quicksort", "mergesort"],
      "semantic_score": 0.88,
      "bm25_score": 0.95
    },
    ...
  ],
  "stats": {
    "result_count": 10,
    "avg_score": 0.0356,
    "unique_documents": 10,
    "topics_covered": ["sorting", "searching"],
    "has_hyde": true,
    "has_self_query_filters": true
  },
  "count": 10
}
```

---

## 5. Performance Optimization

### Query Time

Approximate latencies (single query, no parallelization):
- Self-Query: 10-50ms (rule-based) or 500-2000ms (LLM)
- BM25 Search: 50-200ms
- Semantic Search: 100-500ms
- HyDE Generation & Retrieval: 2-5 seconds
- RAG Fusion: 50-100ms
- **Total**: 2-7 seconds (with HyDE), 0.5-1 second (without HyDE)

### Optimization Strategies

1. **Disable HyDE for speed**: Use only Self-Query + Hybrid Search for real-time queries
   ```python
   await advanced_retrieval(query, use_hyde=False)
   ```

2. **Use rule-based Self-Query**: 50x faster than LLM
   ```python
   extract_filters(query, use_llm=False)
   ```

3. **Reduce top_k**: Retrieve fewer candidates for fusion
   ```python
   await advanced_retrieval(query, top_k=5)  # Instead of 10
   ```

4. **Cache results**: Store frequently asked queries
   - Store extracted filters for similar queries
   - Cache HyDE embeddings for common topics

5. **Parallel execution**: All retrieval methods already run in parallel

### Quality Tuning

1. **RRF k parameter**: Controls ranking emphasis
   - Lower k=20: Emphasizes top results
   - Higher k=100: More balanced ranking

2. **HyDE weight**: Control query vs. hypothetical document emphasis
   - 0.1: Trust original query more
   - 0.5: Equal weight
   - 0.8: Trust hypothetical documents more

3. **Diversity weight**: Promote topic diversity in results
   - 0.0: No diversity promotion
   - 0.2-0.3: Balanced diversity and relevance
   - 0.5: Heavy diversity promotion

---

## 6. Troubleshooting

### Issue: Empty Results

**Causes**:
1. Self-Query filters too restrictive
2. No documents match extracted filters

**Solutions**:
```python
# Disable Self-Query filtering
advanced_retrieval(query, use_self_query=False)

# Or relax filters manually
filters = extract_filters(query)
filters['filters'].clear()  # Remove all filters
```

### Issue: Low Relevance Scores

**Causes**:
1. Query language very different from documents
2. Few documents match all retrieval methods

**Solutions**:
```python
# Use HyDE to bridge language gap
advanced_retrieval(query, use_hyde=True)

# Or increase HyDE weight
hybrid_query_embedding(query, orig_emb, hyde_weight=0.5)
```

### Issue: Too Many Duplicate Results

**Causes**:
1. Multiple retrieval methods returning same document
2. Deduplication threshold too high

**Solutions**:
```python
# Enable deduplication with stricter threshold
fused = apply_rag_fusion(results, deduplicate=True)

# Or manually deduplicate
deduplicated = deduplicate_fused_results(
    fused,
    similarity_threshold=0.85
)
```

### Issue: Slow Performance

**Causes**:
1. HyDE generation is slowest component (2-5s)
2. All retrieval methods running in sequence instead of parallel

**Solutions**:
```python
# Disable HyDE for real-time queries
advanced_retrieval(query, use_hyde=False)

# Or use lighter HyDE config
get_hyde_embeddings(query, num_docs=3)  # Instead of 5
```

---

## 7. Integration with Existing System

### In Query Pipeline

The advanced RAG is optional and can be integrated into existing pipeline:

```python
# Old way (still works)
answer = generate_theory_answer(query)

# New way with advanced RAG
retrieved = await advanced_retrieval(query)
context = "\n".join(r['text'] for r in retrieved[:3])
answer = generate_theory_answer_with_context(query, context)
```

### In Practice Mode

Practice question generation can use advanced retrieval for context:

```python
from app.services.advanced_rag import advanced_retrieval

async def generate_practice_problems(query, question_type):
    # Use advanced RAG to get relevant documents
    results = await advanced_retrieval(query, use_hyde=True)
    context = [r['text'] for r in results[:3]]
    
    # Generate problems from context
    return generate_from_context(context, question_type)
```

---

## 8. Future Enhancements

Potential improvements to implement:

1. **Query Intent Classification**: Identify whether user wants:
   - Search (retrieval-focused)
   - Explanation (generation-focused)
   - Comparison (multiple docs)
   
2. **Adaptive Strategies**: Choose retrieval methods based on query type
   - Simple queries: BM25 only (fastest)
   - Complex queries: All methods with HyDE (most thorough)
   
3. **Result Prediction**: Estimate confidence before retrieval
   - Decide whether to use expensive HyDE
   
4. **User Feedback Loop**: Learn from user interactions
   - If user ignores top results, adjust strategy
   - Learn document relevance patterns

5. **Cross-Lingual Support**: Handle queries in multiple languages
   - Translate queries, retrieve, translate results

---

## Summary

The three advanced RAG techniques work together:

1. **Self-Query** routes queries intelligently
2. **HyDE** bridges language gaps in retrieval
3. **RAG Fusion** combines multiple strategies

Together they provide:
- ✅ Better precision (Self-Query filtering)
- ✅ Better recall (HyDE + multiple methods)
- ✅ Better ranking (RRF fusion)
- ✅ Better diversity (deduplication + diversity ranking)

**Result**: More relevant, diverse, and comprehensive retrieval for complex queries.
