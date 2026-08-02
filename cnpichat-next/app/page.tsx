"use client";

import React, { useState, useRef, useEffect } from "react";
import ReactMarkdown from "react-markdown";

// Types
type Role = "human" | "ai" | "system";

interface Message {
  role: Role;
  content: string;
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
      const res = await fetch("http://127.0.0.1:8000/api/chat/", {
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

      setMessages([...newMessages, { role: "ai", content: data.answer || "Sorry, I couldn't process that." }]);
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
              {showSender && <span className="message-sender">CNPIchat</span>}
              <div className="message-row">
                {isBot ? (
                  <div className="message-avatar">
                    {showSender ? (
                      <svg viewBox="0 0 24 24" fill="none" xmlns="http://www.w3.org/2000/svg">
                        <path d="M5 10C5 8.89543 5.89543 8 7 8H17C18.1046 8 19 8.89543 19 10V16C19 17.1046 18.1046 18 17 18H7C5.89543 18 5 17.1046 5 16V10Z" fill="#A662C6" />
                        <circle cx="9" cy="12" r="1.5" fill="white" />
                        <circle cx="15" cy="12" r="1.5" fill="white" />
                        <path d="M10 15H14" stroke="white" strokeWidth="1.5" strokeLinecap="round" />
                        <path d="M12 4V8" stroke="#A662C6" strokeWidth="2" strokeLinecap="round" />
                        <circle cx="12" cy="4" r="1.5" fill="#A662C6" />
                      </svg>
                    ) : <div style={{ width: 36, height: 36 }}></div>}
                  </div>
                ) : null}
                <div className={`message ${isBot ? "bot-message" : "user-message"}`}>
                  <ReactMarkdown>{msg.content}</ReactMarkdown>
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
