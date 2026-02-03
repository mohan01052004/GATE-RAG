import { useState } from "react";
import { askQuestion, getMcqs } from "../api";
import "./chatbox.css";

export default function ChatBox({
  onAnswer,
  documentId,
  subject,
  documents = [],
  selectedDocumentIds = [],
  onSelectDocuments
}) {
  const [q, setQ] = useState("");
  const [isLoading, setIsLoading] = useState(false);
  const [showDocPanel, setShowDocPanel] = useState(false);
  const [tempSelectedIds, setTempSelectedIds] = useState([]);

  const effectiveSelectedIds = selectedDocumentIds.length
    ? selectedDocumentIds
    : (documentId ? [documentId] : []);

  const handleOpenPanel = () => {
    setTempSelectedIds(effectiveSelectedIds);
    setShowDocPanel(true);
  };

  const handleDocumentToggle = (docId) => {
    setTempSelectedIds(prev => 
      prev.includes(docId) 
        ? prev.filter(id => id !== docId)
        : [...prev, docId]
    );
  };

  const handleSearchAllToggle = (checked) => {
    setTempSelectedIds(checked ? [] : tempSelectedIds);
  };

  const handleApplySelection = () => {
    if (onSelectDocuments) {
      onSelectDocuments(tempSelectedIds);
    }
    setShowDocPanel(false);
  };

  const handleCancelSelection = () => {
    setShowDocPanel(false);
  };

  const ask = async () => {
    if (!q.trim()) return;

    setIsLoading(true);
    onAnswer({ kind: "loading" });

    const isMcq = q.toLowerCase().includes("mcq");
    const docIds = effectiveSelectedIds.length ? effectiveSelectedIds : null;
    const subjectFilter = docIds && docIds.length === 1 ? subject : null;

    try {
      if (isMcq) {
        const res = await getMcqs(q, {
          subject: subjectFilter,
          document_id: docIds && docIds.length === 1 ? docIds[0] : null,
          document_ids: docIds
        });
        onAnswer({ kind: "mcq", value: res.data });
      } else {
        const res = await askQuestion(q, {
          subject: subjectFilter,
          document_id: docIds && docIds.length === 1 ? docIds[0] : null,
          document_ids: docIds
        });
        onAnswer({ kind: "text", value: res.data.answer });
      }
    } catch (error) {
      const errorMsg = error.response?.data?.detail || error.message || "An error occurred";
      if (error.response?.status === 429 || errorMsg.toLowerCase().includes("rate") || errorMsg.toLowerCase().includes("limit")) {
        onAnswer({ kind: "text", value: "⚠️ Rate limit reached. Please wait a moment and try again." });
      } else {
        onAnswer({ kind: "text", value: `❌ Error: ${errorMsg}` });
      }
    } finally {
      setIsLoading(false);
    }
  };

  const handleKeyPress = (e) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      ask();
    }
  };

  return (
    <div className="chatbox-container">
      <div className="chatbox-documents">
        <div className="chatbox-documents-header">
          <label className="chatbox-documents-label">Search documents</label>
          <button 
            className="chatbox-documents-button"
            onClick={handleOpenPanel}
            type="button"
          >
            {effectiveSelectedIds.length === 0 
              ? "All documents" 
              : `${effectiveSelectedIds.length} selected`}
          </button>
        </div>
        
        {showDocPanel && (
          <div className="chatbox-documents-panel">
            <label className="chatbox-documents-checkbox-item chatbox-documents-all">
              <input
                type="checkbox"
                checked={tempSelectedIds.length === 0}
                onChange={(e) => handleSearchAllToggle(e.target.checked)}
              />
              <span>Search all documents</span>
            </label>
            
            <div className="chatbox-documents-divider" />
            
            <div className="chatbox-documents-list">
              {documents.map((doc) => (
                <label key={doc.id} className="chatbox-documents-checkbox-item">
                  <input
                    type="checkbox"
                    checked={tempSelectedIds.includes(doc.id)}
                    onChange={() => handleDocumentToggle(doc.id)}
                    disabled={tempSelectedIds.length === 0}
                  />
                  <span>{doc.subject ? `${doc.subject} — ` : ""}{doc.filename}</span>
                </label>
              ))}
            </div>
            
            <div className="chatbox-documents-actions">
              <button 
                className="chatbox-documents-action-cancel"
                onClick={handleCancelSelection}
                type="button"
              >
                Cancel
              </button>
              <button 
                className="chatbox-documents-action-ok"
                onClick={handleApplySelection}
                type="button"
              >
                OK
              </button>
            </div>
          </div>
        )}
      </div>
      <div className="chatbox-input-wrapper">
        <input
          className="chatbox-input"
          value={q}
          onChange={e => setQ(e.target.value)}
          onKeyPress={handleKeyPress}
          placeholder="Ask a question about your study material..."
          disabled={isLoading}
        />
        <button 
          className="chatbox-send-button" 
          onClick={ask}
          disabled={!q.trim() || isLoading}
        >
          {isLoading ? '⏳' : 'Send'}
        </button>
      </div>
      <p className="chatbox-hint">
        💡 Try: "Explain Dijkstra's algorithm" or "Give me 10 MCQs on sorting"
      </p>
    </div>
  );
}
