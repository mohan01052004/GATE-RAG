import { useEffect, useState } from "react";
import "./answerbox.css";

export default function AnswerBox({ text }) {
  const [selected, setSelected] = useState({});
  const [showAnswers, setShowAnswers] = useState({});

  useEffect(() => {
    setSelected({});
    setShowAnswers({});
  }, [text]);

  if (!text) {
    return null;
  }

  if (typeof text === "object" && text.kind === "loading") {
    return (
      <div className="answer-box loading">
        <div className="loading-spinner"></div>
        <p>Thinking...</p>
      </div>
    );
  }

  if (typeof text === "object" && text.kind === "mcq") {
    const questions = text.value?.questions || [];

    const handleReset = (key) => {
      const newSelected = { ...selected };
      delete newSelected[key];
      setSelected(newSelected);
      
      const newShowAnswers = { ...showAnswers };
      delete newShowAnswers[key];
      setShowAnswers(newShowAnswers);
    };

    const handleShowAnswer = (key, correctAnswer) => {
      setShowAnswers({ ...showAnswers, [key]: true });
      setSelected({ ...selected, [key]: correctAnswer });
    };

    return (
      <div className="answer-box mcq-container">
        <h3 className="mcq-header">📝 Multiple Choice Questions ({questions.length})</h3>
        
        {questions.map((q, idx) => {
          const key = `q-${idx}`;
          const selectedOption = selected[key];
          const isAnswerShown = showAnswers[key];
          const isCorrect = selectedOption && selectedOption === q.correct_answer;
          const isAnswered = selectedOption !== undefined;

          return (
            <div key={key} className="mcq-question">
              <div className="mcq-question-text">
                <span className="mcq-number">Q{idx + 1}</span>
                {q.question}
              </div>

              <div className="mcq-options">
                {q.options.map((opt) => {
                  const isSelected = selectedOption === opt.label;
                  const isCorrectOption = opt.label === q.correct_answer;
                  
                  let optionClass = "mcq-option";
                  if (isAnswered) {
                    if (isSelected && isCorrect) {
                      optionClass += " correct";
                    } else if (isSelected && !isCorrect) {
                      optionClass += " wrong";
                    } else if (isCorrectOption) {
                      optionClass += " correct-answer";
                    }
                  } else if (isSelected) {
                    optionClass += " selected";
                  }

                  return (
                    <button
                      key={opt.label}
                      className={optionClass}
                      onClick={() => !isAnswered && setSelected({ ...selected, [key]: opt.label })}
                      disabled={isAnswered}
                    >
                      <span className="option-label">{opt.label}</span>
                      <span className="option-text">{opt.text}</span>
                    </button>
                  );
                })}
              </div>

              <div className="mcq-action-buttons">
                {!isAnswered && (
                  <button 
                    className="btn-show-answer"
                    onClick={() => handleShowAnswer(key, q.correct_answer)}
                  >
                    💡 Show Answer & Explanation
                  </button>
                )}
                {isAnswered && (
                  <button 
                    className="btn-reset"
                    onClick={() => handleReset(key)}
                  >
                    🔄 Reset
                  </button>
                )}
              </div>

              {isAnswered && (
                <>
                  <div className={`mcq-result ${isCorrect ? 'correct' : 'wrong'}`}>
                    {isCorrect ? (
                      <>✅ Correct! Well done!</>
                    ) : (
                      <>❌ Incorrect. The correct answer is {q.correct_answer}</>
                    )}
                  </div>
                  {q.explanation && (
                    <div className="mcq-explanation">
                      <div className="explanation-icon">💡</div>
                      <div className="explanation-content">
                        <h4 className="explanation-title">Why is {q.correct_answer} correct?</h4>
                        <p className="explanation-text">{q.explanation}</p>
                      </div>
                    </div>
                  )}
                </>
              )}
            </div>
          );
        })}
      </div>
    );
  }

  if (typeof text === "object" && text.kind === "text") {
    return (
      <div className="answer-box text-answer">
        <div className="answer-icon">🤖</div>
        <div className="answer-content">{text.value}</div>
      </div>
    );
  }

  const value = typeof text === "object" ? JSON.stringify(text, null, 2) : text;

  return (
    <div className="answer-box">
      {value}
    </div>
  );
}
