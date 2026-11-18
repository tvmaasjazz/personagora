-- Recreated nullable, as the previous release left it; the dropped values aren't restored
CREATE TYPE psg_llm_type AS ENUM ('FAST', 'STRONG', 'THINKING');

ALTER TABLE psg_llm_call ADD COLUMN llm_type psg_llm_type;
