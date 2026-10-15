-- Gemini API Key Cooldown Tracker
-- এই table টা track করে কোন key কখন rate limit হয়েছে
-- 24 ঘন্টা পর auto-available হয়ে যাবে

CREATE TABLE IF NOT EXISTS gemini_key_cooldown (
    id              SERIAL PRIMARY KEY,
    key_hash        VARCHAR(64) UNIQUE NOT NULL,   -- key এর SHA256 hash (full key store করা safe না)
    key_label       VARCHAR(50) NOT NULL,           -- যেমন: "GEMINI_API_KEY_1"
    exhausted_at    TIMESTAMPTZ NOT NULL,           -- কখন limit হয়েছে
    cooldown_hours  INTEGER NOT NULL DEFAULT 24,    -- কত ঘন্টা cooldown (default 24)
    available_at    TIMESTAMPTZ GENERATED ALWAYS AS 
                    (exhausted_at + (cooldown_hours || ' hours')::INTERVAL) STORED,
    notes           TEXT                            -- optional error message
);

-- Index for fast lookup
CREATE INDEX IF NOT EXISTS idx_gemini_cooldown_available 
    ON gemini_key_cooldown (available_at);

CREATE INDEX IF NOT EXISTS idx_gemini_cooldown_label 
    ON gemini_key_cooldown (key_label);

-- View: currently available keys
CREATE OR REPLACE VIEW gemini_keys_status AS
SELECT
    key_label,
    key_hash,
    exhausted_at,
    available_at,
    CASE 
        WHEN available_at <= NOW() THEN 'available'
        ELSE 'cooldown'
    END AS status,
    CASE
        WHEN available_at > NOW() 
        THEN EXTRACT(EPOCH FROM (available_at - NOW()))/3600.0
        ELSE 0
    END AS hours_remaining
FROM gemini_key_cooldown
ORDER BY key_label;
