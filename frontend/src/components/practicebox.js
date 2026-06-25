import { useState, useEffect } from "react";
import { generatePractice, submitPractice } from "../api";
import "./practicebox.css";

export default function PracticeBox({ subject, documentId, documents, selectedDocumentIds }) {
  const [difficulty, setDifficulty] = useState("medium");
  const [questionType, setQuestionType] = useState("mcq");
  const [count, setCount] = useState(5);
  const [problems, setProblems] = useState([]);
  const [currentIndex, setCurrentIndex] = useState(0);
  const [userAnswer, setUserAnswer] = useState("");
  const [showSolution, setShowSolution] = useState(false);
  const [showHints, setShowHints] = useState(false);
  const [feedback, setFeedback] = useState(null);
  const [isGenerating, setIsGenerating] = useState(false);
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [startTime, setStartTime] = useState(null);
  const [score, setScore] = useState(null);

  const currentProblem = problems[currentIndex];

  const handleGenerate = async () => {
    setIsGenerating(true);
    setProblems([]);
    setCurrentIndex(0);
    setFeedback(null);
    setShowSolution(false);
    setShowHints(false);
    setUserAnswer("");
    setScore(null);

    try {
      const res = await generatePractice({
        subject,
        difficulty,
        count: parseInt(count),
        question_type: questionType,
        document_id: documentId,
        document_ids: selectedDocumentIds && selectedDocumentIds.length ? selectedDocumentIds : null
      });
      setProblems(res.data.problems || []);
      setStartTime(Date.now());
    } catch (error) {
      const errorMsg = error.response?.data?.detail || "Failed to generate practice problems. Try again.";
      alert(errorMsg);
    } finally {
      setIsGenerating(false);
    }
  };

  const handleSubmit = async () => {
    if (!userAnswer.trim()) {
      alert("Please provide an answer");
      return;
    }

    setIsSubmitting(true);
    const timeTaken = Math.floor((Date.now() - startTime) / 1000);

    try {
      const res = await submitPractice({
        problem_id: currentProblem.id,
        question: currentProblem.question,
        question_type: currentProblem.question_type,
        difficulty: currentProblem.difficulty,
        subject: currentProblem.subject,
        topic: currentProblem.topic,
        user_answer: userAnswer,
        correct_answer: currentProblem.correct_answer,
        time_taken: timeTaken
      });
      
      setFeedback(res.data);
      setScore(res.data.score);
      setShowSolution(true);
    } catch (error) {
      alert("Submission failed. Try again.");
    } finally {
      setIsSubmitting(false);
    }
  };

  const handleNext = () => {
    if (currentIndex < problems.length - 1) {
      setCurrentIndex(currentIndex + 1);
      setUserAnswer("");
      setShowSolution(false);
      setShowHints(false);
      setFeedback(null);
      setScore(null);
      setStartTime(Date.now());
    }
  };

  const handlePrevious = () => {
    if (currentIndex > 0) {
      setCurrentIndex(currentIndex - 1);
      setUserAnswer("");
      setShowSolution(false);
      setShowHints(false);
      setFeedback(null);
      setScore(null);
      setStartTime(Date.now());
    }
  };

  const handleReset = () => {
    setProblems([]);
    setCurrentIndex(0);
    setUserAnswer("");
    setShowSolution(false);
    setShowHints(false);
    setFeedback(null);
    setScore(null);
    setStartTime(null);
  };

  return (
    <div className="practicebox-container">
      <div className="practicebox-header">
        <h2>🎯 Practice Mode</h2>
        <p>Generate custom practice problems with adjustable difficulty</p>
      </div>

      <div className="practicebox-controls">
        <div className="practicebox-control-group">
          <label>Difficulty</label>
          <select value={difficulty} onChange={(e) => setDifficulty(e.target.value)}>
            <option value="easy">Easy</option>
            <option value="medium">Medium</option>
            <option value="hard">Hard</option>
          </select>
        </div>

        <div className="practicebox-control-group">
          <label>Type</label>
          <select value={questionType} onChange={(e) => setQuestionType(e.target.value)}>
            <option value="mcq">MCQ</option>
            <option value="theory">Theory</option>
            <option value="numerical">Numerical</option>
          </select>
        </div>

        <div className="practicebox-control-group">
          <label>Count</label>
          <input
            type="number"
            min="1"
            max="20"
            value={count}
            onChange={(e) => setCount(e.target.value)}
          />
        </div>

        <button 
          className="practicebox-generate-button"
          onClick={handleGenerate}
          disabled={isGenerating}
        >
          {isGenerating ? "Generating..." : "Generate Problems"}
        </button>
      </div>

      {problems.length > 0 && (
        <div className="practicebox-problem-area">
          <div className="practicebox-progress">
            Problem {currentIndex + 1} of {problems.length}
            {currentProblem && (
              <span className={`practicebox-difficulty-badge ${currentProblem.difficulty}`}>
                {currentProblem.difficulty.toUpperCase()}
              </span>
            )}
          </div>

          <div className="practicebox-question">
            <h3>{currentProblem.question}</h3>
          </div>

          {currentProblem.question_type === "mcq" && currentProblem.options && (
            <div className="practicebox-options">
              {currentProblem.options.map((option) => (
                <label key={option.label} className="practicebox-option">
                  <input
                    type="radio"
                    name="answer"
                    value={option.label}
                    checked={userAnswer === option.label}
                    onChange={(e) => setUserAnswer(e.target.value)}
                    disabled={showSolution}
                  />
                  <span>{option.label}. {option.text}</span>
                </label>
              ))}
            </div>
          )}

          {currentProblem.question_type !== "mcq" && (
            <div className="practicebox-textarea-wrapper">
              <textarea
                className="practicebox-textarea"
                value={userAnswer}
                onChange={(e) => setUserAnswer(e.target.value)}
                placeholder="Enter your answer here..."
                rows="6"
                disabled={showSolution}
              />
            </div>
          )}

          {!showSolution && (
            <div className="practicebox-actions">
              <button 
                className="practicebox-hint-button"
                onClick={() => setShowHints(!showHints)}
              >
                {showHints ? "Hide" : "Show"} Hints 💡
              </button>
              <button 
                className="practicebox-submit-button"
                onClick={handleSubmit}
                disabled={!userAnswer.trim() || isSubmitting}
              >
                {isSubmitting ? "Submitting..." : "Submit Answer"}
              </button>
            </div>
          )}

          {showHints && currentProblem.hints && currentProblem.hints.length > 0 && (
            <div className="practicebox-hints">
              <h4>💡 Hints:</h4>
              <ul>
                {currentProblem.hints.map((hint, idx) => (
                  <li key={idx}>{hint}</li>
                ))}
              </ul>
            </div>
          )}

          {feedback && (
            <div className={`practicebox-feedback ${feedback.is_correct ? "correct" : "incorrect"}`}>
              <div className="practicebox-feedback-header">
                <strong>{feedback.feedback}</strong>
                {score !== null && <span className="practicebox-score">Score: {score}/100</span>}
              </div>
              <p><strong>Correct Answer:</strong> {feedback.correct_answer}</p>
            </div>
          )}

          {showSolution && currentProblem.solution && (
            <div className="practicebox-solution">
              <h4>📖 Solution:</h4>
              <p>{currentProblem.solution}</p>
            </div>
          )}

          <div className="practicebox-navigation">
            <button 
              onClick={handlePrevious} 
              disabled={currentIndex === 0}
              className="practicebox-nav-button"
            >
              ← Previous
            </button>
            <button 
              onClick={handleReset}
              className="practicebox-nav-button practicebox-reset-button"
            >
              🔄 Reset
            </button>
            <button 
              onClick={handleNext} 
              disabled={currentIndex === problems.length - 1}
              className="practicebox-nav-button"
            >
              Next →
            </button>
          </div>
        </div>
      )}

      {problems.length === 0 && !isGenerating && (
        <div className="practicebox-empty">
          <p>Configure settings above and click "Generate Problems" to start practicing</p>
        </div>
      )}
    </div>
  );
}
