"use client";

import React, { useState, useRef, useEffect } from "react";
import ReactMarkdown from "react-markdown";
import remarkGfm from "remark-gfm";

// API base URL — local dev uses localhost, production uses HuggingFace Space URL
const API_BASE_URL = process.env.NEXT_PUBLIC_API_URL || "http://127.0.0.1:8000";

// Types
type Role = "human" | "ai" | "system";

interface Context {
  rank: number;
  content: string;
  date: string;
  time: string;
  score: number;
  doc_type: string;
  topic: string;
}

interface Message {
  role: Role;
  content: string;
  contexts?: Context[];
}

const initialMessages: Message[] = [
  { role: "ai", content: "আসসালামু আলাইকুম! আমি CNPIchat 🤖। আপনাকে কীভাবে সাহায্য করতে পারি?" }
];

export default function Home() {
  const [messages, setMessages] = useState<Message[]>(initialMessages);
  const [inputValue, setInputValue] = useState("");
  const [isTyping, setIsTyping] = useState(false);
  const messagesEndRef = useRef<HTMLDivElement>(null);
  const [sessionId, setSessionId] = useState<string>("");
  const [showOptions, setShowOptions] = useState(true);
  const [showMenu, setShowMenu] = useState(false);
  const [isMounted, setIsMounted] = useState(false);
  const [showContextsModal, setShowContextsModal] = useState<number | null>(null);

  const scrollToBottom = () => {
    messagesEndRef.current?.scrollIntoView({ behavior: "smooth" });
  };

  useEffect(() => {
    setIsMounted(true);
  }, []);

  useEffect(() => {
    scrollToBottom();
  }, [messages, isTyping]);

  const handleNewSession = () => {
    setMessages(initialMessages);
    setSessionId("");
    setShowOptions(true);
    setShowMenu(false);
  };

  const handleSend = async (text: string) => {
    if (!text.trim()) return;

    // Add user message
    const newMessages: Message[] = [...messages, { role: "human", content: text }];
    setMessages(newMessages);
    setInputValue("");
    setIsTyping(true);
    setShowOptions(false);
    setShowMenu(false); // close menu if open

    try {
      // API call to Django backend
      const res = await fetch(`${API_BASE_URL}/api/chat/`, {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
        },
        body: JSON.stringify({
          message: text,
          session_id: sessionId || undefined,
        }),
      });

      if (!res.ok) {
        throw new Error("Failed to fetch");
      }

      const data = await res.json();

      if (data.session_id) {
        setSessionId(data.session_id);
      }

      setMessages([...newMessages, { 
        role: "ai", 
        content: data.answer || "Sorry, I couldn't process that.",
        contexts: data.contexts || []
      }]);
    } catch (error) {
      console.error(error);
      setMessages([...newMessages, { role: "ai", content: "An error occurred connecting to the server." }]);
    } finally {
      setIsTyping(false);
    }
  };

  const handleKeyDown = (e: React.KeyboardEvent<HTMLInputElement>) => {
    if (e.key === "Enter") {
      handleSend(inputValue);
    }
  };

  const QuickReply = ({ title }: { title: string }) => (
    <button className="quick-reply-btn" onClick={() => handleSend(title)}>
      {title}
    </button>
  );

  if (!isMounted) {
    return null; // Prevents hydration mismatch caused by browser extensions injecting attributes like bis_skin_checked
  }

  return (
    <div className="chat-wrapper">
      {/* HEADER */}
      <header className="chat-header">
        <div className="bot-info">
          <div className="bot-avatar">
            <svg viewBox="0 0 24 24" fill="none" xmlns="http://www.w3.org/2000/svg">
              <path d="M5 10C5 8.89543 5.89543 8 7 8H17C18.1046 8 19 8.89543 19 10V16C19 17.1046 18.1046 18 17 18H7C5.89543 18 5 17.1046 5 16V10Z" fill="#A662C6" />
              <circle cx="9" cy="12" r="1.5" fill="white" />
              <circle cx="15" cy="12" r="1.5" fill="white" />
              <path d="M10 15H14" stroke="white" strokeWidth="1.5" strokeLinecap="round" />
              <path d="M12 4V8" stroke="#A662C6" strokeWidth="2" strokeLinecap="round" />
              <circle cx="12" cy="4" r="1.5" fill="#A662C6" />
            </svg>
          </div>
          <div className="bot-details">
            <h1 className="bot-name">CNPIchat</h1>
            <span className="bot-status"><span className="status-dot"></span> Online Now</span>
          </div>
        </div>
        <div className="header-actions">
          <div style={{ position: "relative" }}>
            <button className="action-btn" aria-label="More options" onClick={() => setShowMenu(!showMenu)}>
              <svg viewBox="0 0 24 24" width="20" height="20" fill="white">
                <circle cx="5" cy="12" r="1.5" />
                <circle cx="12" cy="12" r="1.5" />
                <circle cx="19" cy="12" r="1.5" />
              </svg>
            </button>
            {showMenu && (
              <div style={{
                position: "absolute",
                right: 0,
                top: "30px",
                backgroundColor: "white",
                color: "#373A40",
                boxShadow: "0 4px 15px rgba(0,0,0,0.1)",
                borderRadius: "8px",
                padding: "8px 0",
                minWidth: "140px",
                zIndex: 10
              }}>
                <button 
                  onClick={handleNewSession}
                  style={{
                    width: "100%",
                    padding: "10px 16px",
                    border: "none",
                    background: "none",
                    textAlign: "left",
                    cursor: "pointer",
                    fontSize: "14px",
                    fontWeight: 500,
                    color: "inherit"
                  }}
                  onMouseOver={(e) => e.currentTarget.style.backgroundColor = "#F4F4F5"}
                  onMouseOut={(e) => e.currentTarget.style.backgroundColor = "transparent"}
                >
                  🔄 New Session
                </button>
              </div>
            )}
          </div>
          <button className="action-btn" aria-label="Close">
            <svg viewBox="0 0 24 24" width="20" height="20" fill="none" stroke="white" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
              <line x1="18" y1="6" x2="6" y2="18"></line>
              <line x1="6" y1="6" x2="18" y2="18"></line>
            </svg>
          </button>
        </div>
      </header>

      {/* MESSAGES */}
      <div className="chat-messages" onClick={() => showMenu && setShowMenu(false)}>
        {messages.map((msg, idx) => {
          const isBot = msg.role === "ai" || msg.role === "system";
          const showSender = isBot && (idx === 0 || messages[idx - 1].role !== "ai");

          return (
            <div key={idx} className={`message-group ${isBot ? "bot" : "user"}`}>
              {showSender && (
                <div style={{ display: "flex", alignItems: "center", gap: "8px", marginBottom: "8px" }}>
                  <div className="message-avatar">
                    <svg viewBox="0 0 24 24" fill="none" xmlns="http://www.w3.org/2000/svg">
                      <path d="M5 10C5 8.89543 5.89543 8 7 8H17C18.1046 8 19 8.89543 19 10V16C19 17.1046 18.1046 18 17 18H7C5.89543 18 5 17.1046 5 16V10Z" fill="#A662C6" />
                      <circle cx="9" cy="12" r="1.5" fill="white" />
                      <circle cx="15" cy="12" r="1.5" fill="white" />
                      <path d="M10 15H14" stroke="white" strokeWidth="1.5" strokeLinecap="round" />
                      <path d="M12 4V8" stroke="#A662C6" strokeWidth="2" strokeLinecap="round" />
                      <circle cx="12" cy="4" r="1.5" fill="#A662C6" />
                    </svg>
                  </div>
                  <span className="message-sender">CNPIchat</span>
                </div>
              )}
              <div className="message-row">
                <div className={`message ${isBot ? "bot-message" : "user-message"}`}>
                  <ReactMarkdown remarkPlugins={[remarkGfm]}>
                    {msg.content}
                  </ReactMarkdown>
                  
                  {/* Context dates and source button for AI messages */}
                  {isBot && msg.contexts && msg.contexts.length > 0 && (
                     <div style={{ marginTop: "12px", display: "flex", alignItems: "center", justifyContent: "space-between", gap: "12px", flexWrap: "wrap" }}>
                       {/* Show highest scored context date */}
                       {(() => {
                         // Find the context with the highest score
                         const highestScoredContext = msg.contexts.reduce((max, ctx) => 
                           ctx.score > max.score ? ctx : max
                         , msg.contexts[0]);
                         
                         return (
                           <div style={{ 
                             fontSize: "0.85em", 
                             color: "#666", 
                             display: "flex",
                             alignItems: "center",
                             gap: "6px"
                           }}>
                             <span>📅</span>
                             <span>তথ্যের তারিখ: {highestScoredContext.date}</span>
                           </div>
                         );
                       })()}
                       
                       {/* Source button */}
                       <button
                         onClick={() => setShowContextsModal(showContextsModal === idx ? null : idx)}
                         style={{
                           padding: "6px 14px",
                           backgroundColor: "#A662C6",
                           color: "white",
                           border: "none",
                           borderRadius: "6px",
                           cursor: "pointer",
                           fontSize: "0.85em",
                           fontWeight: "500",
                           display: "flex",
                           alignItems: "center",
                           gap: "6px",
                           transition: "background-color 0.2s"
                         }}
                         onMouseOver={(e) => e.currentTarget.style.backgroundColor = "#8B4FA8"}
                         onMouseOut={(e) => e.currentTarget.style.backgroundColor = "#A662C6"}
                       >
                         <span>📄</span>
                         <span>Source ({msg.contexts.length})</span>
                       </button>
                      
                      {/* Contexts Modal */}
                      {showContextsModal === idx && (
                        <div 
                          style={{
                            position: "fixed",
                            top: 0,
                            left: 0,
                            right: 0,
                            bottom: 0,
                            backgroundColor: "rgba(0, 0, 0, 0.5)",
                            display: "flex",
                            alignItems: "center",
                            justifyContent: "center",
                            zIndex: 1000,
                            padding: "20px"
                          }}
                          onClick={() => setShowContextsModal(null)}
                        >
                          <div 
                            style={{
                              backgroundColor: "white",
                              borderRadius: "12px",
                              maxWidth: "800px",
                              width: "100%",
                              maxHeight: "80vh",
                              overflow: "hidden",
                              display: "flex",
                              flexDirection: "column",
                              boxShadow: "0 10px 40px rgba(0,0,0,0.2)"
                            }}
                            onClick={(e) => e.stopPropagation()}
                          >
                            {/* Modal Header */}
                            <div style={{
                              padding: "20px",
                              borderBottom: "1px solid #e0e0e0",
                              display: "flex",
                              justifyContent: "space-between",
                              alignItems: "center"
                            }}>
                              <h3 style={{ margin: 0, color: "#373A40" }}>সমস্ত Context</h3>
                              <button
                                onClick={() => setShowContextsModal(null)}
                                style={{
                                  background: "none",
                                  border: "none",
                                  fontSize: "24px",
                                  cursor: "pointer",
                                  color: "#666",
                                  padding: "0",
                                  width: "30px",
                                  height: "30px",
                                  display: "flex",
                                  alignItems: "center",
                                  justifyContent: "center"
                                }}
                              >
                                ×
                              </button>
                            </div>
                            
                            {/* Modal Body */}
                            <div style={{
                              overflowY: "auto",
                              padding: "20px"
                            }}>
                              {msg.contexts!.map((ctx, ctxIdx) => (
                                <div 
                                  key={ctxIdx}
                                  style={{
                                    border: "1px solid #e0e0e0",
                                    borderRadius: "8px",
                                    padding: "16px",
                                    marginBottom: "12px",
                                    backgroundColor: "#f9f9f9"
                                  }}
                                >
                                  {/* Context Meta */}
                                  <div style={{
                                    display: "flex",
                                    gap: "12px",
                                    flexWrap: "wrap",
                                    marginBottom: "12px",
                                    fontSize: "0.85em",
                                    color: "#666"
                                  }}>
                                    <span style={{ 
                                      fontWeight: "600", 
                                      color: "#A662C6" 
                                    }}>
                                      #{ctx.rank}
                                    </span>
                                    <span>📅 {ctx.date} {ctx.time}</span>
                                    <span>⭐ {(ctx.score * 100).toFixed(1)}%</span>
                                    {ctx.doc_type && <span>📝 {ctx.doc_type}</span>}
                                  </div>
                                  
                                  {/* Context Content */}
                                  <div style={{
                                    whiteSpace: "pre-wrap",
                                    lineHeight: "1.6",
                                    color: "#373A40",
                                    fontSize: "0.95em"
                                  }}>
                                    {ctx.content}
                                  </div>
                                  
                                  {/* Context Topic */}
                                  {ctx.topic && (
                                    <div style={{
                                      marginTop: "10px",
                                      fontSize: "0.85em",
                                      color: "#666",
                                      fontStyle: "italic"
                                    }}>
                                      বিষয়: {ctx.topic}
                                    </div>
                                  )}
                                </div>
                              ))}
                            </div>
                          </div>
                        </div>
                      )}
                    </div>
                  )}
                </div>
              </div>

              {/* Show options for initial message */}
              {showOptions && idx === 0 && (
                <div className="quick-replies">
                  <QuickReply title="CST ডিপার্টমেন্ট" />
                  <QuickReply title="শিক্ষকদের তথ্য" />
                  <QuickReply title="ক্লাস রুটিন" />
                </div>
              )}
            </div>
          );
        })}
        {isTyping && (
          <div className="message-group bot">
            <div className="message-row">
              <div className="message-avatar">
                <svg viewBox="0 0 24 24" fill="none" xmlns="http://www.w3.org/2000/svg">
                  <path d="M5 10C5 8.89543 5.89543 8 7 8H17C18.1046 8 19 8.89543 19 10V16C19 17.1046 18.1046 18 17 18H7C5.89543 18 5 17.1046 5 16V10Z" fill="#A662C6" />
                  <circle cx="9" cy="12" r="1.5" fill="white" />
                  <circle cx="15" cy="12" r="1.5" fill="white" />
                  <path d="M10 15H14" stroke="white" strokeWidth="1.5" strokeLinecap="round" />
                  <path d="M12 4V8" stroke="#A662C6" strokeWidth="2" strokeLinecap="round" />
                  <circle cx="12" cy="4" r="1.5" fill="#A662C6" />
                </svg>
              </div>
              <div className="typing-indicator" style={{ marginLeft: 0 }}>
                <div className="dot"></div><div className="dot"></div><div className="dot"></div>
              </div>
            </div>
          </div>
        )}
        <div ref={messagesEndRef} />
      </div>

      {/* FOOTER */}
      <div className="chat-input-area" onClick={() => showMenu && setShowMenu(false)}>
        <div className="input-wrapper">
          <input
            type="text"
            placeholder="Reply to CNPIchat..."
            value={inputValue}
            onChange={(e) => setInputValue(e.target.value)}
            onKeyDown={handleKeyDown}
          />
          <button 
            className="send-btn" 
            onClick={() => handleSend(inputValue)}
            disabled={!inputValue.trim() || isTyping}
            aria-label="Send message"
          >
            <svg viewBox="0 0 24 24" width="20" height="20" fill="currentColor">
              <path d="M2.01 21L23 12 2.01 3 2 10l15 2-15 2z" />
            </svg>
          </button>
        </div>
        <div className="footer-branding">
          <div></div>
          <div className="brand-name">
            We're <svg width="10" height="14" viewBox="0 0 10 14" fill="none" xmlns="http://www.w3.org/2000/svg" style={{ margin: "0 2px" }}>
              <path d="M4.5 0L0 8H4.5L3.5 14L9.5 5.5H5L4.5 0Z" fill="#FFC107" />
            </svg> by <strong>CNPIan</strong>
          </div>
        </div>
      </div>
    </div>
  );
}
