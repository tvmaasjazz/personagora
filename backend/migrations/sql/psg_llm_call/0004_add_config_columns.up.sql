ALTER TABLE psg_llm_call
    ADD COLUMN config_key TEXT,
    ADD COLUMN config_variation_key TEXT,
    ADD COLUMN config_variation_version INTEGER;
