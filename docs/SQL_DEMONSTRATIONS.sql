-- ==============================================================================
-- SEMANTIC PYQ ANALYZER & STUDY HEATMAP
-- SQL DEMONSTRATION & FACULTY EVALUATION SCRIPT
-- ==============================================================================
-- This script contains executable SQL queries demonstrating the DBMS features:
-- 1. pgvector Extension & HNSW Index Verification
-- 2. Schema Structure & Integrity Constraints
-- 3. Vector Cosine Distance (<=>) Similarity Queries
-- 4. Multi-Table Relational JOINs (Subject -> Document -> Chunk -> Score -> PYQ)
-- 5. Curriculum Analytics & High-Yield Paragraph Aggregations
-- 6. Referential Integrity & Cascade Deletion Verification
-- ==============================================================================

-- ------------------------------------------------------------------------------
-- 1. VERIFY PGVECTOR EXTENSION & HNSW INDEXES
-- ------------------------------------------------------------------------------

-- Check pgvector extension version
SELECT extname, extversion 
FROM pg_extension 
WHERE extname = 'vector';

-- Verify HNSW vector indexes created on note_chunks and pyqs
SELECT 
    schemaname,
    tablename,
    indexname,
    indexdef
FROM pg_indexes
WHERE indexname LIKE '%hnsw%';


-- ------------------------------------------------------------------------------
-- 2. SUMMARY COUNTS ACROSS ALL RELATIONAL TABLES
-- ------------------------------------------------------------------------------

SELECT 
    (SELECT COUNT(*) FROM subjects) AS total_subjects,
    (SELECT COUNT(*) FROM documents) AS total_documents,
    (SELECT COUNT(*) FROM note_chunks) AS total_note_chunks,
    (SELECT COUNT(*) FROM pyqs) AS total_pyqs,
    (SELECT COUNT(*) FROM analysis_runs WHERE status = 'completed') AS completed_analyses,
    (SELECT COUNT(*) FROM chunk_scores) AS total_scores_computed;


-- ------------------------------------------------------------------------------
-- 3. DEMONSTRATE VECTOR COSINE SIMILARITY SEARCH (<=>)
-- ------------------------------------------------------------------------------
-- Finds the top 5 note chunks most semantically relevant to a specific PYQ
-- using the pgvector cosine distance operator `<=>` (1 - distance = similarity)

WITH sample_pyq AS (
    SELECT pyq_id, question, embedding
    FROM pyqs
    WHERE embedding IS NOT NULL
    LIMIT 1
)
SELECT 
    p.question AS target_pyq_question,
    nc.position AS chunk_position,
    d.filename AS document_filename,
    s.name AS subject_name,
    ROUND((1 - (nc.embedding <=> p.embedding))::numeric, 4) AS cosine_similarity,
    SUBSTRING(nc.content FROM 1 FOR 180) || '...' AS matching_paragraph_excerpt
FROM sample_pyq p
CROSS JOIN note_chunks nc
JOIN documents d ON nc.document_id = d.document_id
JOIN subjects s ON nc.subject_id = s.subject_id
WHERE nc.embedding IS NOT NULL
ORDER BY nc.embedding <=> p.embedding ASC
LIMIT 5;


-- ------------------------------------------------------------------------------
-- 4. HEATMAP IMPORTANCE SCORES JOINED WITH DOCUMENTS & SUBJECTS
-- ------------------------------------------------------------------------------
-- Demonstrates multi-table JOIN across 5 tables to present the study heatmap:

SELECT 
    s.name AS subject_name,
    d.filename AS source_document,
    nc.position AS paragraph_number,
    cs.hit_count AS direct_pyq_hits,
    ROUND((cs.importance_score * 100)::numeric, 1) || '%' AS importance_yield,
    CASE 
        WHEN cs.importance_score >= 0.70 THEN 'HIGH YIELD (Red)'
        WHEN cs.importance_score >= 0.40 THEN 'MEDIUM YIELD (Amber)'
        WHEN cs.importance_score >= 0.10 THEN 'LOW YIELD (Yellow)'
        ELSE 'UNMATCHED (Slate)'
    END AS heatmap_classification,
    SUBSTRING(nc.content FROM 1 FOR 120) || '...' AS paragraph_content
FROM chunk_scores cs
JOIN note_chunks nc ON cs.chunk_id = nc.chunk_id
JOIN documents d ON nc.document_id = d.document_id
JOIN subjects s ON nc.subject_id = s.subject_id
ORDER BY cs.importance_score DESC
LIMIT 10;


-- ------------------------------------------------------------------------------
-- 5. PYQ DISTRIBUTION ANALYTICS BY YEAR & MARKS
-- ------------------------------------------------------------------------------

-- Question frequency by exam year
SELECT 
    exam_year,
    COUNT(*) AS total_questions,
    SUM(marks) AS total_marks_allocated,
    ROUND(AVG(marks), 1) AS average_question_weight
FROM pyqs
GROUP BY exam_year
ORDER BY exam_year DESC;

-- Distribution of questions by marks weightage (e.g. 5m, 10m, 15m)
SELECT 
    marks AS question_marks,
    COUNT(*) AS frequency,
    ROUND((COUNT(*) * 100.0 / (SELECT COUNT(*) FROM pyqs))::numeric, 1) || '%' AS percentage_of_all_pyqs
FROM pyqs
GROUP BY marks
ORDER BY marks ASC;


-- ------------------------------------------------------------------------------
-- 6. TOP 5 HIGH-YIELD PARAGRAPHS PER SUBJECT (WINDOW FUNCTION)
-- ------------------------------------------------------------------------------
-- Uses the SQL DENSE_RANK() analytical window function to rank paragraphs:

WITH ranked_chunks AS (
    SELECT 
        s.name AS subject_name,
        d.filename AS document_name,
        nc.chunk_id,
        cs.hit_count,
        cs.importance_score,
        SUBSTRING(nc.content FROM 1 FOR 150) AS content_excerpt,
        DENSE_RANK() OVER (
            PARTITION BY s.subject_id 
            ORDER BY cs.importance_score DESC
        ) AS subject_rank
    FROM chunk_scores cs
    JOIN note_chunks nc ON cs.chunk_id = nc.chunk_id
    JOIN documents d ON nc.document_id = d.document_id
    JOIN subjects s ON nc.subject_id = s.subject_id
)
SELECT 
    subject_name,
    subject_rank,
    ROUND((importance_score * 100)::numeric, 1) || '%' AS score,
    hit_count AS pyq_hits,
    document_name,
    content_excerpt || '...' AS excerpt
FROM ranked_chunks
WHERE subject_rank <= 5
ORDER BY subject_name, subject_rank;


-- ------------------------------------------------------------------------------
-- 7. DEMONSTRATE ACID TRANSACTIONS & REFERENTIAL CASCADES
-- ------------------------------------------------------------------------------
-- Creates a dummy course, adds documents & chunks, and demonstrates that
-- deleting the subject cleanly cascades without leaving orphaned records:

BEGIN;

-- Insert temporary demonstration subject
INSERT INTO subjects (subject_id, name, course_code, description, created_at, updated_at)
VALUES ('00000000-0000-0000-0000-000000000001', 'Temporary Demo Course', 'DEMO101', 'For cascade test', NOW(), NOW());

-- Insert document
INSERT INTO documents (document_id, subject_id, filename, stored_path, file_type, processing_status, created_at, updated_at)
VALUES ('00000000-0000-0000-0000-000000000002', '00000000-0000-0000-0000-000000000001', 'demo.txt', '/tmp/demo.txt', 'txt', 'completed', NOW(), NOW());

-- Insert chunk
INSERT INTO note_chunks (chunk_id, subject_id, document_id, position, content, word_count, created_at)
VALUES ('00000000-0000-0000-0000-000000000003', '00000000-0000-0000-0000-000000000001', '00000000-0000-0000-0000-000000000002', 1, 'Sample cascade content', 3, NOW());

-- Verify insertion
SELECT COUNT(*) AS chunks_before_delete FROM note_chunks WHERE subject_id = '00000000-0000-0000-0000-000000000001';

-- Delete parent subject (triggers ON DELETE CASCADE)
DELETE FROM subjects WHERE subject_id = '00000000-0000-0000-0000-000000000001';

-- Verify child records were automatically purged
SELECT COUNT(*) AS chunks_after_delete FROM note_chunks WHERE subject_id = '00000000-0000-0000-0000-000000000001';

-- Rollback transaction to maintain database cleanliness
ROLLBACK;
