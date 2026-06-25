import { useEffect, useState } from "react";
import UploadBox from "./components/uploadbox";
import ChatBox from "./components/chatbox";
import AnswerBox from "./components/answerbox";
import PracticeBox from "./components/practicebox";
import { getDocuments } from "./api";
import './App.css';

function App() {
  const [answer, setAnswer] = useState(null);
  const [documentId, setDocumentId] = useState(null);
  const [subject, setSubject] = useState("");
  const [hasDocument, setHasDocument] = useState(false);
  const [documents, setDocuments] = useState([]);
  const [selectedDocumentIds, setSelectedDocumentIds] = useState([]);
  const [activeTab, setActiveTab] = useState("query"); // "query" or "practice"

  const loadDocuments = async () => {
    try {
      const res = await getDocuments();
      setDocuments(res.data?.documents || []);
    } catch {
      setDocuments([]);
    }
  };


  useEffect(() => {
    loadDocuments();
  }, []);

  return (
    <div className="app-container">
      <div className="header">
        <div className="header-icon">🎓</div>
        <h1 className="header-title">GATE RAG Tutor</h1>
        <p className="header-subtitle">Upload your study material and ask questions</p>
      </div>

      <div className="content-container">
        <div className="upload-section">
          <UploadBox
            onUploaded={(docId, subj) => {
              setDocumentId(docId);
              setSubject(subj);
              setHasDocument(true);
              setSelectedDocumentIds([docId]);
              loadDocuments();
            }}
          />
        </div>

        {hasDocument && (
          <div className="mode-tabs">
            <button
              className={`mode-tab ${activeTab === "query" ? "active" : ""}`}
              onClick={() => setActiveTab("query")}
            >
              <span className="tab-icon">💬</span>
              Query Mode
            </button>
            <button
              className={`mode-tab ${activeTab === "practice" ? "active" : ""}`}
              onClick={() => setActiveTab("practice")}
            >
              <span className="tab-icon">📝</span>
              Practice Mode
            </button>
          </div>
        )}

        {!hasDocument && (
          <div className="welcome-message">
            <div className="chat-bubble-icon">💬</div>
            <h2 className="welcome-title">Ready to help you learn!</h2>
            <p className="welcome-text">
              Upload a PDF and start asking questions about your GATE preparation
            </p>
          </div>
        )}

        {hasDocument && activeTab === "query" && (
          <>
            <div className="chat-section">
              <ChatBox
                onAnswer={setAnswer}
                documentId={documentId}
                subject={subject}
                documents={documents}
                selectedDocumentIds={selectedDocumentIds}
                onSelectDocuments={setSelectedDocumentIds}
              />
            </div>

            {answer && (
              <div className="answer-section">
                <AnswerBox text={answer} />
              </div>
            )}
          </>
        )}

        {hasDocument && activeTab === "practice" && (
          <div className="practice-section">
            <PracticeBox
              documentIds={selectedDocumentIds}
              subject={subject}
            />
          </div>
        )}
      </div>
    </div>
  );
}

export default App;
