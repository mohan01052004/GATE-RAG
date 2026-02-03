"""
Practice Problem Generator - Difficulty-Based RAG

Generates practice problems from uploaded content with adjustable difficulty:
- Easy: Basic recall, definitions, simple MCQs
- Medium: Application, understanding, moderate problem-solving
- Hard: Analysis, synthesis, complex multi-step problems
"""

from app.services.rag_pipeline import generate_mcqs
from app.services.hybrid_search import hybrid_search
from app.services.reranker import rerank_results
from app.services.query_expansion import expand_query
from app.services.multi_query_retrieval import multi_query_retrieve, smart_deduplication
from app.schemas import PracticeProblem, MCQOption
from typing import List, Optional
import uuid
import random


def _classify_difficulty_prompt(difficulty: str, question_type: str) -> dict:
    """Get prompt instructions based on difficulty level"""
    
    if difficulty == "easy":
        return {
            "description": "Basic recall and understanding",
            "instructions": [
                "Focus on definitions and fundamental concepts",
                "Use direct, straightforward questions",
                "Test basic knowledge and terminology",
                "Options should be clearly distinct",
                "Avoid tricky or ambiguous phrasing"
            ],
            "example_mcq": "What is the time complexity of binary search? A) O(n) B) O(log n) C) O(n²) D) O(1)",
            "hint_level": "Give clear hints that guide toward the answer"
        }
    elif difficulty == "hard":
        return {
            "description": "Complex analysis and synthesis",
            "instructions": [
                "Require multi-step reasoning",
                "Combine multiple concepts",
                "Include edge cases and advanced scenarios",
                "Options should be subtle and require careful analysis",
                "Test deep understanding and application"
            ],
            "example_mcq": "A cache has 4-way set associativity with 256 sets and 64-byte blocks. If the address is 32 bits, how many tag bits are needed?",
            "hint_level": "Provide minimal hints that encourage independent thinking"
        }
    else:  # medium
        return {
            "description": "Application and moderate problem-solving",
            "instructions": [
                "Test understanding and application",
                "Include moderate problem-solving",
                "Balance between recall and analysis",
                "Options should require some thought",
                "Mix conceptual and practical aspects"
            ],
            "example_mcq": "Which sorting algorithm has the best average-case time complexity? A) Bubble Sort B) Merge Sort C) Quick Sort D) Selection Sort",
            "hint_level": "Provide moderate hints that help without giving away the answer"
        }


def generate_practice_problems(
    topic: Optional[str] = None,
    subject: Optional[str] = None,
    difficulty: str = "medium",
    count: int = 5,
    question_type: str = "mcq",
    document_id: Optional[int] = None,
    document_ids: Optional[List[int]] = None
) -> List[PracticeProblem]:
    """
    Generate practice problems with specified difficulty from uploaded content.
    
    Args:
        topic: Specific topic to generate problems from
        subject: Subject filter
        difficulty: easy, medium, or hard
        count: Number of problems to generate
        question_type: mcq, theory, or numerical
        document_id: Single document to search
        document_ids: Multiple documents to search
    
    Returns:
        List of PracticeProblem objects
    """
    
    # Build search query
    if topic:
        query = f"Generate {difficulty} {question_type} questions on {topic}"
    elif subject:
        query = f"Generate {difficulty} {question_type} questions on {subject}"
    else:
        query = f"Generate {difficulty} {question_type} questions"
    
    # Get difficulty-specific instructions
    diff_config = _classify_difficulty_prompt(difficulty, question_type)
    
    # Retrieve relevant content
    filters = {}
    # Note: Disable subject filter as database subjects don't match user input
    # if subject:
    #     filters["subject"] = subject
    if document_ids:
        filters["document_id"] = {"$in": document_ids}
    elif document_id:
        filters["document_id"] = document_id
    
    # Multi-query retrieval for better coverage
    query_variations = expand_query(query, mode="auto", num_variations=2)
    
    def search_fn(q, k):
        return hybrid_search(q, top_k=k, filters=filters if filters else None)
    
    # Retrieve more content for harder questions
    retrieve_count = {
        "easy": 15,
        "medium": 25,
        "hard": 40
    }.get(difficulty, 25)
    
    candidates = multi_query_retrieve(
        query_variations,
        search_fn,
        top_k_per_query=retrieve_count,
        final_top_k=retrieve_count,
        fusion_method="rrf"
    )
    
    candidates = smart_deduplication(candidates, similarity_threshold=0.90)
    context = rerank_results(query, candidates, top_k=min(len(candidates), retrieve_count))
    context_text = "\n\n".join([c for c in context if c]).strip()
    
    if not context_text:
        # Return empty list if no context
        return []
    
    # Generate problems based on type
    if question_type == "mcq":
        return _generate_mcq_problems(
            context_text, count, difficulty, diff_config, subject, topic
        )
    elif question_type == "theory":
        return _generate_theory_problems(
            context_text, count, difficulty, diff_config, subject, topic
        )
    elif question_type == "numerical":
        return _generate_numerical_problems(
            context_text, count, difficulty, diff_config, subject, topic
        )
    else:
        return []


def _generate_mcq_problems(
    context: str,
    count: int,
    difficulty: str,
    config: dict,
    subject: Optional[str],
    topic: Optional[str]
) -> List[PracticeProblem]:
    """Generate MCQ problems with specified difficulty"""
    
    # Use existing MCQ generation with enhanced prompting for difficulty
    from app.services.rag_pipeline import _generate_with_gemini
    from app.schemas import MCQQuestion, MCQResponse
    import json
    
    prompt = f"""You are a GATE exam practice problem generator. Generate {count} multiple-choice questions.

DIFFICULTY LEVEL: {difficulty.upper()}
{config['description']}

INSTRUCTIONS:
{chr(10).join(f"• {inst}" for inst in config['instructions'])}

EXAMPLE ({difficulty}):
{config['example_mcq']}

CONTEXT FROM STUDY MATERIAL:
{context[:4000]}

Generate exactly {count} questions in this JSON format:
[
  {{
    "question": "Clear, {difficulty}-level question",
    "options": {{
      "A": "First option",
      "B": "Second option",
      "C": "Third option",
      "D": "Fourth option"
    }},
    "correct_answer": "B",
    "explanation": "Detailed explanation with reasoning",
    "hints": ["Hint 1", "Hint 2"]
  }}
]

Generate {count} {difficulty}-difficulty MCQs now (JSON only):"""
    
    result = _generate_with_gemini(prompt, temperature=0.85, max_tokens=6000)
    
    problems = []
    if result and result != "RATE_LIMIT_EXCEEDED":
        try:
            json_match = result.find("[")
            if json_match != -1:
                json_end = result.rfind("]")
                if json_end != -1:
                    json_str = result[json_match:json_end + 1]
                    data = json.loads(json_str)
                    
                    for item in data[:count]:
                        options_dict = item.get("options", {})
                        problems.append(PracticeProblem(
                            id=str(uuid.uuid4()),
                            question=item.get("question", ""),
                            question_type="mcq",
                            difficulty=difficulty,
                            subject=subject,
                            topic=topic,
                            options=[
                                MCQOption(label="A", text=str(options_dict.get("A", ""))),
                                MCQOption(label="B", text=str(options_dict.get("B", ""))),
                                MCQOption(label="C", text=str(options_dict.get("C", ""))),
                                MCQOption(label="D", text=str(options_dict.get("D", "")))
                            ],
                            correct_answer=item.get("correct_answer", "A"),
                            solution=item.get("explanation", ""),
                            hints=item.get("hints", [])
                        ))
        except:
            pass
    
    # Fallback: generate simple problems from context
    if not problems:
        problems = _generate_fallback_mcqs(context, count, difficulty, subject, topic)
    
    return problems


def _generate_theory_problems(
    context: str,
    count: int,
    difficulty: str,
    config: dict,
    subject: Optional[str],
    topic: Optional[str]
) -> List[PracticeProblem]:
    """Generate theory/explanation problems"""
    
    from app.services.rag_pipeline import _generate_with_gemini
    
    prompt = f"""Generate {count} {difficulty}-level theory questions that require detailed explanations.

DIFFICULTY: {difficulty.upper()}
{chr(10).join(f"• {inst}" for inst in config['instructions'])}

CONTEXT:
{context[:4000]}

For each question, provide:
1. A clear question
2. The correct answer/explanation
3. {config['hint_level']}

Generate exactly {count} questions in this JSON format:
[
  {{
    "question": "Your theory question here",
    "correct_answer": "Detailed correct answer with explanation",
    "hints": ["Hint 1", "Hint 2"]
  }}
]

Generate {count} theory questions now (JSON only):"""
    
    result = _generate_with_gemini(prompt, temperature=0.8, max_tokens=5000)
    
    problems = []
    if result and result != "RATE_LIMIT_EXCEEDED":
        try:
            json_match = result.find("[")
            if json_match != -1:
                json_end = result.rfind("]")
                if json_end != -1:
                    json_str = result[json_match:json_end + 1]
                    data = json.loads(json_str)
                    
                    for item in data[:count]:
                        problems.append(PracticeProblem(
                            id=str(uuid.uuid4()),
                            question=item.get("question", ""),
                            question_type="theory",
                            difficulty=difficulty,
                            subject=subject,
                            topic=topic,
                            correct_answer=item.get("correct_answer", ""),
                            solution=item.get("correct_answer", ""),
                            hints=item.get("hints", [])
                        ))
        except Exception as e:
            print(f"Error parsing theory problems: {e}")
            print(f"LLM result: {result[:500]}...")
            pass
    
    # Fallback if LLM generation failed
    if not problems:
        problems = _generate_fallback_theory(context, count, difficulty, subject, topic)
    
    return problems


def _generate_numerical_problems(
    context: str,
    count: int,
    difficulty: str,
    config: dict,
    subject: Optional[str],
    topic: Optional[str]
) -> List[PracticeProblem]:
    """Generate numerical/calculation problems"""
    
    from app.services.rag_pipeline import _generate_with_gemini
    
    prompt = f"""Generate {count} {difficulty}-level numerical problems requiring calculations.

DIFFICULTY: {difficulty.upper()}
{chr(10).join(f"• {inst}" for inst in config['instructions'])}

CONTEXT:
{context[:4000]}

For each problem:
1. Clear problem statement with given values
2. Step-by-step solution
3. Final numerical answer
4. {config['hint_level']}

Generate exactly {count} numerical problems in this JSON format:
[
  {{
    "question": "Problem statement with values",
    "correct_answer": "Final numerical answer (e.g., '42' or '3.14')",
    "solution": "Step-by-step solution process",
    "hints": ["Hint 1", "Hint 2"]
  }}
]

Generate {count} numerical problems now (JSON only):"""
    
    result = _generate_with_gemini(prompt, temperature=0.7, max_tokens=5000)
    
    problems = []
    if result and result != "RATE_LIMIT_EXCEEDED":
        try:
            json_match = result.find("[")
            if json_match != -1:
                json_end = result.rfind("]")
                if json_end != -1:
                    json_str = result[json_match:json_end + 1]
                    data = json.loads(json_str)
                    
                    for item in data[:count]:
                        problems.append(PracticeProblem(
                            id=str(uuid.uuid4()),
                            question=item.get("question", ""),
                            question_type="numerical",
                            difficulty=difficulty,
                            subject=subject,
                            topic=topic,
                            correct_answer=str(item.get("correct_answer", "")),
                            solution=item.get("solution", ""),
                            hints=item.get("hints", [])
                        ))
        except Exception as e:
            print(f"Error parsing numerical problems: {e}")
            print(f"LLM result: {result[:500]}...")
            pass
    
    # Fallback if LLM generation failed
    if not problems:
        problems = _generate_fallback_numerical(context, count, difficulty, subject, topic)
    
    return problems


def _generate_fallback_mcqs(
    context: str,
    count: int,
    difficulty: str,
    subject: Optional[str],
    topic: Optional[str]
) -> List[PracticeProblem]:
    """Fallback MCQ generation when LLM fails"""
    
    sentences = [s.strip() for s in context.split('.') if len(s.strip()) > 30]
    problems = []
    
    for i in range(min(count, len(sentences))):
        sentence = sentences[i]
        # Randomize correct answer instead of always "A"
        correct_option = random.choice(["A", "B", "C", "D"])
        
        problems.append(PracticeProblem(
            id=str(uuid.uuid4()),
            question=f"Q{i+1}: Based on the study material, which statement is correct about: {sentence[:80]}...?",
            question_type="mcq",
            difficulty=difficulty,
            subject=subject,
            topic=topic,
            options=[
                MCQOption(label="A", text="Option A based on context"),
                MCQOption(label="B", text="Option B based on context"),
                MCQOption(label="C", text="Option C based on context"),
                MCQOption(label="D", text="Insufficient information")
            ],
            correct_answer=correct_option,
            solution=f"Based on the provided context in the study material. The correct answer is option {correct_option}.",
            hints=["Review the relevant section", "Focus on key concepts"]
        ))
    
    return problems


def _generate_fallback_theory(
    context: str,
    count: int,
    difficulty: str,
    subject: Optional[str],
    topic: Optional[str]
) -> List[PracticeProblem]:
    """Fallback theory question generation when LLM fails - only if context is suitable"""
    
    import re as regex
    
    # Check if context has meaningful theory content (definitions, explanations, concepts)
    theory_indicators = [
        'definition', 'concept', 'explain', 'description', 'principle',
        'theory', 'algorithm', 'process', 'method', 'technique', 'approach',
        'property', 'characteristic', 'feature', 'purpose', 'function'
    ]
    
    context_lower = context.lower()
    theory_count = sum(1 for indicator in theory_indicators if indicator in context_lower)
    
    # Only generate if we have enough theory-related content
    if theory_count < 2:
        return []  # Return empty if not enough theory content
    
    sentences = [s.strip() for s in context.split('.') if len(s.strip()) > 50 and len(s.strip()) < 500]
    
    if not sentences:
        return []
    
    problems = []
    
    for i in range(min(count, len(sentences))):
        sentence = sentences[i]
        
        # Only use sentences that contain theory indicators
        if any(indicator in sentence.lower() for indicator in theory_indicators):
            problems.append(PracticeProblem(
                id=str(uuid.uuid4()),
                question=f"Explain or describe the following concept based on the study material: {sentence[:100]}...",
                question_type="theory",
                difficulty=difficulty,
                subject=subject,
                topic=topic,
                correct_answer=sentence,
                solution=f"Detailed explanation: {sentence}",
                hints=["Identify key concepts", "Provide definitions and examples", "Explain the significance"]
            ))
    
    return problems


def _generate_fallback_numerical(
    context: str,
    count: int,
    difficulty: str,
    subject: Optional[str],
    topic: Optional[str]
) -> List[PracticeProblem]:
    """Fallback numerical question generation when LLM fails - only if context has relevant numbers"""
    
    import re as regex
    
    # Look for number patterns in context that suggest calculations or technical values
    # Examples: time complexity O(n), cache size 256KB, algorithm runs in 2.5ms, etc.
    number_patterns = [
        r'(\d+(?:\.\d+)?)\s*(ms|seconds?|minutes?|hours?|us|ns)',  # Time values
        r'(\d+(?:\.\d+)?)\s*(kb|mb|gb|bytes?)',  # Size values
        r'O\s*\(\s*([n\d+\-\*/^]+)\s*\)',  # Big O notation
        r'(\d+(?:\.\d+)?)\s*(%|percent)',  # Percentages
        r'(\d+(?:\.\d+)?)\s*x\s*(\d+(?:\.\d+)?)',  # Dimensions
    ]
    
    found_patterns = []
    for pattern in number_patterns:
        found_patterns.extend(regex.findall(pattern, context, regex.IGNORECASE))
    
    # If we didn't find meaningful numerical content, return empty
    if not found_patterns:
        return []
    
    # Try to extract meaningful numerical contexts
    sentences = [s.strip() for s in context.split('.') if any(c.isdigit() for c in s) and len(s.strip()) > 20]
    
    if not sentences:
        return []
    
    problems = []
    
    for i in range(min(count, len(sentences))):
        sentence = sentences[i]
        
        problems.append(PracticeProblem(
            id=str(uuid.uuid4()),
            question=f"Based on the study material, analyze or calculate: {sentence[:80]}...",
            question_type="numerical",
            difficulty=difficulty,
            subject=subject,
            topic=topic,
            correct_answer="[Calculate based on the given context in study material]",
            solution=f"Reference from study material: {sentence}",
            hints=["Carefully read the problem statement", "Identify given values and required calculation", "Apply relevant formulas or concepts from the study material"]
        ))
    
    return problems
