-- The tier is derived from model_name, so rows written under other models become STRONG
UPDATE psg_llm_call
SET
    llm_type = CASE
        WHEN model_name IN ('gpt-5.4-nano', 'gpt-4o-mini') THEN 'FAST'
        WHEN model_name = 'o3' THEN 'THINKING'
        ELSE 'STRONG'
    END::psg_llm_type,
    updated_at = (now() AT TIME ZONE 'utc')
WHERE llm_type IS NULL;

ALTER TABLE psg_llm_call ALTER COLUMN llm_type SET NOT NULL;
