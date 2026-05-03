import { useState } from "react";
import "./Header.css";

export default function Header({ onNewChat }) {
  const [showSettings, setShowSettings] = useState(false);

  return (
    <header className="app-header">
      <div className="header-left">
        <div className="logo">
          <span className="logo-icon">🏥</span>
          <h1>GutBot</h1>
        </div>
        <span className="tagline">AI-Powered Health Analysis</span>
      </div>

      <div className="header-right">
        <button
          onClick={onNewChat}
          className="new-chat-btn"
          title="Start a new conversation"
        >
          ➕ New Chat
        </button>

        <div className="settings-menu">
          <button
            onClick={() => setShowSettings(!showSettings)}
            className="settings-btn"
            title="Settings"
          >
            ⚙️
          </button>

          {showSettings && (
            <div className="settings-dropdown">
              <div className="setting-item">
                <label>Dark Mode</label>
                <input type="checkbox" />
              </div>
              <div className="setting-item">
                <label>Auto-save</label>
                <input type="checkbox" defaultChecked />
              </div>
              <div className="setting-item">
                <label>Enable Notifications</label>
                <input type="checkbox" />
              </div>
              <hr />
              <a href="#" className="setting-link">
                📖 Help & Documentation
              </a>
              <a href="#" className="setting-link">
                ℹ️ About
              </a>
            </div>
          )}
        </div>
      </div>
    </header>
  );
}
