-- Add 'audio' as a valid source type
-- Previously only 'youtube' and 'podcast' were allowed
ALTER TABLE sources DROP CONSTRAINT IF EXISTS sources_type_check;

ALTER TABLE sources
ADD CONSTRAINT sources_type_check
CHECK (type IN ('youtube', 'podcast', 'audio'));
