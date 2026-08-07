-- =========================================================================
-- Data-quality issue summary
--
-- Audience: Executive / Program Leadership
-- Question: How many data-quality findings did the ETL pipeline
--           generate, and how severe are they?
-- Decision supported: Whether the database can be trusted for
--                      downstream reporting as-is, or whether specific
--                      findings need engineering follow-up before this
--                      data is used for a mission-critical decision.
-- Why it matters: this table is the pipeline's own explicit statement
-- of what it found and chose not to silently discard (CLAUDE.md rule
-- 12) -- a leadership audience should see this count before trusting
-- any other number in this analytical layer.
--
-- Tables involved: data_quality_issues
-- Join path: single table (data_quality_issues is deliberately an
--            ETL-generated audit log with no foreign keys of its own --
--            docs/DATABASE_DESIGN.md Section 5.10 -- so there is no
--            further table to join to without inventing a relationship
--            the schema intentionally does not assert).
-- SQL technique: simple aggregation (GROUP BY + COUNT)
-- Grain: one row per distinct (issue_type, severity) combination.
--
-- Assumptions/limitations: this table only grows as new cleaning rules
-- are implemented -- it is not, and is not intended to be, a complete
-- inventory of every possible data-quality concern in the source file
-- (see docs/DATA_CLEANING.md for the full list of rules actually
-- implemented, including several checked-and-found-clean cases that
-- never produce a data_quality_issues row at all).
-- =========================================================================

SELECT
    issue_type,
    severity,
    COUNT(*) AS issue_count
FROM data_quality_issues
GROUP BY issue_type, severity
ORDER BY issue_count DESC;
