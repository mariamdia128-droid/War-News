-- GENERATED REVIEW FILE. Inspect the CSV before running this file.
-- Moves each approved row back to the incident pipeline exactly once.
--
-- RUN THIS ONLY AFTER the backfill has run with --apply: each DELETE is
-- guarded on the review_status/review_reason that --apply writes, so on an
-- un-applied database every DELETE matches zero rows.
--
-- Messages already 'materialized' or 'duplicate' are left untouched: they
-- are represented by a live incident or by their canonical message, and
-- reopening them is what would create a duplicate incident.
-- 311 rows are moved here; 14 import rows have no
-- source message and are listed, not deleted, at the end of this file.
BEGIN;
-- air_violation_id=722 reason=excluded_kinetic_casualty_or_damage
UPDATE raw_messages rm
SET status = 'pending'::message_status,
    match_result = NULL,
    error_message = NULL, processing_claim_stage = NULL,
    processing_claimed_at = NULL, processing_claimed_by = NULL
WHERE rm.id = (SELECT raw_message_id FROM air_violations WHERE id = 722)
  AND rm.status NOT IN ('materialized'::message_status, 'duplicate'::message_status)
  AND NOT EXISTS (SELECT 1 FROM incidents i
                  WHERE i.raw_message_id = rm.id AND i.is_deleted = false);
DELETE FROM air_violations WHERE id = 722
  AND review_status = 'flagged_for_review' AND review_reason = 'excluded_kinetic_casualty_or_damage';
-- air_violation_id=723 reason=excluded_kinetic_casualty_or_damage
UPDATE raw_messages rm
SET status = 'pending'::message_status,
    match_result = NULL,
    error_message = NULL, processing_claim_stage = NULL,
    processing_claimed_at = NULL, processing_claimed_by = NULL
WHERE rm.id = (SELECT raw_message_id FROM air_violations WHERE id = 723)
  AND rm.status NOT IN ('materialized'::message_status, 'duplicate'::message_status)
  AND NOT EXISTS (SELECT 1 FROM incidents i
                  WHERE i.raw_message_id = rm.id AND i.is_deleted = false);
DELETE FROM air_violations WHERE id = 723
  AND review_status = 'flagged_for_review' AND review_reason = 'excluded_kinetic_casualty_or_damage';
-- air_violation_id=726 reason=excluded_kinetic_casualty_or_damage
UPDATE raw_messages rm
SET status = 'pending'::message_status,
    match_result = NULL,
    error_message = NULL, processing_claim_stage = NULL,
    processing_claimed_at = NULL, processing_claimed_by = NULL
WHERE rm.id = (SELECT raw_message_id FROM air_violations WHERE id = 726)
  AND rm.status NOT IN ('materialized'::message_status, 'duplicate'::message_status)
  AND NOT EXISTS (SELECT 1 FROM incidents i
                  WHERE i.raw_message_id = rm.id AND i.is_deleted = false);
DELETE FROM air_violations WHERE id = 726
  AND review_status = 'flagged_for_review' AND review_reason = 'excluded_kinetic_casualty_or_damage';
-- air_violation_id=727 reason=excluded_kinetic_casualty_or_damage
UPDATE raw_messages rm
SET status = 'pending'::message_status,
    match_result = NULL,
    error_message = NULL, processing_claim_stage = NULL,
    processing_claimed_at = NULL, processing_claimed_by = NULL
WHERE rm.id = (SELECT raw_message_id FROM air_violations WHERE id = 727)
  AND rm.status NOT IN ('materialized'::message_status, 'duplicate'::message_status)
  AND NOT EXISTS (SELECT 1 FROM incidents i
                  WHERE i.raw_message_id = rm.id AND i.is_deleted = false);
DELETE FROM air_violations WHERE id = 727
  AND review_status = 'flagged_for_review' AND review_reason = 'excluded_kinetic_casualty_or_damage';
-- air_violation_id=729 reason=excluded_kinetic_casualty_or_damage
UPDATE raw_messages rm
SET status = 'pending'::message_status,
    match_result = NULL,
    error_message = NULL, processing_claim_stage = NULL,
    processing_claimed_at = NULL, processing_claimed_by = NULL
WHERE rm.id = (SELECT raw_message_id FROM air_violations WHERE id = 729)
  AND rm.status NOT IN ('materialized'::message_status, 'duplicate'::message_status)
  AND NOT EXISTS (SELECT 1 FROM incidents i
                  WHERE i.raw_message_id = rm.id AND i.is_deleted = false);
DELETE FROM air_violations WHERE id = 729
  AND review_status = 'flagged_for_review' AND review_reason = 'excluded_kinetic_casualty_or_damage';
-- air_violation_id=730 reason=excluded_kinetic_casualty_or_damage
UPDATE raw_messages rm
SET status = 'pending'::message_status,
    match_result = NULL,
    error_message = NULL, processing_claim_stage = NULL,
    processing_claimed_at = NULL, processing_claimed_by = NULL
WHERE rm.id = (SELECT raw_message_id FROM air_violations WHERE id = 730)
  AND rm.status NOT IN ('materialized'::message_status, 'duplicate'::message_status)
  AND NOT EXISTS (SELECT 1 FROM incidents i
                  WHERE i.raw_message_id = rm.id AND i.is_deleted = false);
DELETE FROM air_violations WHERE id = 730
  AND review_status = 'flagged_for_review' AND review_reason = 'excluded_kinetic_casualty_or_damage';
-- air_violation_id=731 reason=excluded_kinetic_casualty_or_damage
UPDATE raw_messages rm
SET status = 'pending'::message_status,
    match_result = NULL,
    error_message = NULL, processing_claim_stage = NULL,
    processing_claimed_at = NULL, processing_claimed_by = NULL
WHERE rm.id = (SELECT raw_message_id FROM air_violations WHERE id = 731)
  AND rm.status NOT IN ('materialized'::message_status, 'duplicate'::message_status)
  AND NOT EXISTS (SELECT 1 FROM incidents i
                  WHERE i.raw_message_id = rm.id AND i.is_deleted = false);
DELETE FROM air_violations WHERE id = 731
  AND review_status = 'flagged_for_review' AND review_reason = 'excluded_kinetic_casualty_or_damage';
-- air_violation_id=732 reason=excluded_kinetic_casualty_or_damage
UPDATE raw_messages rm
SET status = 'pending'::message_status,
    match_result = NULL,
    error_message = NULL, processing_claim_stage = NULL,
    processing_claimed_at = NULL, processing_claimed_by = NULL
WHERE rm.id = (SELECT raw_message_id FROM air_violations WHERE id = 732)
  AND rm.status NOT IN ('materialized'::message_status, 'duplicate'::message_status)
  AND NOT EXISTS (SELECT 1 FROM incidents i
                  WHERE i.raw_message_id = rm.id AND i.is_deleted = false);
DELETE FROM air_violations WHERE id = 732
  AND review_status = 'flagged_for_review' AND review_reason = 'excluded_kinetic_casualty_or_damage';
-- air_violation_id=733 reason=excluded_kinetic_casualty_or_damage
UPDATE raw_messages rm
SET status = 'pending'::message_status,
    match_result = NULL,
    error_message = NULL, processing_claim_stage = NULL,
    processing_claimed_at = NULL, processing_claimed_by = NULL
WHERE rm.id = (SELECT raw_message_id FROM air_violations WHERE id = 733)
  AND rm.status NOT IN ('materialized'::message_status, 'duplicate'::message_status)
  AND NOT EXISTS (SELECT 1 FROM incidents i
                  WHERE i.raw_message_id = rm.id AND i.is_deleted = false);
DELETE FROM air_violations WHERE id = 733
  AND review_status = 'flagged_for_review' AND review_reason = 'excluded_kinetic_casualty_or_damage';
-- air_violation_id=734 reason=excluded_kinetic_casualty_or_damage
UPDATE raw_messages rm
SET status = 'pending'::message_status,
    match_result = NULL,
    error_message = NULL, processing_claim_stage = NULL,
    processing_claimed_at = NULL, processing_claimed_by = NULL
WHERE rm.id = (SELECT raw_message_id FROM air_violations WHERE id = 734)
  AND rm.status NOT IN ('materialized'::message_status, 'duplicate'::message_status)
  AND NOT EXISTS (SELECT 1 FROM incidents i
                  WHERE i.raw_message_id = rm.id AND i.is_deleted = false);
DELETE FROM air_violations WHERE id = 734
  AND review_status = 'flagged_for_review' AND review_reason = 'excluded_kinetic_casualty_or_damage';
-- air_violation_id=735 reason=excluded_kinetic_casualty_or_damage
UPDATE raw_messages rm
SET status = 'pending'::message_status,
    match_result = NULL,
    error_message = NULL, processing_claim_stage = NULL,
    processing_claimed_at = NULL, processing_claimed_by = NULL
WHERE rm.id = (SELECT raw_message_id FROM air_violations WHERE id = 735)
  AND rm.status NOT IN ('materialized'::message_status, 'duplicate'::message_status)
  AND NOT EXISTS (SELECT 1 FROM incidents i
                  WHERE i.raw_message_id = rm.id AND i.is_deleted = false);
DELETE FROM air_violations WHERE id = 735
  AND review_status = 'flagged_for_review' AND review_reason = 'excluded_kinetic_casualty_or_damage';
-- air_violation_id=736 reason=excluded_kinetic_casualty_or_damage
UPDATE raw_messages rm
SET status = 'pending'::message_status,
    match_result = NULL,
    error_message = NULL, processing_claim_stage = NULL,
    processing_claimed_at = NULL, processing_claimed_by = NULL
WHERE rm.id = (SELECT raw_message_id FROM air_violations WHERE id = 736)
  AND rm.status NOT IN ('materialized'::message_status, 'duplicate'::message_status)
  AND NOT EXISTS (SELECT 1 FROM incidents i
                  WHERE i.raw_message_id = rm.id AND i.is_deleted = false);
DELETE FROM air_violations WHERE id = 736
  AND review_status = 'flagged_for_review' AND review_reason = 'excluded_kinetic_casualty_or_damage';
-- air_violation_id=737 reason=excluded_kinetic_casualty_or_damage
UPDATE raw_messages rm
SET status = 'pending'::message_status,
    match_result = NULL,
    error_message = NULL, processing_claim_stage = NULL,
    processing_claimed_at = NULL, processing_claimed_by = NULL
WHERE rm.id = (SELECT raw_message_id FROM air_violations WHERE id = 737)
  AND rm.status NOT IN ('materialized'::message_status, 'duplicate'::message_status)
  AND NOT EXISTS (SELECT 1 FROM incidents i
                  WHERE i.raw_message_id = rm.id AND i.is_deleted = false);
DELETE FROM air_violations WHERE id = 737
  AND review_status = 'flagged_for_review' AND review_reason = 'excluded_kinetic_casualty_or_damage';
-- air_violation_id=738 reason=excluded_kinetic_casualty_or_damage
UPDATE raw_messages rm
SET status = 'pending'::message_status,
    match_result = NULL,
    error_message = NULL, processing_claim_stage = NULL,
    processing_claimed_at = NULL, processing_claimed_by = NULL
WHERE rm.id = (SELECT raw_message_id FROM air_violations WHERE id = 738)
  AND rm.status NOT IN ('materialized'::message_status, 'duplicate'::message_status)
  AND NOT EXISTS (SELECT 1 FROM incidents i
                  WHERE i.raw_message_id = rm.id AND i.is_deleted = false);
DELETE FROM air_violations WHERE id = 738
  AND review_status = 'flagged_for_review' AND review_reason = 'excluded_kinetic_casualty_or_damage';
-- air_violation_id=739 reason=excluded_kinetic_casualty_or_damage
UPDATE raw_messages rm
SET status = 'pending'::message_status,
    match_result = NULL,
    error_message = NULL, processing_claim_stage = NULL,
    processing_claimed_at = NULL, processing_claimed_by = NULL
WHERE rm.id = (SELECT raw_message_id FROM air_violations WHERE id = 739)
  AND rm.status NOT IN ('materialized'::message_status, 'duplicate'::message_status)
  AND NOT EXISTS (SELECT 1 FROM incidents i
                  WHERE i.raw_message_id = rm.id AND i.is_deleted = false);
DELETE FROM air_violations WHERE id = 739
  AND review_status = 'flagged_for_review' AND review_reason = 'excluded_kinetic_casualty_or_damage';
-- air_violation_id=740 reason=excluded_kinetic_casualty_or_damage
UPDATE raw_messages rm
SET status = 'pending'::message_status,
    match_result = NULL,
    error_message = NULL, processing_claim_stage = NULL,
    processing_claimed_at = NULL, processing_claimed_by = NULL
WHERE rm.id = (SELECT raw_message_id FROM air_violations WHERE id = 740)
  AND rm.status NOT IN ('materialized'::message_status, 'duplicate'::message_status)
  AND NOT EXISTS (SELECT 1 FROM incidents i
                  WHERE i.raw_message_id = rm.id AND i.is_deleted = false);
DELETE FROM air_violations WHERE id = 740
  AND review_status = 'flagged_for_review' AND review_reason = 'excluded_kinetic_casualty_or_damage';
-- air_violation_id=741 reason=excluded_kinetic_casualty_or_damage
UPDATE raw_messages rm
SET status = 'pending'::message_status,
    match_result = NULL,
    error_message = NULL, processing_claim_stage = NULL,
    processing_claimed_at = NULL, processing_claimed_by = NULL
WHERE rm.id = (SELECT raw_message_id FROM air_violations WHERE id = 741)
  AND rm.status NOT IN ('materialized'::message_status, 'duplicate'::message_status)
  AND NOT EXISTS (SELECT 1 FROM incidents i
                  WHERE i.raw_message_id = rm.id AND i.is_deleted = false);
DELETE FROM air_violations WHERE id = 741
  AND review_status = 'flagged_for_review' AND review_reason = 'excluded_kinetic_casualty_or_damage';
-- air_violation_id=742 reason=excluded_kinetic_casualty_or_damage
UPDATE raw_messages rm
SET status = 'pending'::message_status,
    match_result = NULL,
    error_message = NULL, processing_claim_stage = NULL,
    processing_claimed_at = NULL, processing_claimed_by = NULL
WHERE rm.id = (SELECT raw_message_id FROM air_violations WHERE id = 742)
  AND rm.status NOT IN ('materialized'::message_status, 'duplicate'::message_status)
  AND NOT EXISTS (SELECT 1 FROM incidents i
                  WHERE i.raw_message_id = rm.id AND i.is_deleted = false);
DELETE FROM air_violations WHERE id = 742
  AND review_status = 'flagged_for_review' AND review_reason = 'excluded_kinetic_casualty_or_damage';
-- air_violation_id=743 reason=excluded_kinetic_casualty_or_damage
UPDATE raw_messages rm
SET status = 'pending'::message_status,
    match_result = NULL,
    error_message = NULL, processing_claim_stage = NULL,
    processing_claimed_at = NULL, processing_claimed_by = NULL
WHERE rm.id = (SELECT raw_message_id FROM air_violations WHERE id = 743)
  AND rm.status NOT IN ('materialized'::message_status, 'duplicate'::message_status)
  AND NOT EXISTS (SELECT 1 FROM incidents i
                  WHERE i.raw_message_id = rm.id AND i.is_deleted = false);
DELETE FROM air_violations WHERE id = 743
  AND review_status = 'flagged_for_review' AND review_reason = 'excluded_kinetic_casualty_or_damage';
-- air_violation_id=744 reason=excluded_kinetic_casualty_or_damage
UPDATE raw_messages rm
SET status = 'pending'::message_status,
    match_result = NULL,
    error_message = NULL, processing_claim_stage = NULL,
    processing_claimed_at = NULL, processing_claimed_by = NULL
WHERE rm.id = (SELECT raw_message_id FROM air_violations WHERE id = 744)
  AND rm.status NOT IN ('materialized'::message_status, 'duplicate'::message_status)
  AND NOT EXISTS (SELECT 1 FROM incidents i
                  WHERE i.raw_message_id = rm.id AND i.is_deleted = false);
DELETE FROM air_violations WHERE id = 744
  AND review_status = 'flagged_for_review' AND review_reason = 'excluded_kinetic_casualty_or_damage';
-- air_violation_id=745 reason=excluded_kinetic_casualty_or_damage
UPDATE raw_messages rm
SET status = 'pending'::message_status,
    match_result = NULL,
    error_message = NULL, processing_claim_stage = NULL,
    processing_claimed_at = NULL, processing_claimed_by = NULL
WHERE rm.id = (SELECT raw_message_id FROM air_violations WHERE id = 745)
  AND rm.status NOT IN ('materialized'::message_status, 'duplicate'::message_status)
  AND NOT EXISTS (SELECT 1 FROM incidents i
                  WHERE i.raw_message_id = rm.id AND i.is_deleted = false);
DELETE FROM air_violations WHERE id = 745
  AND review_status = 'flagged_for_review' AND review_reason = 'excluded_kinetic_casualty_or_damage';
-- air_violation_id=746 reason=excluded_kinetic_casualty_or_damage
UPDATE raw_messages rm
SET status = 'pending'::message_status,
    match_result = NULL,
    error_message = NULL, processing_claim_stage = NULL,
    processing_claimed_at = NULL, processing_claimed_by = NULL
WHERE rm.id = (SELECT raw_message_id FROM air_violations WHERE id = 746)
  AND rm.status NOT IN ('materialized'::message_status, 'duplicate'::message_status)
  AND NOT EXISTS (SELECT 1 FROM incidents i
                  WHERE i.raw_message_id = rm.id AND i.is_deleted = false);
DELETE FROM air_violations WHERE id = 746
  AND review_status = 'flagged_for_review' AND review_reason = 'excluded_kinetic_casualty_or_damage';
-- air_violation_id=747 reason=excluded_kinetic_casualty_or_damage
UPDATE raw_messages rm
SET status = 'pending'::message_status,
    match_result = NULL,
    error_message = NULL, processing_claim_stage = NULL,
    processing_claimed_at = NULL, processing_claimed_by = NULL
WHERE rm.id = (SELECT raw_message_id FROM air_violations WHERE id = 747)
  AND rm.status NOT IN ('materialized'::message_status, 'duplicate'::message_status)
  AND NOT EXISTS (SELECT 1 FROM incidents i
                  WHERE i.raw_message_id = rm.id AND i.is_deleted = false);
DELETE FROM air_violations WHERE id = 747
  AND review_status = 'flagged_for_review' AND review_reason = 'excluded_kinetic_casualty_or_damage';
-- air_violation_id=748 reason=excluded_kinetic_casualty_or_damage
UPDATE raw_messages rm
SET status = 'pending'::message_status,
    match_result = NULL,
    error_message = NULL, processing_claim_stage = NULL,
    processing_claimed_at = NULL, processing_claimed_by = NULL
WHERE rm.id = (SELECT raw_message_id FROM air_violations WHERE id = 748)
  AND rm.status NOT IN ('materialized'::message_status, 'duplicate'::message_status)
  AND NOT EXISTS (SELECT 1 FROM incidents i
                  WHERE i.raw_message_id = rm.id AND i.is_deleted = false);
DELETE FROM air_violations WHERE id = 748
  AND review_status = 'flagged_for_review' AND review_reason = 'excluded_kinetic_casualty_or_damage';
-- air_violation_id=749 reason=excluded_kinetic_casualty_or_damage
UPDATE raw_messages rm
SET status = 'pending'::message_status,
    match_result = NULL,
    error_message = NULL, processing_claim_stage = NULL,
    processing_claimed_at = NULL, processing_claimed_by = NULL
WHERE rm.id = (SELECT raw_message_id FROM air_violations WHERE id = 749)
  AND rm.status NOT IN ('materialized'::message_status, 'duplicate'::message_status)
  AND NOT EXISTS (SELECT 1 FROM incidents i
                  WHERE i.raw_message_id = rm.id AND i.is_deleted = false);
DELETE FROM air_violations WHERE id = 749
  AND review_status = 'flagged_for_review' AND review_reason = 'excluded_kinetic_casualty_or_damage';
-- air_violation_id=750 reason=excluded_kinetic_casualty_or_damage
UPDATE raw_messages rm
SET status = 'pending'::message_status,
    match_result = NULL,
    error_message = NULL, processing_claim_stage = NULL,
    processing_claimed_at = NULL, processing_claimed_by = NULL
WHERE rm.id = (SELECT raw_message_id FROM air_violations WHERE id = 750)
  AND rm.status NOT IN ('materialized'::message_status, 'duplicate'::message_status)
  AND NOT EXISTS (SELECT 1 FROM incidents i
                  WHERE i.raw_message_id = rm.id AND i.is_deleted = false);
DELETE FROM air_violations WHERE id = 750
  AND review_status = 'flagged_for_review' AND review_reason = 'excluded_kinetic_casualty_or_damage';
-- air_violation_id=751 reason=excluded_kinetic_casualty_or_damage
UPDATE raw_messages rm
SET status = 'pending'::message_status,
    match_result = NULL,
    error_message = NULL, processing_claim_stage = NULL,
    processing_claimed_at = NULL, processing_claimed_by = NULL
WHERE rm.id = (SELECT raw_message_id FROM air_violations WHERE id = 751)
  AND rm.status NOT IN ('materialized'::message_status, 'duplicate'::message_status)
  AND NOT EXISTS (SELECT 1 FROM incidents i
                  WHERE i.raw_message_id = rm.id AND i.is_deleted = false);
DELETE FROM air_violations WHERE id = 751
  AND review_status = 'flagged_for_review' AND review_reason = 'excluded_kinetic_casualty_or_damage';
-- air_violation_id=752 reason=excluded_kinetic_casualty_or_damage
UPDATE raw_messages rm
SET status = 'pending'::message_status,
    match_result = NULL,
    error_message = NULL, processing_claim_stage = NULL,
    processing_claimed_at = NULL, processing_claimed_by = NULL
WHERE rm.id = (SELECT raw_message_id FROM air_violations WHERE id = 752)
  AND rm.status NOT IN ('materialized'::message_status, 'duplicate'::message_status)
  AND NOT EXISTS (SELECT 1 FROM incidents i
                  WHERE i.raw_message_id = rm.id AND i.is_deleted = false);
DELETE FROM air_violations WHERE id = 752
  AND review_status = 'flagged_for_review' AND review_reason = 'excluded_kinetic_casualty_or_damage';
-- air_violation_id=753 reason=excluded_kinetic_casualty_or_damage
UPDATE raw_messages rm
SET status = 'pending'::message_status,
    match_result = NULL,
    error_message = NULL, processing_claim_stage = NULL,
    processing_claimed_at = NULL, processing_claimed_by = NULL
WHERE rm.id = (SELECT raw_message_id FROM air_violations WHERE id = 753)
  AND rm.status NOT IN ('materialized'::message_status, 'duplicate'::message_status)
  AND NOT EXISTS (SELECT 1 FROM incidents i
                  WHERE i.raw_message_id = rm.id AND i.is_deleted = false);
DELETE FROM air_violations WHERE id = 753
  AND review_status = 'flagged_for_review' AND review_reason = 'excluded_kinetic_casualty_or_damage';
-- air_violation_id=754 reason=excluded_kinetic_casualty_or_damage
UPDATE raw_messages rm
SET status = 'pending'::message_status,
    match_result = NULL,
    error_message = NULL, processing_claim_stage = NULL,
    processing_claimed_at = NULL, processing_claimed_by = NULL
WHERE rm.id = (SELECT raw_message_id FROM air_violations WHERE id = 754)
  AND rm.status NOT IN ('materialized'::message_status, 'duplicate'::message_status)
  AND NOT EXISTS (SELECT 1 FROM incidents i
                  WHERE i.raw_message_id = rm.id AND i.is_deleted = false);
DELETE FROM air_violations WHERE id = 754
  AND review_status = 'flagged_for_review' AND review_reason = 'excluded_kinetic_casualty_or_damage';
-- air_violation_id=755 reason=excluded_kinetic_casualty_or_damage
UPDATE raw_messages rm
SET status = 'pending'::message_status,
    match_result = NULL,
    error_message = NULL, processing_claim_stage = NULL,
    processing_claimed_at = NULL, processing_claimed_by = NULL
WHERE rm.id = (SELECT raw_message_id FROM air_violations WHERE id = 755)
  AND rm.status NOT IN ('materialized'::message_status, 'duplicate'::message_status)
  AND NOT EXISTS (SELECT 1 FROM incidents i
                  WHERE i.raw_message_id = rm.id AND i.is_deleted = false);
DELETE FROM air_violations WHERE id = 755
  AND review_status = 'flagged_for_review' AND review_reason = 'excluded_kinetic_casualty_or_damage';
-- air_violation_id=756 reason=excluded_kinetic_casualty_or_damage
UPDATE raw_messages rm
SET status = 'pending'::message_status,
    match_result = NULL,
    error_message = NULL, processing_claim_stage = NULL,
    processing_claimed_at = NULL, processing_claimed_by = NULL
WHERE rm.id = (SELECT raw_message_id FROM air_violations WHERE id = 756)
  AND rm.status NOT IN ('materialized'::message_status, 'duplicate'::message_status)
  AND NOT EXISTS (SELECT 1 FROM incidents i
                  WHERE i.raw_message_id = rm.id AND i.is_deleted = false);
DELETE FROM air_violations WHERE id = 756
  AND review_status = 'flagged_for_review' AND review_reason = 'excluded_kinetic_casualty_or_damage';
-- air_violation_id=757 reason=excluded_kinetic_casualty_or_damage
UPDATE raw_messages rm
SET status = 'pending'::message_status,
    match_result = NULL,
    error_message = NULL, processing_claim_stage = NULL,
    processing_claimed_at = NULL, processing_claimed_by = NULL
WHERE rm.id = (SELECT raw_message_id FROM air_violations WHERE id = 757)
  AND rm.status NOT IN ('materialized'::message_status, 'duplicate'::message_status)
  AND NOT EXISTS (SELECT 1 FROM incidents i
                  WHERE i.raw_message_id = rm.id AND i.is_deleted = false);
DELETE FROM air_violations WHERE id = 757
  AND review_status = 'flagged_for_review' AND review_reason = 'excluded_kinetic_casualty_or_damage';
-- air_violation_id=758 reason=excluded_kinetic_casualty_or_damage
UPDATE raw_messages rm
SET status = 'pending'::message_status,
    match_result = NULL,
    error_message = NULL, processing_claim_stage = NULL,
    processing_claimed_at = NULL, processing_claimed_by = NULL
WHERE rm.id = (SELECT raw_message_id FROM air_violations WHERE id = 758)
  AND rm.status NOT IN ('materialized'::message_status, 'duplicate'::message_status)
  AND NOT EXISTS (SELECT 1 FROM incidents i
                  WHERE i.raw_message_id = rm.id AND i.is_deleted = false);
DELETE FROM air_violations WHERE id = 758
  AND review_status = 'flagged_for_review' AND review_reason = 'excluded_kinetic_casualty_or_damage';
-- air_violation_id=759 reason=excluded_kinetic_casualty_or_damage
UPDATE raw_messages rm
SET status = 'pending'::message_status,
    match_result = NULL,
    error_message = NULL, processing_claim_stage = NULL,
    processing_claimed_at = NULL, processing_claimed_by = NULL
WHERE rm.id = (SELECT raw_message_id FROM air_violations WHERE id = 759)
  AND rm.status NOT IN ('materialized'::message_status, 'duplicate'::message_status)
  AND NOT EXISTS (SELECT 1 FROM incidents i
                  WHERE i.raw_message_id = rm.id AND i.is_deleted = false);
DELETE FROM air_violations WHERE id = 759
  AND review_status = 'flagged_for_review' AND review_reason = 'excluded_kinetic_casualty_or_damage';
-- air_violation_id=760 reason=excluded_kinetic_casualty_or_damage
UPDATE raw_messages rm
SET status = 'pending'::message_status,
    match_result = NULL,
    error_message = NULL, processing_claim_stage = NULL,
    processing_claimed_at = NULL, processing_claimed_by = NULL
WHERE rm.id = (SELECT raw_message_id FROM air_violations WHERE id = 760)
  AND rm.status NOT IN ('materialized'::message_status, 'duplicate'::message_status)
  AND NOT EXISTS (SELECT 1 FROM incidents i
                  WHERE i.raw_message_id = rm.id AND i.is_deleted = false);
DELETE FROM air_violations WHERE id = 760
  AND review_status = 'flagged_for_review' AND review_reason = 'excluded_kinetic_casualty_or_damage';
-- air_violation_id=761 reason=excluded_kinetic_casualty_or_damage
UPDATE raw_messages rm
SET status = 'pending'::message_status,
    match_result = NULL,
    error_message = NULL, processing_claim_stage = NULL,
    processing_claimed_at = NULL, processing_claimed_by = NULL
WHERE rm.id = (SELECT raw_message_id FROM air_violations WHERE id = 761)
  AND rm.status NOT IN ('materialized'::message_status, 'duplicate'::message_status)
  AND NOT EXISTS (SELECT 1 FROM incidents i
                  WHERE i.raw_message_id = rm.id AND i.is_deleted = false);
DELETE FROM air_violations WHERE id = 761
  AND review_status = 'flagged_for_review' AND review_reason = 'excluded_kinetic_casualty_or_damage';
-- air_violation_id=762 reason=excluded_kinetic_casualty_or_damage
UPDATE raw_messages rm
SET status = 'pending'::message_status,
    match_result = NULL,
    error_message = NULL, processing_claim_stage = NULL,
    processing_claimed_at = NULL, processing_claimed_by = NULL
WHERE rm.id = (SELECT raw_message_id FROM air_violations WHERE id = 762)
  AND rm.status NOT IN ('materialized'::message_status, 'duplicate'::message_status)
  AND NOT EXISTS (SELECT 1 FROM incidents i
                  WHERE i.raw_message_id = rm.id AND i.is_deleted = false);
DELETE FROM air_violations WHERE id = 762
  AND review_status = 'flagged_for_review' AND review_reason = 'excluded_kinetic_casualty_or_damage';
-- air_violation_id=763 reason=excluded_kinetic_casualty_or_damage
UPDATE raw_messages rm
SET status = 'pending'::message_status,
    match_result = NULL,
    error_message = NULL, processing_claim_stage = NULL,
    processing_claimed_at = NULL, processing_claimed_by = NULL
WHERE rm.id = (SELECT raw_message_id FROM air_violations WHERE id = 763)
  AND rm.status NOT IN ('materialized'::message_status, 'duplicate'::message_status)
  AND NOT EXISTS (SELECT 1 FROM incidents i
                  WHERE i.raw_message_id = rm.id AND i.is_deleted = false);
DELETE FROM air_violations WHERE id = 763
  AND review_status = 'flagged_for_review' AND review_reason = 'excluded_kinetic_casualty_or_damage';
-- air_violation_id=764 reason=excluded_kinetic_casualty_or_damage
UPDATE raw_messages rm
SET status = 'pending'::message_status,
    match_result = NULL,
    error_message = NULL, processing_claim_stage = NULL,
    processing_claimed_at = NULL, processing_claimed_by = NULL
WHERE rm.id = (SELECT raw_message_id FROM air_violations WHERE id = 764)
  AND rm.status NOT IN ('materialized'::message_status, 'duplicate'::message_status)
  AND NOT EXISTS (SELECT 1 FROM incidents i
                  WHERE i.raw_message_id = rm.id AND i.is_deleted = false);
DELETE FROM air_violations WHERE id = 764
  AND review_status = 'flagged_for_review' AND review_reason = 'excluded_kinetic_casualty_or_damage';
-- air_violation_id=765 reason=excluded_kinetic_casualty_or_damage
UPDATE raw_messages rm
SET status = 'pending'::message_status,
    match_result = NULL,
    error_message = NULL, processing_claim_stage = NULL,
    processing_claimed_at = NULL, processing_claimed_by = NULL
WHERE rm.id = (SELECT raw_message_id FROM air_violations WHERE id = 765)
  AND rm.status NOT IN ('materialized'::message_status, 'duplicate'::message_status)
  AND NOT EXISTS (SELECT 1 FROM incidents i
                  WHERE i.raw_message_id = rm.id AND i.is_deleted = false);
DELETE FROM air_violations WHERE id = 765
  AND review_status = 'flagged_for_review' AND review_reason = 'excluded_kinetic_casualty_or_damage';
-- air_violation_id=766 reason=excluded_kinetic_casualty_or_damage
UPDATE raw_messages rm
SET status = 'pending'::message_status,
    match_result = NULL,
    error_message = NULL, processing_claim_stage = NULL,
    processing_claimed_at = NULL, processing_claimed_by = NULL
WHERE rm.id = (SELECT raw_message_id FROM air_violations WHERE id = 766)
  AND rm.status NOT IN ('materialized'::message_status, 'duplicate'::message_status)
  AND NOT EXISTS (SELECT 1 FROM incidents i
                  WHERE i.raw_message_id = rm.id AND i.is_deleted = false);
DELETE FROM air_violations WHERE id = 766
  AND review_status = 'flagged_for_review' AND review_reason = 'excluded_kinetic_casualty_or_damage';
-- air_violation_id=767 reason=excluded_kinetic_casualty_or_damage
UPDATE raw_messages rm
SET status = 'pending'::message_status,
    match_result = NULL,
    error_message = NULL, processing_claim_stage = NULL,
    processing_claimed_at = NULL, processing_claimed_by = NULL
WHERE rm.id = (SELECT raw_message_id FROM air_violations WHERE id = 767)
  AND rm.status NOT IN ('materialized'::message_status, 'duplicate'::message_status)
  AND NOT EXISTS (SELECT 1 FROM incidents i
                  WHERE i.raw_message_id = rm.id AND i.is_deleted = false);
DELETE FROM air_violations WHERE id = 767
  AND review_status = 'flagged_for_review' AND review_reason = 'excluded_kinetic_casualty_or_damage';
-- air_violation_id=768 reason=excluded_kinetic_casualty_or_damage
UPDATE raw_messages rm
SET status = 'pending'::message_status,
    match_result = NULL,
    error_message = NULL, processing_claim_stage = NULL,
    processing_claimed_at = NULL, processing_claimed_by = NULL
WHERE rm.id = (SELECT raw_message_id FROM air_violations WHERE id = 768)
  AND rm.status NOT IN ('materialized'::message_status, 'duplicate'::message_status)
  AND NOT EXISTS (SELECT 1 FROM incidents i
                  WHERE i.raw_message_id = rm.id AND i.is_deleted = false);
DELETE FROM air_violations WHERE id = 768
  AND review_status = 'flagged_for_review' AND review_reason = 'excluded_kinetic_casualty_or_damage';
-- air_violation_id=769 reason=excluded_kinetic_casualty_or_damage
UPDATE raw_messages rm
SET status = 'pending'::message_status,
    match_result = NULL,
    error_message = NULL, processing_claim_stage = NULL,
    processing_claimed_at = NULL, processing_claimed_by = NULL
WHERE rm.id = (SELECT raw_message_id FROM air_violations WHERE id = 769)
  AND rm.status NOT IN ('materialized'::message_status, 'duplicate'::message_status)
  AND NOT EXISTS (SELECT 1 FROM incidents i
                  WHERE i.raw_message_id = rm.id AND i.is_deleted = false);
DELETE FROM air_violations WHERE id = 769
  AND review_status = 'flagged_for_review' AND review_reason = 'excluded_kinetic_casualty_or_damage';
-- air_violation_id=770 reason=excluded_kinetic_casualty_or_damage
UPDATE raw_messages rm
SET status = 'pending'::message_status,
    match_result = NULL,
    error_message = NULL, processing_claim_stage = NULL,
    processing_claimed_at = NULL, processing_claimed_by = NULL
WHERE rm.id = (SELECT raw_message_id FROM air_violations WHERE id = 770)
  AND rm.status NOT IN ('materialized'::message_status, 'duplicate'::message_status)
  AND NOT EXISTS (SELECT 1 FROM incidents i
                  WHERE i.raw_message_id = rm.id AND i.is_deleted = false);
DELETE FROM air_violations WHERE id = 770
  AND review_status = 'flagged_for_review' AND review_reason = 'excluded_kinetic_casualty_or_damage';
-- air_violation_id=771 reason=excluded_kinetic_casualty_or_damage
UPDATE raw_messages rm
SET status = 'pending'::message_status,
    match_result = NULL,
    error_message = NULL, processing_claim_stage = NULL,
    processing_claimed_at = NULL, processing_claimed_by = NULL
WHERE rm.id = (SELECT raw_message_id FROM air_violations WHERE id = 771)
  AND rm.status NOT IN ('materialized'::message_status, 'duplicate'::message_status)
  AND NOT EXISTS (SELECT 1 FROM incidents i
                  WHERE i.raw_message_id = rm.id AND i.is_deleted = false);
DELETE FROM air_violations WHERE id = 771
  AND review_status = 'flagged_for_review' AND review_reason = 'excluded_kinetic_casualty_or_damage';
-- air_violation_id=772 reason=excluded_kinetic_casualty_or_damage
UPDATE raw_messages rm
SET status = 'pending'::message_status,
    match_result = NULL,
    error_message = NULL, processing_claim_stage = NULL,
    processing_claimed_at = NULL, processing_claimed_by = NULL
WHERE rm.id = (SELECT raw_message_id FROM air_violations WHERE id = 772)
  AND rm.status NOT IN ('materialized'::message_status, 'duplicate'::message_status)
  AND NOT EXISTS (SELECT 1 FROM incidents i
                  WHERE i.raw_message_id = rm.id AND i.is_deleted = false);
DELETE FROM air_violations WHERE id = 772
  AND review_status = 'flagged_for_review' AND review_reason = 'excluded_kinetic_casualty_or_damage';
-- air_violation_id=773 reason=excluded_kinetic_casualty_or_damage
UPDATE raw_messages rm
SET status = 'pending'::message_status,
    match_result = NULL,
    error_message = NULL, processing_claim_stage = NULL,
    processing_claimed_at = NULL, processing_claimed_by = NULL
WHERE rm.id = (SELECT raw_message_id FROM air_violations WHERE id = 773)
  AND rm.status NOT IN ('materialized'::message_status, 'duplicate'::message_status)
  AND NOT EXISTS (SELECT 1 FROM incidents i
                  WHERE i.raw_message_id = rm.id AND i.is_deleted = false);
DELETE FROM air_violations WHERE id = 773
  AND review_status = 'flagged_for_review' AND review_reason = 'excluded_kinetic_casualty_or_damage';
-- air_violation_id=774 reason=excluded_kinetic_casualty_or_damage
UPDATE raw_messages rm
SET status = 'pending'::message_status,
    match_result = NULL,
    error_message = NULL, processing_claim_stage = NULL,
    processing_claimed_at = NULL, processing_claimed_by = NULL
WHERE rm.id = (SELECT raw_message_id FROM air_violations WHERE id = 774)
  AND rm.status NOT IN ('materialized'::message_status, 'duplicate'::message_status)
  AND NOT EXISTS (SELECT 1 FROM incidents i
                  WHERE i.raw_message_id = rm.id AND i.is_deleted = false);
DELETE FROM air_violations WHERE id = 774
  AND review_status = 'flagged_for_review' AND review_reason = 'excluded_kinetic_casualty_or_damage';
-- air_violation_id=775 reason=excluded_kinetic_casualty_or_damage
UPDATE raw_messages rm
SET status = 'pending'::message_status,
    match_result = NULL,
    error_message = NULL, processing_claim_stage = NULL,
    processing_claimed_at = NULL, processing_claimed_by = NULL
WHERE rm.id = (SELECT raw_message_id FROM air_violations WHERE id = 775)
  AND rm.status NOT IN ('materialized'::message_status, 'duplicate'::message_status)
  AND NOT EXISTS (SELECT 1 FROM incidents i
                  WHERE i.raw_message_id = rm.id AND i.is_deleted = false);
DELETE FROM air_violations WHERE id = 775
  AND review_status = 'flagged_for_review' AND review_reason = 'excluded_kinetic_casualty_or_damage';
-- air_violation_id=776 reason=excluded_kinetic_casualty_or_damage
UPDATE raw_messages rm
SET status = 'pending'::message_status,
    match_result = NULL,
    error_message = NULL, processing_claim_stage = NULL,
    processing_claimed_at = NULL, processing_claimed_by = NULL
WHERE rm.id = (SELECT raw_message_id FROM air_violations WHERE id = 776)
  AND rm.status NOT IN ('materialized'::message_status, 'duplicate'::message_status)
  AND NOT EXISTS (SELECT 1 FROM incidents i
                  WHERE i.raw_message_id = rm.id AND i.is_deleted = false);
DELETE FROM air_violations WHERE id = 776
  AND review_status = 'flagged_for_review' AND review_reason = 'excluded_kinetic_casualty_or_damage';
-- air_violation_id=777 reason=excluded_kinetic_casualty_or_damage
UPDATE raw_messages rm
SET status = 'pending'::message_status,
    match_result = NULL,
    error_message = NULL, processing_claim_stage = NULL,
    processing_claimed_at = NULL, processing_claimed_by = NULL
WHERE rm.id = (SELECT raw_message_id FROM air_violations WHERE id = 777)
  AND rm.status NOT IN ('materialized'::message_status, 'duplicate'::message_status)
  AND NOT EXISTS (SELECT 1 FROM incidents i
                  WHERE i.raw_message_id = rm.id AND i.is_deleted = false);
DELETE FROM air_violations WHERE id = 777
  AND review_status = 'flagged_for_review' AND review_reason = 'excluded_kinetic_casualty_or_damage';
-- air_violation_id=778 reason=excluded_kinetic_casualty_or_damage
UPDATE raw_messages rm
SET status = 'pending'::message_status,
    match_result = NULL,
    error_message = NULL, processing_claim_stage = NULL,
    processing_claimed_at = NULL, processing_claimed_by = NULL
WHERE rm.id = (SELECT raw_message_id FROM air_violations WHERE id = 778)
  AND rm.status NOT IN ('materialized'::message_status, 'duplicate'::message_status)
  AND NOT EXISTS (SELECT 1 FROM incidents i
                  WHERE i.raw_message_id = rm.id AND i.is_deleted = false);
DELETE FROM air_violations WHERE id = 778
  AND review_status = 'flagged_for_review' AND review_reason = 'excluded_kinetic_casualty_or_damage';
-- air_violation_id=779 reason=excluded_kinetic_casualty_or_damage
UPDATE raw_messages rm
SET status = 'pending'::message_status,
    match_result = NULL,
    error_message = NULL, processing_claim_stage = NULL,
    processing_claimed_at = NULL, processing_claimed_by = NULL
WHERE rm.id = (SELECT raw_message_id FROM air_violations WHERE id = 779)
  AND rm.status NOT IN ('materialized'::message_status, 'duplicate'::message_status)
  AND NOT EXISTS (SELECT 1 FROM incidents i
                  WHERE i.raw_message_id = rm.id AND i.is_deleted = false);
DELETE FROM air_violations WHERE id = 779
  AND review_status = 'flagged_for_review' AND review_reason = 'excluded_kinetic_casualty_or_damage';
-- air_violation_id=780 reason=excluded_kinetic_casualty_or_damage
UPDATE raw_messages rm
SET status = 'pending'::message_status,
    match_result = NULL,
    error_message = NULL, processing_claim_stage = NULL,
    processing_claimed_at = NULL, processing_claimed_by = NULL
WHERE rm.id = (SELECT raw_message_id FROM air_violations WHERE id = 780)
  AND rm.status NOT IN ('materialized'::message_status, 'duplicate'::message_status)
  AND NOT EXISTS (SELECT 1 FROM incidents i
                  WHERE i.raw_message_id = rm.id AND i.is_deleted = false);
DELETE FROM air_violations WHERE id = 780
  AND review_status = 'flagged_for_review' AND review_reason = 'excluded_kinetic_casualty_or_damage';
-- air_violation_id=781 reason=excluded_kinetic_casualty_or_damage
UPDATE raw_messages rm
SET status = 'pending'::message_status,
    match_result = NULL,
    error_message = NULL, processing_claim_stage = NULL,
    processing_claimed_at = NULL, processing_claimed_by = NULL
WHERE rm.id = (SELECT raw_message_id FROM air_violations WHERE id = 781)
  AND rm.status NOT IN ('materialized'::message_status, 'duplicate'::message_status)
  AND NOT EXISTS (SELECT 1 FROM incidents i
                  WHERE i.raw_message_id = rm.id AND i.is_deleted = false);
DELETE FROM air_violations WHERE id = 781
  AND review_status = 'flagged_for_review' AND review_reason = 'excluded_kinetic_casualty_or_damage';
-- air_violation_id=782 reason=excluded_kinetic_casualty_or_damage
UPDATE raw_messages rm
SET status = 'pending'::message_status,
    match_result = NULL,
    error_message = NULL, processing_claim_stage = NULL,
    processing_claimed_at = NULL, processing_claimed_by = NULL
WHERE rm.id = (SELECT raw_message_id FROM air_violations WHERE id = 782)
  AND rm.status NOT IN ('materialized'::message_status, 'duplicate'::message_status)
  AND NOT EXISTS (SELECT 1 FROM incidents i
                  WHERE i.raw_message_id = rm.id AND i.is_deleted = false);
DELETE FROM air_violations WHERE id = 782
  AND review_status = 'flagged_for_review' AND review_reason = 'excluded_kinetic_casualty_or_damage';
-- air_violation_id=783 reason=excluded_kinetic_casualty_or_damage
UPDATE raw_messages rm
SET status = 'pending'::message_status,
    match_result = NULL,
    error_message = NULL, processing_claim_stage = NULL,
    processing_claimed_at = NULL, processing_claimed_by = NULL
WHERE rm.id = (SELECT raw_message_id FROM air_violations WHERE id = 783)
  AND rm.status NOT IN ('materialized'::message_status, 'duplicate'::message_status)
  AND NOT EXISTS (SELECT 1 FROM incidents i
                  WHERE i.raw_message_id = rm.id AND i.is_deleted = false);
DELETE FROM air_violations WHERE id = 783
  AND review_status = 'flagged_for_review' AND review_reason = 'excluded_kinetic_casualty_or_damage';
-- air_violation_id=784 reason=excluded_kinetic_casualty_or_damage
UPDATE raw_messages rm
SET status = 'pending'::message_status,
    match_result = NULL,
    error_message = NULL, processing_claim_stage = NULL,
    processing_claimed_at = NULL, processing_claimed_by = NULL
WHERE rm.id = (SELECT raw_message_id FROM air_violations WHERE id = 784)
  AND rm.status NOT IN ('materialized'::message_status, 'duplicate'::message_status)
  AND NOT EXISTS (SELECT 1 FROM incidents i
                  WHERE i.raw_message_id = rm.id AND i.is_deleted = false);
DELETE FROM air_violations WHERE id = 784
  AND review_status = 'flagged_for_review' AND review_reason = 'excluded_kinetic_casualty_or_damage';
-- air_violation_id=785 reason=excluded_kinetic_casualty_or_damage
UPDATE raw_messages rm
SET status = 'pending'::message_status,
    match_result = NULL,
    error_message = NULL, processing_claim_stage = NULL,
    processing_claimed_at = NULL, processing_claimed_by = NULL
WHERE rm.id = (SELECT raw_message_id FROM air_violations WHERE id = 785)
  AND rm.status NOT IN ('materialized'::message_status, 'duplicate'::message_status)
  AND NOT EXISTS (SELECT 1 FROM incidents i
                  WHERE i.raw_message_id = rm.id AND i.is_deleted = false);
DELETE FROM air_violations WHERE id = 785
  AND review_status = 'flagged_for_review' AND review_reason = 'excluded_kinetic_casualty_or_damage';
-- air_violation_id=786 reason=excluded_kinetic_casualty_or_damage
UPDATE raw_messages rm
SET status = 'pending'::message_status,
    match_result = NULL,
    error_message = NULL, processing_claim_stage = NULL,
    processing_claimed_at = NULL, processing_claimed_by = NULL
WHERE rm.id = (SELECT raw_message_id FROM air_violations WHERE id = 786)
  AND rm.status NOT IN ('materialized'::message_status, 'duplicate'::message_status)
  AND NOT EXISTS (SELECT 1 FROM incidents i
                  WHERE i.raw_message_id = rm.id AND i.is_deleted = false);
DELETE FROM air_violations WHERE id = 786
  AND review_status = 'flagged_for_review' AND review_reason = 'excluded_kinetic_casualty_or_damage';
-- air_violation_id=787 reason=excluded_kinetic_casualty_or_damage
UPDATE raw_messages rm
SET status = 'pending'::message_status,
    match_result = NULL,
    error_message = NULL, processing_claim_stage = NULL,
    processing_claimed_at = NULL, processing_claimed_by = NULL
WHERE rm.id = (SELECT raw_message_id FROM air_violations WHERE id = 787)
  AND rm.status NOT IN ('materialized'::message_status, 'duplicate'::message_status)
  AND NOT EXISTS (SELECT 1 FROM incidents i
                  WHERE i.raw_message_id = rm.id AND i.is_deleted = false);
DELETE FROM air_violations WHERE id = 787
  AND review_status = 'flagged_for_review' AND review_reason = 'excluded_kinetic_casualty_or_damage';
-- air_violation_id=789 reason=excluded_kinetic_casualty_or_damage
UPDATE raw_messages rm
SET status = 'pending'::message_status,
    match_result = NULL,
    error_message = NULL, processing_claim_stage = NULL,
    processing_claimed_at = NULL, processing_claimed_by = NULL
WHERE rm.id = (SELECT raw_message_id FROM air_violations WHERE id = 789)
  AND rm.status NOT IN ('materialized'::message_status, 'duplicate'::message_status)
  AND NOT EXISTS (SELECT 1 FROM incidents i
                  WHERE i.raw_message_id = rm.id AND i.is_deleted = false);
DELETE FROM air_violations WHERE id = 789
  AND review_status = 'flagged_for_review' AND review_reason = 'excluded_kinetic_casualty_or_damage';
-- air_violation_id=790 reason=excluded_kinetic_casualty_or_damage
UPDATE raw_messages rm
SET status = 'pending'::message_status,
    match_result = NULL,
    error_message = NULL, processing_claim_stage = NULL,
    processing_claimed_at = NULL, processing_claimed_by = NULL
WHERE rm.id = (SELECT raw_message_id FROM air_violations WHERE id = 790)
  AND rm.status NOT IN ('materialized'::message_status, 'duplicate'::message_status)
  AND NOT EXISTS (SELECT 1 FROM incidents i
                  WHERE i.raw_message_id = rm.id AND i.is_deleted = false);
DELETE FROM air_violations WHERE id = 790
  AND review_status = 'flagged_for_review' AND review_reason = 'excluded_kinetic_casualty_or_damage';
-- air_violation_id=791 reason=excluded_kinetic_casualty_or_damage
UPDATE raw_messages rm
SET status = 'pending'::message_status,
    match_result = NULL,
    error_message = NULL, processing_claim_stage = NULL,
    processing_claimed_at = NULL, processing_claimed_by = NULL
WHERE rm.id = (SELECT raw_message_id FROM air_violations WHERE id = 791)
  AND rm.status NOT IN ('materialized'::message_status, 'duplicate'::message_status)
  AND NOT EXISTS (SELECT 1 FROM incidents i
                  WHERE i.raw_message_id = rm.id AND i.is_deleted = false);
DELETE FROM air_violations WHERE id = 791
  AND review_status = 'flagged_for_review' AND review_reason = 'excluded_kinetic_casualty_or_damage';
-- air_violation_id=792 reason=excluded_kinetic_casualty_or_damage
UPDATE raw_messages rm
SET status = 'pending'::message_status,
    match_result = NULL,
    error_message = NULL, processing_claim_stage = NULL,
    processing_claimed_at = NULL, processing_claimed_by = NULL
WHERE rm.id = (SELECT raw_message_id FROM air_violations WHERE id = 792)
  AND rm.status NOT IN ('materialized'::message_status, 'duplicate'::message_status)
  AND NOT EXISTS (SELECT 1 FROM incidents i
                  WHERE i.raw_message_id = rm.id AND i.is_deleted = false);
DELETE FROM air_violations WHERE id = 792
  AND review_status = 'flagged_for_review' AND review_reason = 'excluded_kinetic_casualty_or_damage';
-- air_violation_id=793 reason=excluded_kinetic_casualty_or_damage
UPDATE raw_messages rm
SET status = 'pending'::message_status,
    match_result = NULL,
    error_message = NULL, processing_claim_stage = NULL,
    processing_claimed_at = NULL, processing_claimed_by = NULL
WHERE rm.id = (SELECT raw_message_id FROM air_violations WHERE id = 793)
  AND rm.status NOT IN ('materialized'::message_status, 'duplicate'::message_status)
  AND NOT EXISTS (SELECT 1 FROM incidents i
                  WHERE i.raw_message_id = rm.id AND i.is_deleted = false);
DELETE FROM air_violations WHERE id = 793
  AND review_status = 'flagged_for_review' AND review_reason = 'excluded_kinetic_casualty_or_damage';
-- air_violation_id=794 reason=excluded_kinetic_casualty_or_damage
UPDATE raw_messages rm
SET status = 'pending'::message_status,
    match_result = NULL,
    error_message = NULL, processing_claim_stage = NULL,
    processing_claimed_at = NULL, processing_claimed_by = NULL
WHERE rm.id = (SELECT raw_message_id FROM air_violations WHERE id = 794)
  AND rm.status NOT IN ('materialized'::message_status, 'duplicate'::message_status)
  AND NOT EXISTS (SELECT 1 FROM incidents i
                  WHERE i.raw_message_id = rm.id AND i.is_deleted = false);
DELETE FROM air_violations WHERE id = 794
  AND review_status = 'flagged_for_review' AND review_reason = 'excluded_kinetic_casualty_or_damage';
-- air_violation_id=795 reason=excluded_kinetic_casualty_or_damage
UPDATE raw_messages rm
SET status = 'pending'::message_status,
    match_result = NULL,
    error_message = NULL, processing_claim_stage = NULL,
    processing_claimed_at = NULL, processing_claimed_by = NULL
WHERE rm.id = (SELECT raw_message_id FROM air_violations WHERE id = 795)
  AND rm.status NOT IN ('materialized'::message_status, 'duplicate'::message_status)
  AND NOT EXISTS (SELECT 1 FROM incidents i
                  WHERE i.raw_message_id = rm.id AND i.is_deleted = false);
DELETE FROM air_violations WHERE id = 795
  AND review_status = 'flagged_for_review' AND review_reason = 'excluded_kinetic_casualty_or_damage';
-- air_violation_id=796 reason=excluded_kinetic_casualty_or_damage
UPDATE raw_messages rm
SET status = 'pending'::message_status,
    match_result = NULL,
    error_message = NULL, processing_claim_stage = NULL,
    processing_claimed_at = NULL, processing_claimed_by = NULL
WHERE rm.id = (SELECT raw_message_id FROM air_violations WHERE id = 796)
  AND rm.status NOT IN ('materialized'::message_status, 'duplicate'::message_status)
  AND NOT EXISTS (SELECT 1 FROM incidents i
                  WHERE i.raw_message_id = rm.id AND i.is_deleted = false);
DELETE FROM air_violations WHERE id = 796
  AND review_status = 'flagged_for_review' AND review_reason = 'excluded_kinetic_casualty_or_damage';
-- air_violation_id=797 reason=excluded_kinetic_casualty_or_damage
UPDATE raw_messages rm
SET status = 'pending'::message_status,
    match_result = NULL,
    error_message = NULL, processing_claim_stage = NULL,
    processing_claimed_at = NULL, processing_claimed_by = NULL
WHERE rm.id = (SELECT raw_message_id FROM air_violations WHERE id = 797)
  AND rm.status NOT IN ('materialized'::message_status, 'duplicate'::message_status)
  AND NOT EXISTS (SELECT 1 FROM incidents i
                  WHERE i.raw_message_id = rm.id AND i.is_deleted = false);
DELETE FROM air_violations WHERE id = 797
  AND review_status = 'flagged_for_review' AND review_reason = 'excluded_kinetic_casualty_or_damage';
-- air_violation_id=798 reason=excluded_kinetic_casualty_or_damage
UPDATE raw_messages rm
SET status = 'pending'::message_status,
    match_result = NULL,
    error_message = NULL, processing_claim_stage = NULL,
    processing_claimed_at = NULL, processing_claimed_by = NULL
WHERE rm.id = (SELECT raw_message_id FROM air_violations WHERE id = 798)
  AND rm.status NOT IN ('materialized'::message_status, 'duplicate'::message_status)
  AND NOT EXISTS (SELECT 1 FROM incidents i
                  WHERE i.raw_message_id = rm.id AND i.is_deleted = false);
DELETE FROM air_violations WHERE id = 798
  AND review_status = 'flagged_for_review' AND review_reason = 'excluded_kinetic_casualty_or_damage';
-- air_violation_id=799 reason=excluded_kinetic_casualty_or_damage
UPDATE raw_messages rm
SET status = 'pending'::message_status,
    match_result = NULL,
    error_message = NULL, processing_claim_stage = NULL,
    processing_claimed_at = NULL, processing_claimed_by = NULL
WHERE rm.id = (SELECT raw_message_id FROM air_violations WHERE id = 799)
  AND rm.status NOT IN ('materialized'::message_status, 'duplicate'::message_status)
  AND NOT EXISTS (SELECT 1 FROM incidents i
                  WHERE i.raw_message_id = rm.id AND i.is_deleted = false);
DELETE FROM air_violations WHERE id = 799
  AND review_status = 'flagged_for_review' AND review_reason = 'excluded_kinetic_casualty_or_damage';
-- air_violation_id=800 reason=excluded_kinetic_casualty_or_damage
UPDATE raw_messages rm
SET status = 'pending'::message_status,
    match_result = NULL,
    error_message = NULL, processing_claim_stage = NULL,
    processing_claimed_at = NULL, processing_claimed_by = NULL
WHERE rm.id = (SELECT raw_message_id FROM air_violations WHERE id = 800)
  AND rm.status NOT IN ('materialized'::message_status, 'duplicate'::message_status)
  AND NOT EXISTS (SELECT 1 FROM incidents i
                  WHERE i.raw_message_id = rm.id AND i.is_deleted = false);
DELETE FROM air_violations WHERE id = 800
  AND review_status = 'flagged_for_review' AND review_reason = 'excluded_kinetic_casualty_or_damage';
-- air_violation_id=801 reason=excluded_kinetic_casualty_or_damage
UPDATE raw_messages rm
SET status = 'pending'::message_status,
    match_result = NULL,
    error_message = NULL, processing_claim_stage = NULL,
    processing_claimed_at = NULL, processing_claimed_by = NULL
WHERE rm.id = (SELECT raw_message_id FROM air_violations WHERE id = 801)
  AND rm.status NOT IN ('materialized'::message_status, 'duplicate'::message_status)
  AND NOT EXISTS (SELECT 1 FROM incidents i
                  WHERE i.raw_message_id = rm.id AND i.is_deleted = false);
DELETE FROM air_violations WHERE id = 801
  AND review_status = 'flagged_for_review' AND review_reason = 'excluded_kinetic_casualty_or_damage';
-- air_violation_id=802 reason=excluded_kinetic_casualty_or_damage
UPDATE raw_messages rm
SET status = 'pending'::message_status,
    match_result = NULL,
    error_message = NULL, processing_claim_stage = NULL,
    processing_claimed_at = NULL, processing_claimed_by = NULL
WHERE rm.id = (SELECT raw_message_id FROM air_violations WHERE id = 802)
  AND rm.status NOT IN ('materialized'::message_status, 'duplicate'::message_status)
  AND NOT EXISTS (SELECT 1 FROM incidents i
                  WHERE i.raw_message_id = rm.id AND i.is_deleted = false);
DELETE FROM air_violations WHERE id = 802
  AND review_status = 'flagged_for_review' AND review_reason = 'excluded_kinetic_casualty_or_damage';
-- air_violation_id=803 reason=excluded_kinetic_casualty_or_damage
UPDATE raw_messages rm
SET status = 'pending'::message_status,
    match_result = NULL,
    error_message = NULL, processing_claim_stage = NULL,
    processing_claimed_at = NULL, processing_claimed_by = NULL
WHERE rm.id = (SELECT raw_message_id FROM air_violations WHERE id = 803)
  AND rm.status NOT IN ('materialized'::message_status, 'duplicate'::message_status)
  AND NOT EXISTS (SELECT 1 FROM incidents i
                  WHERE i.raw_message_id = rm.id AND i.is_deleted = false);
DELETE FROM air_violations WHERE id = 803
  AND review_status = 'flagged_for_review' AND review_reason = 'excluded_kinetic_casualty_or_damage';
-- air_violation_id=804 reason=excluded_kinetic_casualty_or_damage
UPDATE raw_messages rm
SET status = 'pending'::message_status,
    match_result = NULL,
    error_message = NULL, processing_claim_stage = NULL,
    processing_claimed_at = NULL, processing_claimed_by = NULL
WHERE rm.id = (SELECT raw_message_id FROM air_violations WHERE id = 804)
  AND rm.status NOT IN ('materialized'::message_status, 'duplicate'::message_status)
  AND NOT EXISTS (SELECT 1 FROM incidents i
                  WHERE i.raw_message_id = rm.id AND i.is_deleted = false);
DELETE FROM air_violations WHERE id = 804
  AND review_status = 'flagged_for_review' AND review_reason = 'excluded_kinetic_casualty_or_damage';
-- air_violation_id=805 reason=excluded_kinetic_casualty_or_damage
UPDATE raw_messages rm
SET status = 'pending'::message_status,
    match_result = NULL,
    error_message = NULL, processing_claim_stage = NULL,
    processing_claimed_at = NULL, processing_claimed_by = NULL
WHERE rm.id = (SELECT raw_message_id FROM air_violations WHERE id = 805)
  AND rm.status NOT IN ('materialized'::message_status, 'duplicate'::message_status)
  AND NOT EXISTS (SELECT 1 FROM incidents i
                  WHERE i.raw_message_id = rm.id AND i.is_deleted = false);
DELETE FROM air_violations WHERE id = 805
  AND review_status = 'flagged_for_review' AND review_reason = 'excluded_kinetic_casualty_or_damage';
-- air_violation_id=806 reason=excluded_kinetic_casualty_or_damage
UPDATE raw_messages rm
SET status = 'pending'::message_status,
    match_result = NULL,
    error_message = NULL, processing_claim_stage = NULL,
    processing_claimed_at = NULL, processing_claimed_by = NULL
WHERE rm.id = (SELECT raw_message_id FROM air_violations WHERE id = 806)
  AND rm.status NOT IN ('materialized'::message_status, 'duplicate'::message_status)
  AND NOT EXISTS (SELECT 1 FROM incidents i
                  WHERE i.raw_message_id = rm.id AND i.is_deleted = false);
DELETE FROM air_violations WHERE id = 806
  AND review_status = 'flagged_for_review' AND review_reason = 'excluded_kinetic_casualty_or_damage';
-- air_violation_id=807 reason=excluded_kinetic_casualty_or_damage
UPDATE raw_messages rm
SET status = 'pending'::message_status,
    match_result = NULL,
    error_message = NULL, processing_claim_stage = NULL,
    processing_claimed_at = NULL, processing_claimed_by = NULL
WHERE rm.id = (SELECT raw_message_id FROM air_violations WHERE id = 807)
  AND rm.status NOT IN ('materialized'::message_status, 'duplicate'::message_status)
  AND NOT EXISTS (SELECT 1 FROM incidents i
                  WHERE i.raw_message_id = rm.id AND i.is_deleted = false);
DELETE FROM air_violations WHERE id = 807
  AND review_status = 'flagged_for_review' AND review_reason = 'excluded_kinetic_casualty_or_damage';
-- air_violation_id=808 reason=excluded_kinetic_casualty_or_damage
UPDATE raw_messages rm
SET status = 'pending'::message_status,
    match_result = NULL,
    error_message = NULL, processing_claim_stage = NULL,
    processing_claimed_at = NULL, processing_claimed_by = NULL
WHERE rm.id = (SELECT raw_message_id FROM air_violations WHERE id = 808)
  AND rm.status NOT IN ('materialized'::message_status, 'duplicate'::message_status)
  AND NOT EXISTS (SELECT 1 FROM incidents i
                  WHERE i.raw_message_id = rm.id AND i.is_deleted = false);
DELETE FROM air_violations WHERE id = 808
  AND review_status = 'flagged_for_review' AND review_reason = 'excluded_kinetic_casualty_or_damage';
-- air_violation_id=809 reason=excluded_kinetic_casualty_or_damage
UPDATE raw_messages rm
SET status = 'pending'::message_status,
    match_result = NULL,
    error_message = NULL, processing_claim_stage = NULL,
    processing_claimed_at = NULL, processing_claimed_by = NULL
WHERE rm.id = (SELECT raw_message_id FROM air_violations WHERE id = 809)
  AND rm.status NOT IN ('materialized'::message_status, 'duplicate'::message_status)
  AND NOT EXISTS (SELECT 1 FROM incidents i
                  WHERE i.raw_message_id = rm.id AND i.is_deleted = false);
DELETE FROM air_violations WHERE id = 809
  AND review_status = 'flagged_for_review' AND review_reason = 'excluded_kinetic_casualty_or_damage';
-- air_violation_id=810 reason=excluded_kinetic_casualty_or_damage
UPDATE raw_messages rm
SET status = 'pending'::message_status,
    match_result = NULL,
    error_message = NULL, processing_claim_stage = NULL,
    processing_claimed_at = NULL, processing_claimed_by = NULL
WHERE rm.id = (SELECT raw_message_id FROM air_violations WHERE id = 810)
  AND rm.status NOT IN ('materialized'::message_status, 'duplicate'::message_status)
  AND NOT EXISTS (SELECT 1 FROM incidents i
                  WHERE i.raw_message_id = rm.id AND i.is_deleted = false);
DELETE FROM air_violations WHERE id = 810
  AND review_status = 'flagged_for_review' AND review_reason = 'excluded_kinetic_casualty_or_damage';
-- air_violation_id=811 reason=excluded_kinetic_casualty_or_damage
UPDATE raw_messages rm
SET status = 'pending'::message_status,
    match_result = NULL,
    error_message = NULL, processing_claim_stage = NULL,
    processing_claimed_at = NULL, processing_claimed_by = NULL
WHERE rm.id = (SELECT raw_message_id FROM air_violations WHERE id = 811)
  AND rm.status NOT IN ('materialized'::message_status, 'duplicate'::message_status)
  AND NOT EXISTS (SELECT 1 FROM incidents i
                  WHERE i.raw_message_id = rm.id AND i.is_deleted = false);
DELETE FROM air_violations WHERE id = 811
  AND review_status = 'flagged_for_review' AND review_reason = 'excluded_kinetic_casualty_or_damage';
-- air_violation_id=812 reason=excluded_kinetic_casualty_or_damage
UPDATE raw_messages rm
SET status = 'pending'::message_status,
    match_result = NULL,
    error_message = NULL, processing_claim_stage = NULL,
    processing_claimed_at = NULL, processing_claimed_by = NULL
WHERE rm.id = (SELECT raw_message_id FROM air_violations WHERE id = 812)
  AND rm.status NOT IN ('materialized'::message_status, 'duplicate'::message_status)
  AND NOT EXISTS (SELECT 1 FROM incidents i
                  WHERE i.raw_message_id = rm.id AND i.is_deleted = false);
DELETE FROM air_violations WHERE id = 812
  AND review_status = 'flagged_for_review' AND review_reason = 'excluded_kinetic_casualty_or_damage';
-- air_violation_id=813 reason=excluded_kinetic_casualty_or_damage
UPDATE raw_messages rm
SET status = 'pending'::message_status,
    match_result = NULL,
    error_message = NULL, processing_claim_stage = NULL,
    processing_claimed_at = NULL, processing_claimed_by = NULL
WHERE rm.id = (SELECT raw_message_id FROM air_violations WHERE id = 813)
  AND rm.status NOT IN ('materialized'::message_status, 'duplicate'::message_status)
  AND NOT EXISTS (SELECT 1 FROM incidents i
                  WHERE i.raw_message_id = rm.id AND i.is_deleted = false);
DELETE FROM air_violations WHERE id = 813
  AND review_status = 'flagged_for_review' AND review_reason = 'excluded_kinetic_casualty_or_damage';
-- air_violation_id=814 reason=excluded_kinetic_casualty_or_damage
UPDATE raw_messages rm
SET status = 'pending'::message_status,
    match_result = NULL,
    error_message = NULL, processing_claim_stage = NULL,
    processing_claimed_at = NULL, processing_claimed_by = NULL
WHERE rm.id = (SELECT raw_message_id FROM air_violations WHERE id = 814)
  AND rm.status NOT IN ('materialized'::message_status, 'duplicate'::message_status)
  AND NOT EXISTS (SELECT 1 FROM incidents i
                  WHERE i.raw_message_id = rm.id AND i.is_deleted = false);
DELETE FROM air_violations WHERE id = 814
  AND review_status = 'flagged_for_review' AND review_reason = 'excluded_kinetic_casualty_or_damage';
-- air_violation_id=815 reason=excluded_kinetic_casualty_or_damage
UPDATE raw_messages rm
SET status = 'pending'::message_status,
    match_result = NULL,
    error_message = NULL, processing_claim_stage = NULL,
    processing_claimed_at = NULL, processing_claimed_by = NULL
WHERE rm.id = (SELECT raw_message_id FROM air_violations WHERE id = 815)
  AND rm.status NOT IN ('materialized'::message_status, 'duplicate'::message_status)
  AND NOT EXISTS (SELECT 1 FROM incidents i
                  WHERE i.raw_message_id = rm.id AND i.is_deleted = false);
DELETE FROM air_violations WHERE id = 815
  AND review_status = 'flagged_for_review' AND review_reason = 'excluded_kinetic_casualty_or_damage';
-- air_violation_id=816 reason=excluded_kinetic_casualty_or_damage
UPDATE raw_messages rm
SET status = 'pending'::message_status,
    match_result = NULL,
    error_message = NULL, processing_claim_stage = NULL,
    processing_claimed_at = NULL, processing_claimed_by = NULL
WHERE rm.id = (SELECT raw_message_id FROM air_violations WHERE id = 816)
  AND rm.status NOT IN ('materialized'::message_status, 'duplicate'::message_status)
  AND NOT EXISTS (SELECT 1 FROM incidents i
                  WHERE i.raw_message_id = rm.id AND i.is_deleted = false);
DELETE FROM air_violations WHERE id = 816
  AND review_status = 'flagged_for_review' AND review_reason = 'excluded_kinetic_casualty_or_damage';
-- air_violation_id=817 reason=excluded_kinetic_casualty_or_damage
UPDATE raw_messages rm
SET status = 'pending'::message_status,
    match_result = NULL,
    error_message = NULL, processing_claim_stage = NULL,
    processing_claimed_at = NULL, processing_claimed_by = NULL
WHERE rm.id = (SELECT raw_message_id FROM air_violations WHERE id = 817)
  AND rm.status NOT IN ('materialized'::message_status, 'duplicate'::message_status)
  AND NOT EXISTS (SELECT 1 FROM incidents i
                  WHERE i.raw_message_id = rm.id AND i.is_deleted = false);
DELETE FROM air_violations WHERE id = 817
  AND review_status = 'flagged_for_review' AND review_reason = 'excluded_kinetic_casualty_or_damage';
-- air_violation_id=818 reason=excluded_kinetic_casualty_or_damage
UPDATE raw_messages rm
SET status = 'pending'::message_status,
    match_result = NULL,
    error_message = NULL, processing_claim_stage = NULL,
    processing_claimed_at = NULL, processing_claimed_by = NULL
WHERE rm.id = (SELECT raw_message_id FROM air_violations WHERE id = 818)
  AND rm.status NOT IN ('materialized'::message_status, 'duplicate'::message_status)
  AND NOT EXISTS (SELECT 1 FROM incidents i
                  WHERE i.raw_message_id = rm.id AND i.is_deleted = false);
DELETE FROM air_violations WHERE id = 818
  AND review_status = 'flagged_for_review' AND review_reason = 'excluded_kinetic_casualty_or_damage';
-- air_violation_id=819 reason=excluded_kinetic_casualty_or_damage
UPDATE raw_messages rm
SET status = 'pending'::message_status,
    match_result = NULL,
    error_message = NULL, processing_claim_stage = NULL,
    processing_claimed_at = NULL, processing_claimed_by = NULL
WHERE rm.id = (SELECT raw_message_id FROM air_violations WHERE id = 819)
  AND rm.status NOT IN ('materialized'::message_status, 'duplicate'::message_status)
  AND NOT EXISTS (SELECT 1 FROM incidents i
                  WHERE i.raw_message_id = rm.id AND i.is_deleted = false);
DELETE FROM air_violations WHERE id = 819
  AND review_status = 'flagged_for_review' AND review_reason = 'excluded_kinetic_casualty_or_damage';
-- air_violation_id=820 reason=excluded_kinetic_casualty_or_damage
UPDATE raw_messages rm
SET status = 'pending'::message_status,
    match_result = NULL,
    error_message = NULL, processing_claim_stage = NULL,
    processing_claimed_at = NULL, processing_claimed_by = NULL
WHERE rm.id = (SELECT raw_message_id FROM air_violations WHERE id = 820)
  AND rm.status NOT IN ('materialized'::message_status, 'duplicate'::message_status)
  AND NOT EXISTS (SELECT 1 FROM incidents i
                  WHERE i.raw_message_id = rm.id AND i.is_deleted = false);
DELETE FROM air_violations WHERE id = 820
  AND review_status = 'flagged_for_review' AND review_reason = 'excluded_kinetic_casualty_or_damage';
-- air_violation_id=821 reason=excluded_kinetic_casualty_or_damage
UPDATE raw_messages rm
SET status = 'pending'::message_status,
    match_result = NULL,
    error_message = NULL, processing_claim_stage = NULL,
    processing_claimed_at = NULL, processing_claimed_by = NULL
WHERE rm.id = (SELECT raw_message_id FROM air_violations WHERE id = 821)
  AND rm.status NOT IN ('materialized'::message_status, 'duplicate'::message_status)
  AND NOT EXISTS (SELECT 1 FROM incidents i
                  WHERE i.raw_message_id = rm.id AND i.is_deleted = false);
DELETE FROM air_violations WHERE id = 821
  AND review_status = 'flagged_for_review' AND review_reason = 'excluded_kinetic_casualty_or_damage';
-- air_violation_id=822 reason=excluded_kinetic_casualty_or_damage
UPDATE raw_messages rm
SET status = 'pending'::message_status,
    match_result = NULL,
    error_message = NULL, processing_claim_stage = NULL,
    processing_claimed_at = NULL, processing_claimed_by = NULL
WHERE rm.id = (SELECT raw_message_id FROM air_violations WHERE id = 822)
  AND rm.status NOT IN ('materialized'::message_status, 'duplicate'::message_status)
  AND NOT EXISTS (SELECT 1 FROM incidents i
                  WHERE i.raw_message_id = rm.id AND i.is_deleted = false);
DELETE FROM air_violations WHERE id = 822
  AND review_status = 'flagged_for_review' AND review_reason = 'excluded_kinetic_casualty_or_damage';
-- air_violation_id=823 reason=excluded_kinetic_casualty_or_damage
UPDATE raw_messages rm
SET status = 'pending'::message_status,
    match_result = NULL,
    error_message = NULL, processing_claim_stage = NULL,
    processing_claimed_at = NULL, processing_claimed_by = NULL
WHERE rm.id = (SELECT raw_message_id FROM air_violations WHERE id = 823)
  AND rm.status NOT IN ('materialized'::message_status, 'duplicate'::message_status)
  AND NOT EXISTS (SELECT 1 FROM incidents i
                  WHERE i.raw_message_id = rm.id AND i.is_deleted = false);
DELETE FROM air_violations WHERE id = 823
  AND review_status = 'flagged_for_review' AND review_reason = 'excluded_kinetic_casualty_or_damage';
-- air_violation_id=824 reason=excluded_kinetic_casualty_or_damage
UPDATE raw_messages rm
SET status = 'pending'::message_status,
    match_result = NULL,
    error_message = NULL, processing_claim_stage = NULL,
    processing_claimed_at = NULL, processing_claimed_by = NULL
WHERE rm.id = (SELECT raw_message_id FROM air_violations WHERE id = 824)
  AND rm.status NOT IN ('materialized'::message_status, 'duplicate'::message_status)
  AND NOT EXISTS (SELECT 1 FROM incidents i
                  WHERE i.raw_message_id = rm.id AND i.is_deleted = false);
DELETE FROM air_violations WHERE id = 824
  AND review_status = 'flagged_for_review' AND review_reason = 'excluded_kinetic_casualty_or_damage';
-- air_violation_id=825 reason=excluded_kinetic_casualty_or_damage
UPDATE raw_messages rm
SET status = 'pending'::message_status,
    match_result = NULL,
    error_message = NULL, processing_claim_stage = NULL,
    processing_claimed_at = NULL, processing_claimed_by = NULL
WHERE rm.id = (SELECT raw_message_id FROM air_violations WHERE id = 825)
  AND rm.status NOT IN ('materialized'::message_status, 'duplicate'::message_status)
  AND NOT EXISTS (SELECT 1 FROM incidents i
                  WHERE i.raw_message_id = rm.id AND i.is_deleted = false);
DELETE FROM air_violations WHERE id = 825
  AND review_status = 'flagged_for_review' AND review_reason = 'excluded_kinetic_casualty_or_damage';
-- air_violation_id=826 reason=excluded_kinetic_casualty_or_damage
UPDATE raw_messages rm
SET status = 'pending'::message_status,
    match_result = NULL,
    error_message = NULL, processing_claim_stage = NULL,
    processing_claimed_at = NULL, processing_claimed_by = NULL
WHERE rm.id = (SELECT raw_message_id FROM air_violations WHERE id = 826)
  AND rm.status NOT IN ('materialized'::message_status, 'duplicate'::message_status)
  AND NOT EXISTS (SELECT 1 FROM incidents i
                  WHERE i.raw_message_id = rm.id AND i.is_deleted = false);
DELETE FROM air_violations WHERE id = 826
  AND review_status = 'flagged_for_review' AND review_reason = 'excluded_kinetic_casualty_or_damage';
-- air_violation_id=827 reason=excluded_kinetic_casualty_or_damage
UPDATE raw_messages rm
SET status = 'pending'::message_status,
    match_result = NULL,
    error_message = NULL, processing_claim_stage = NULL,
    processing_claimed_at = NULL, processing_claimed_by = NULL
WHERE rm.id = (SELECT raw_message_id FROM air_violations WHERE id = 827)
  AND rm.status NOT IN ('materialized'::message_status, 'duplicate'::message_status)
  AND NOT EXISTS (SELECT 1 FROM incidents i
                  WHERE i.raw_message_id = rm.id AND i.is_deleted = false);
DELETE FROM air_violations WHERE id = 827
  AND review_status = 'flagged_for_review' AND review_reason = 'excluded_kinetic_casualty_or_damage';
-- air_violation_id=828 reason=excluded_kinetic_casualty_or_damage
UPDATE raw_messages rm
SET status = 'pending'::message_status,
    match_result = NULL,
    error_message = NULL, processing_claim_stage = NULL,
    processing_claimed_at = NULL, processing_claimed_by = NULL
WHERE rm.id = (SELECT raw_message_id FROM air_violations WHERE id = 828)
  AND rm.status NOT IN ('materialized'::message_status, 'duplicate'::message_status)
  AND NOT EXISTS (SELECT 1 FROM incidents i
                  WHERE i.raw_message_id = rm.id AND i.is_deleted = false);
DELETE FROM air_violations WHERE id = 828
  AND review_status = 'flagged_for_review' AND review_reason = 'excluded_kinetic_casualty_or_damage';
-- air_violation_id=829 reason=excluded_kinetic_casualty_or_damage
UPDATE raw_messages rm
SET status = 'pending'::message_status,
    match_result = NULL,
    error_message = NULL, processing_claim_stage = NULL,
    processing_claimed_at = NULL, processing_claimed_by = NULL
WHERE rm.id = (SELECT raw_message_id FROM air_violations WHERE id = 829)
  AND rm.status NOT IN ('materialized'::message_status, 'duplicate'::message_status)
  AND NOT EXISTS (SELECT 1 FROM incidents i
                  WHERE i.raw_message_id = rm.id AND i.is_deleted = false);
DELETE FROM air_violations WHERE id = 829
  AND review_status = 'flagged_for_review' AND review_reason = 'excluded_kinetic_casualty_or_damage';
-- air_violation_id=830 reason=excluded_kinetic_casualty_or_damage
UPDATE raw_messages rm
SET status = 'pending'::message_status,
    match_result = NULL,
    error_message = NULL, processing_claim_stage = NULL,
    processing_claimed_at = NULL, processing_claimed_by = NULL
WHERE rm.id = (SELECT raw_message_id FROM air_violations WHERE id = 830)
  AND rm.status NOT IN ('materialized'::message_status, 'duplicate'::message_status)
  AND NOT EXISTS (SELECT 1 FROM incidents i
                  WHERE i.raw_message_id = rm.id AND i.is_deleted = false);
DELETE FROM air_violations WHERE id = 830
  AND review_status = 'flagged_for_review' AND review_reason = 'excluded_kinetic_casualty_or_damage';
-- air_violation_id=831 reason=excluded_kinetic_casualty_or_damage
UPDATE raw_messages rm
SET status = 'pending'::message_status,
    match_result = NULL,
    error_message = NULL, processing_claim_stage = NULL,
    processing_claimed_at = NULL, processing_claimed_by = NULL
WHERE rm.id = (SELECT raw_message_id FROM air_violations WHERE id = 831)
  AND rm.status NOT IN ('materialized'::message_status, 'duplicate'::message_status)
  AND NOT EXISTS (SELECT 1 FROM incidents i
                  WHERE i.raw_message_id = rm.id AND i.is_deleted = false);
DELETE FROM air_violations WHERE id = 831
  AND review_status = 'flagged_for_review' AND review_reason = 'excluded_kinetic_casualty_or_damage';
-- air_violation_id=832 reason=excluded_kinetic_casualty_or_damage
UPDATE raw_messages rm
SET status = 'pending'::message_status,
    match_result = NULL,
    error_message = NULL, processing_claim_stage = NULL,
    processing_claimed_at = NULL, processing_claimed_by = NULL
WHERE rm.id = (SELECT raw_message_id FROM air_violations WHERE id = 832)
  AND rm.status NOT IN ('materialized'::message_status, 'duplicate'::message_status)
  AND NOT EXISTS (SELECT 1 FROM incidents i
                  WHERE i.raw_message_id = rm.id AND i.is_deleted = false);
DELETE FROM air_violations WHERE id = 832
  AND review_status = 'flagged_for_review' AND review_reason = 'excluded_kinetic_casualty_or_damage';
-- air_violation_id=833 reason=excluded_kinetic_casualty_or_damage
UPDATE raw_messages rm
SET status = 'pending'::message_status,
    match_result = NULL,
    error_message = NULL, processing_claim_stage = NULL,
    processing_claimed_at = NULL, processing_claimed_by = NULL
WHERE rm.id = (SELECT raw_message_id FROM air_violations WHERE id = 833)
  AND rm.status NOT IN ('materialized'::message_status, 'duplicate'::message_status)
  AND NOT EXISTS (SELECT 1 FROM incidents i
                  WHERE i.raw_message_id = rm.id AND i.is_deleted = false);
DELETE FROM air_violations WHERE id = 833
  AND review_status = 'flagged_for_review' AND review_reason = 'excluded_kinetic_casualty_or_damage';
-- air_violation_id=834 reason=excluded_kinetic_casualty_or_damage
UPDATE raw_messages rm
SET status = 'pending'::message_status,
    match_result = NULL,
    error_message = NULL, processing_claim_stage = NULL,
    processing_claimed_at = NULL, processing_claimed_by = NULL
WHERE rm.id = (SELECT raw_message_id FROM air_violations WHERE id = 834)
  AND rm.status NOT IN ('materialized'::message_status, 'duplicate'::message_status)
  AND NOT EXISTS (SELECT 1 FROM incidents i
                  WHERE i.raw_message_id = rm.id AND i.is_deleted = false);
DELETE FROM air_violations WHERE id = 834
  AND review_status = 'flagged_for_review' AND review_reason = 'excluded_kinetic_casualty_or_damage';
-- air_violation_id=835 reason=excluded_kinetic_casualty_or_damage
UPDATE raw_messages rm
SET status = 'pending'::message_status,
    match_result = NULL,
    error_message = NULL, processing_claim_stage = NULL,
    processing_claimed_at = NULL, processing_claimed_by = NULL
WHERE rm.id = (SELECT raw_message_id FROM air_violations WHERE id = 835)
  AND rm.status NOT IN ('materialized'::message_status, 'duplicate'::message_status)
  AND NOT EXISTS (SELECT 1 FROM incidents i
                  WHERE i.raw_message_id = rm.id AND i.is_deleted = false);
DELETE FROM air_violations WHERE id = 835
  AND review_status = 'flagged_for_review' AND review_reason = 'excluded_kinetic_casualty_or_damage';
-- air_violation_id=836 reason=excluded_kinetic_casualty_or_damage
UPDATE raw_messages rm
SET status = 'pending'::message_status,
    match_result = NULL,
    error_message = NULL, processing_claim_stage = NULL,
    processing_claimed_at = NULL, processing_claimed_by = NULL
WHERE rm.id = (SELECT raw_message_id FROM air_violations WHERE id = 836)
  AND rm.status NOT IN ('materialized'::message_status, 'duplicate'::message_status)
  AND NOT EXISTS (SELECT 1 FROM incidents i
                  WHERE i.raw_message_id = rm.id AND i.is_deleted = false);
DELETE FROM air_violations WHERE id = 836
  AND review_status = 'flagged_for_review' AND review_reason = 'excluded_kinetic_casualty_or_damage';
-- air_violation_id=837 reason=excluded_kinetic_casualty_or_damage
UPDATE raw_messages rm
SET status = 'pending'::message_status,
    match_result = NULL,
    error_message = NULL, processing_claim_stage = NULL,
    processing_claimed_at = NULL, processing_claimed_by = NULL
WHERE rm.id = (SELECT raw_message_id FROM air_violations WHERE id = 837)
  AND rm.status NOT IN ('materialized'::message_status, 'duplicate'::message_status)
  AND NOT EXISTS (SELECT 1 FROM incidents i
                  WHERE i.raw_message_id = rm.id AND i.is_deleted = false);
DELETE FROM air_violations WHERE id = 837
  AND review_status = 'flagged_for_review' AND review_reason = 'excluded_kinetic_casualty_or_damage';
-- air_violation_id=838 reason=excluded_kinetic_casualty_or_damage
UPDATE raw_messages rm
SET status = 'pending'::message_status,
    match_result = NULL,
    error_message = NULL, processing_claim_stage = NULL,
    processing_claimed_at = NULL, processing_claimed_by = NULL
WHERE rm.id = (SELECT raw_message_id FROM air_violations WHERE id = 838)
  AND rm.status NOT IN ('materialized'::message_status, 'duplicate'::message_status)
  AND NOT EXISTS (SELECT 1 FROM incidents i
                  WHERE i.raw_message_id = rm.id AND i.is_deleted = false);
DELETE FROM air_violations WHERE id = 838
  AND review_status = 'flagged_for_review' AND review_reason = 'excluded_kinetic_casualty_or_damage';
-- air_violation_id=839 reason=excluded_kinetic_casualty_or_damage
UPDATE raw_messages rm
SET status = 'pending'::message_status,
    match_result = NULL,
    error_message = NULL, processing_claim_stage = NULL,
    processing_claimed_at = NULL, processing_claimed_by = NULL
WHERE rm.id = (SELECT raw_message_id FROM air_violations WHERE id = 839)
  AND rm.status NOT IN ('materialized'::message_status, 'duplicate'::message_status)
  AND NOT EXISTS (SELECT 1 FROM incidents i
                  WHERE i.raw_message_id = rm.id AND i.is_deleted = false);
DELETE FROM air_violations WHERE id = 839
  AND review_status = 'flagged_for_review' AND review_reason = 'excluded_kinetic_casualty_or_damage';
-- air_violation_id=840 reason=excluded_kinetic_casualty_or_damage
UPDATE raw_messages rm
SET status = 'pending'::message_status,
    match_result = NULL,
    error_message = NULL, processing_claim_stage = NULL,
    processing_claimed_at = NULL, processing_claimed_by = NULL
WHERE rm.id = (SELECT raw_message_id FROM air_violations WHERE id = 840)
  AND rm.status NOT IN ('materialized'::message_status, 'duplicate'::message_status)
  AND NOT EXISTS (SELECT 1 FROM incidents i
                  WHERE i.raw_message_id = rm.id AND i.is_deleted = false);
DELETE FROM air_violations WHERE id = 840
  AND review_status = 'flagged_for_review' AND review_reason = 'excluded_kinetic_casualty_or_damage';
-- air_violation_id=841 reason=excluded_kinetic_casualty_or_damage
UPDATE raw_messages rm
SET status = 'pending'::message_status,
    match_result = NULL,
    error_message = NULL, processing_claim_stage = NULL,
    processing_claimed_at = NULL, processing_claimed_by = NULL
WHERE rm.id = (SELECT raw_message_id FROM air_violations WHERE id = 841)
  AND rm.status NOT IN ('materialized'::message_status, 'duplicate'::message_status)
  AND NOT EXISTS (SELECT 1 FROM incidents i
                  WHERE i.raw_message_id = rm.id AND i.is_deleted = false);
DELETE FROM air_violations WHERE id = 841
  AND review_status = 'flagged_for_review' AND review_reason = 'excluded_kinetic_casualty_or_damage';
-- air_violation_id=842 reason=excluded_kinetic_casualty_or_damage
UPDATE raw_messages rm
SET status = 'pending'::message_status,
    match_result = NULL,
    error_message = NULL, processing_claim_stage = NULL,
    processing_claimed_at = NULL, processing_claimed_by = NULL
WHERE rm.id = (SELECT raw_message_id FROM air_violations WHERE id = 842)
  AND rm.status NOT IN ('materialized'::message_status, 'duplicate'::message_status)
  AND NOT EXISTS (SELECT 1 FROM incidents i
                  WHERE i.raw_message_id = rm.id AND i.is_deleted = false);
DELETE FROM air_violations WHERE id = 842
  AND review_status = 'flagged_for_review' AND review_reason = 'excluded_kinetic_casualty_or_damage';
-- air_violation_id=843 reason=excluded_kinetic_casualty_or_damage
UPDATE raw_messages rm
SET status = 'pending'::message_status,
    match_result = NULL,
    error_message = NULL, processing_claim_stage = NULL,
    processing_claimed_at = NULL, processing_claimed_by = NULL
WHERE rm.id = (SELECT raw_message_id FROM air_violations WHERE id = 843)
  AND rm.status NOT IN ('materialized'::message_status, 'duplicate'::message_status)
  AND NOT EXISTS (SELECT 1 FROM incidents i
                  WHERE i.raw_message_id = rm.id AND i.is_deleted = false);
DELETE FROM air_violations WHERE id = 843
  AND review_status = 'flagged_for_review' AND review_reason = 'excluded_kinetic_casualty_or_damage';
-- air_violation_id=844 reason=excluded_kinetic_casualty_or_damage
UPDATE raw_messages rm
SET status = 'pending'::message_status,
    match_result = NULL,
    error_message = NULL, processing_claim_stage = NULL,
    processing_claimed_at = NULL, processing_claimed_by = NULL
WHERE rm.id = (SELECT raw_message_id FROM air_violations WHERE id = 844)
  AND rm.status NOT IN ('materialized'::message_status, 'duplicate'::message_status)
  AND NOT EXISTS (SELECT 1 FROM incidents i
                  WHERE i.raw_message_id = rm.id AND i.is_deleted = false);
DELETE FROM air_violations WHERE id = 844
  AND review_status = 'flagged_for_review' AND review_reason = 'excluded_kinetic_casualty_or_damage';
-- air_violation_id=845 reason=excluded_kinetic_casualty_or_damage
UPDATE raw_messages rm
SET status = 'pending'::message_status,
    match_result = NULL,
    error_message = NULL, processing_claim_stage = NULL,
    processing_claimed_at = NULL, processing_claimed_by = NULL
WHERE rm.id = (SELECT raw_message_id FROM air_violations WHERE id = 845)
  AND rm.status NOT IN ('materialized'::message_status, 'duplicate'::message_status)
  AND NOT EXISTS (SELECT 1 FROM incidents i
                  WHERE i.raw_message_id = rm.id AND i.is_deleted = false);
DELETE FROM air_violations WHERE id = 845
  AND review_status = 'flagged_for_review' AND review_reason = 'excluded_kinetic_casualty_or_damage';
-- air_violation_id=846 reason=excluded_kinetic_casualty_or_damage
UPDATE raw_messages rm
SET status = 'pending'::message_status,
    match_result = NULL,
    error_message = NULL, processing_claim_stage = NULL,
    processing_claimed_at = NULL, processing_claimed_by = NULL
WHERE rm.id = (SELECT raw_message_id FROM air_violations WHERE id = 846)
  AND rm.status NOT IN ('materialized'::message_status, 'duplicate'::message_status)
  AND NOT EXISTS (SELECT 1 FROM incidents i
                  WHERE i.raw_message_id = rm.id AND i.is_deleted = false);
DELETE FROM air_violations WHERE id = 846
  AND review_status = 'flagged_for_review' AND review_reason = 'excluded_kinetic_casualty_or_damage';
-- air_violation_id=847 reason=excluded_kinetic_casualty_or_damage
UPDATE raw_messages rm
SET status = 'pending'::message_status,
    match_result = NULL,
    error_message = NULL, processing_claim_stage = NULL,
    processing_claimed_at = NULL, processing_claimed_by = NULL
WHERE rm.id = (SELECT raw_message_id FROM air_violations WHERE id = 847)
  AND rm.status NOT IN ('materialized'::message_status, 'duplicate'::message_status)
  AND NOT EXISTS (SELECT 1 FROM incidents i
                  WHERE i.raw_message_id = rm.id AND i.is_deleted = false);
DELETE FROM air_violations WHERE id = 847
  AND review_status = 'flagged_for_review' AND review_reason = 'excluded_kinetic_casualty_or_damage';
-- air_violation_id=848 reason=excluded_kinetic_casualty_or_damage
UPDATE raw_messages rm
SET status = 'pending'::message_status,
    match_result = NULL,
    error_message = NULL, processing_claim_stage = NULL,
    processing_claimed_at = NULL, processing_claimed_by = NULL
WHERE rm.id = (SELECT raw_message_id FROM air_violations WHERE id = 848)
  AND rm.status NOT IN ('materialized'::message_status, 'duplicate'::message_status)
  AND NOT EXISTS (SELECT 1 FROM incidents i
                  WHERE i.raw_message_id = rm.id AND i.is_deleted = false);
DELETE FROM air_violations WHERE id = 848
  AND review_status = 'flagged_for_review' AND review_reason = 'excluded_kinetic_casualty_or_damage';
-- air_violation_id=849 reason=excluded_kinetic_casualty_or_damage
UPDATE raw_messages rm
SET status = 'pending'::message_status,
    match_result = NULL,
    error_message = NULL, processing_claim_stage = NULL,
    processing_claimed_at = NULL, processing_claimed_by = NULL
WHERE rm.id = (SELECT raw_message_id FROM air_violations WHERE id = 849)
  AND rm.status NOT IN ('materialized'::message_status, 'duplicate'::message_status)
  AND NOT EXISTS (SELECT 1 FROM incidents i
                  WHERE i.raw_message_id = rm.id AND i.is_deleted = false);
DELETE FROM air_violations WHERE id = 849
  AND review_status = 'flagged_for_review' AND review_reason = 'excluded_kinetic_casualty_or_damage';
-- air_violation_id=851 reason=excluded_kinetic_casualty_or_damage
UPDATE raw_messages rm
SET status = 'pending'::message_status,
    match_result = NULL,
    error_message = NULL, processing_claim_stage = NULL,
    processing_claimed_at = NULL, processing_claimed_by = NULL
WHERE rm.id = (SELECT raw_message_id FROM air_violations WHERE id = 851)
  AND rm.status NOT IN ('materialized'::message_status, 'duplicate'::message_status)
  AND NOT EXISTS (SELECT 1 FROM incidents i
                  WHERE i.raw_message_id = rm.id AND i.is_deleted = false);
DELETE FROM air_violations WHERE id = 851
  AND review_status = 'flagged_for_review' AND review_reason = 'excluded_kinetic_casualty_or_damage';
-- air_violation_id=852 reason=excluded_kinetic_casualty_or_damage
UPDATE raw_messages rm
SET status = 'pending'::message_status,
    match_result = NULL,
    error_message = NULL, processing_claim_stage = NULL,
    processing_claimed_at = NULL, processing_claimed_by = NULL
WHERE rm.id = (SELECT raw_message_id FROM air_violations WHERE id = 852)
  AND rm.status NOT IN ('materialized'::message_status, 'duplicate'::message_status)
  AND NOT EXISTS (SELECT 1 FROM incidents i
                  WHERE i.raw_message_id = rm.id AND i.is_deleted = false);
DELETE FROM air_violations WHERE id = 852
  AND review_status = 'flagged_for_review' AND review_reason = 'excluded_kinetic_casualty_or_damage';
-- air_violation_id=853 reason=excluded_kinetic_casualty_or_damage
UPDATE raw_messages rm
SET status = 'pending'::message_status,
    match_result = NULL,
    error_message = NULL, processing_claim_stage = NULL,
    processing_claimed_at = NULL, processing_claimed_by = NULL
WHERE rm.id = (SELECT raw_message_id FROM air_violations WHERE id = 853)
  AND rm.status NOT IN ('materialized'::message_status, 'duplicate'::message_status)
  AND NOT EXISTS (SELECT 1 FROM incidents i
                  WHERE i.raw_message_id = rm.id AND i.is_deleted = false);
DELETE FROM air_violations WHERE id = 853
  AND review_status = 'flagged_for_review' AND review_reason = 'excluded_kinetic_casualty_or_damage';
-- air_violation_id=854 reason=excluded_kinetic_casualty_or_damage
UPDATE raw_messages rm
SET status = 'pending'::message_status,
    match_result = NULL,
    error_message = NULL, processing_claim_stage = NULL,
    processing_claimed_at = NULL, processing_claimed_by = NULL
WHERE rm.id = (SELECT raw_message_id FROM air_violations WHERE id = 854)
  AND rm.status NOT IN ('materialized'::message_status, 'duplicate'::message_status)
  AND NOT EXISTS (SELECT 1 FROM incidents i
                  WHERE i.raw_message_id = rm.id AND i.is_deleted = false);
DELETE FROM air_violations WHERE id = 854
  AND review_status = 'flagged_for_review' AND review_reason = 'excluded_kinetic_casualty_or_damage';
-- air_violation_id=855 reason=excluded_kinetic_casualty_or_damage
UPDATE raw_messages rm
SET status = 'pending'::message_status,
    match_result = NULL,
    error_message = NULL, processing_claim_stage = NULL,
    processing_claimed_at = NULL, processing_claimed_by = NULL
WHERE rm.id = (SELECT raw_message_id FROM air_violations WHERE id = 855)
  AND rm.status NOT IN ('materialized'::message_status, 'duplicate'::message_status)
  AND NOT EXISTS (SELECT 1 FROM incidents i
                  WHERE i.raw_message_id = rm.id AND i.is_deleted = false);
DELETE FROM air_violations WHERE id = 855
  AND review_status = 'flagged_for_review' AND review_reason = 'excluded_kinetic_casualty_or_damage';
-- air_violation_id=856 reason=excluded_kinetic_casualty_or_damage
UPDATE raw_messages rm
SET status = 'pending'::message_status,
    match_result = NULL,
    error_message = NULL, processing_claim_stage = NULL,
    processing_claimed_at = NULL, processing_claimed_by = NULL
WHERE rm.id = (SELECT raw_message_id FROM air_violations WHERE id = 856)
  AND rm.status NOT IN ('materialized'::message_status, 'duplicate'::message_status)
  AND NOT EXISTS (SELECT 1 FROM incidents i
                  WHERE i.raw_message_id = rm.id AND i.is_deleted = false);
DELETE FROM air_violations WHERE id = 856
  AND review_status = 'flagged_for_review' AND review_reason = 'excluded_kinetic_casualty_or_damage';
-- air_violation_id=857 reason=excluded_kinetic_casualty_or_damage
UPDATE raw_messages rm
SET status = 'pending'::message_status,
    match_result = NULL,
    error_message = NULL, processing_claim_stage = NULL,
    processing_claimed_at = NULL, processing_claimed_by = NULL
WHERE rm.id = (SELECT raw_message_id FROM air_violations WHERE id = 857)
  AND rm.status NOT IN ('materialized'::message_status, 'duplicate'::message_status)
  AND NOT EXISTS (SELECT 1 FROM incidents i
                  WHERE i.raw_message_id = rm.id AND i.is_deleted = false);
DELETE FROM air_violations WHERE id = 857
  AND review_status = 'flagged_for_review' AND review_reason = 'excluded_kinetic_casualty_or_damage';
-- air_violation_id=858 reason=excluded_kinetic_casualty_or_damage
UPDATE raw_messages rm
SET status = 'pending'::message_status,
    match_result = NULL,
    error_message = NULL, processing_claim_stage = NULL,
    processing_claimed_at = NULL, processing_claimed_by = NULL
WHERE rm.id = (SELECT raw_message_id FROM air_violations WHERE id = 858)
  AND rm.status NOT IN ('materialized'::message_status, 'duplicate'::message_status)
  AND NOT EXISTS (SELECT 1 FROM incidents i
                  WHERE i.raw_message_id = rm.id AND i.is_deleted = false);
DELETE FROM air_violations WHERE id = 858
  AND review_status = 'flagged_for_review' AND review_reason = 'excluded_kinetic_casualty_or_damage';
-- air_violation_id=859 reason=excluded_kinetic_casualty_or_damage
UPDATE raw_messages rm
SET status = 'pending'::message_status,
    match_result = NULL,
    error_message = NULL, processing_claim_stage = NULL,
    processing_claimed_at = NULL, processing_claimed_by = NULL
WHERE rm.id = (SELECT raw_message_id FROM air_violations WHERE id = 859)
  AND rm.status NOT IN ('materialized'::message_status, 'duplicate'::message_status)
  AND NOT EXISTS (SELECT 1 FROM incidents i
                  WHERE i.raw_message_id = rm.id AND i.is_deleted = false);
DELETE FROM air_violations WHERE id = 859
  AND review_status = 'flagged_for_review' AND review_reason = 'excluded_kinetic_casualty_or_damage';
-- air_violation_id=860 reason=excluded_kinetic_casualty_or_damage
UPDATE raw_messages rm
SET status = 'pending'::message_status,
    match_result = NULL,
    error_message = NULL, processing_claim_stage = NULL,
    processing_claimed_at = NULL, processing_claimed_by = NULL
WHERE rm.id = (SELECT raw_message_id FROM air_violations WHERE id = 860)
  AND rm.status NOT IN ('materialized'::message_status, 'duplicate'::message_status)
  AND NOT EXISTS (SELECT 1 FROM incidents i
                  WHERE i.raw_message_id = rm.id AND i.is_deleted = false);
DELETE FROM air_violations WHERE id = 860
  AND review_status = 'flagged_for_review' AND review_reason = 'excluded_kinetic_casualty_or_damage';
-- air_violation_id=861 reason=excluded_kinetic_casualty_or_damage
UPDATE raw_messages rm
SET status = 'pending'::message_status,
    match_result = NULL,
    error_message = NULL, processing_claim_stage = NULL,
    processing_claimed_at = NULL, processing_claimed_by = NULL
WHERE rm.id = (SELECT raw_message_id FROM air_violations WHERE id = 861)
  AND rm.status NOT IN ('materialized'::message_status, 'duplicate'::message_status)
  AND NOT EXISTS (SELECT 1 FROM incidents i
                  WHERE i.raw_message_id = rm.id AND i.is_deleted = false);
DELETE FROM air_violations WHERE id = 861
  AND review_status = 'flagged_for_review' AND review_reason = 'excluded_kinetic_casualty_or_damage';
-- air_violation_id=862 reason=excluded_kinetic_casualty_or_damage
UPDATE raw_messages rm
SET status = 'pending'::message_status,
    match_result = NULL,
    error_message = NULL, processing_claim_stage = NULL,
    processing_claimed_at = NULL, processing_claimed_by = NULL
WHERE rm.id = (SELECT raw_message_id FROM air_violations WHERE id = 862)
  AND rm.status NOT IN ('materialized'::message_status, 'duplicate'::message_status)
  AND NOT EXISTS (SELECT 1 FROM incidents i
                  WHERE i.raw_message_id = rm.id AND i.is_deleted = false);
DELETE FROM air_violations WHERE id = 862
  AND review_status = 'flagged_for_review' AND review_reason = 'excluded_kinetic_casualty_or_damage';
-- air_violation_id=863 reason=excluded_kinetic_casualty_or_damage
UPDATE raw_messages rm
SET status = 'pending'::message_status,
    match_result = NULL,
    error_message = NULL, processing_claim_stage = NULL,
    processing_claimed_at = NULL, processing_claimed_by = NULL
WHERE rm.id = (SELECT raw_message_id FROM air_violations WHERE id = 863)
  AND rm.status NOT IN ('materialized'::message_status, 'duplicate'::message_status)
  AND NOT EXISTS (SELECT 1 FROM incidents i
                  WHERE i.raw_message_id = rm.id AND i.is_deleted = false);
DELETE FROM air_violations WHERE id = 863
  AND review_status = 'flagged_for_review' AND review_reason = 'excluded_kinetic_casualty_or_damage';
-- air_violation_id=864 reason=excluded_kinetic_casualty_or_damage
UPDATE raw_messages rm
SET status = 'pending'::message_status,
    match_result = NULL,
    error_message = NULL, processing_claim_stage = NULL,
    processing_claimed_at = NULL, processing_claimed_by = NULL
WHERE rm.id = (SELECT raw_message_id FROM air_violations WHERE id = 864)
  AND rm.status NOT IN ('materialized'::message_status, 'duplicate'::message_status)
  AND NOT EXISTS (SELECT 1 FROM incidents i
                  WHERE i.raw_message_id = rm.id AND i.is_deleted = false);
DELETE FROM air_violations WHERE id = 864
  AND review_status = 'flagged_for_review' AND review_reason = 'excluded_kinetic_casualty_or_damage';
-- air_violation_id=865 reason=excluded_kinetic_casualty_or_damage
UPDATE raw_messages rm
SET status = 'pending'::message_status,
    match_result = NULL,
    error_message = NULL, processing_claim_stage = NULL,
    processing_claimed_at = NULL, processing_claimed_by = NULL
WHERE rm.id = (SELECT raw_message_id FROM air_violations WHERE id = 865)
  AND rm.status NOT IN ('materialized'::message_status, 'duplicate'::message_status)
  AND NOT EXISTS (SELECT 1 FROM incidents i
                  WHERE i.raw_message_id = rm.id AND i.is_deleted = false);
DELETE FROM air_violations WHERE id = 865
  AND review_status = 'flagged_for_review' AND review_reason = 'excluded_kinetic_casualty_or_damage';
-- air_violation_id=866 reason=excluded_kinetic_casualty_or_damage
UPDATE raw_messages rm
SET status = 'pending'::message_status,
    match_result = NULL,
    error_message = NULL, processing_claim_stage = NULL,
    processing_claimed_at = NULL, processing_claimed_by = NULL
WHERE rm.id = (SELECT raw_message_id FROM air_violations WHERE id = 866)
  AND rm.status NOT IN ('materialized'::message_status, 'duplicate'::message_status)
  AND NOT EXISTS (SELECT 1 FROM incidents i
                  WHERE i.raw_message_id = rm.id AND i.is_deleted = false);
DELETE FROM air_violations WHERE id = 866
  AND review_status = 'flagged_for_review' AND review_reason = 'excluded_kinetic_casualty_or_damage';
-- air_violation_id=867 reason=excluded_kinetic_casualty_or_damage
UPDATE raw_messages rm
SET status = 'pending'::message_status,
    match_result = NULL,
    error_message = NULL, processing_claim_stage = NULL,
    processing_claimed_at = NULL, processing_claimed_by = NULL
WHERE rm.id = (SELECT raw_message_id FROM air_violations WHERE id = 867)
  AND rm.status NOT IN ('materialized'::message_status, 'duplicate'::message_status)
  AND NOT EXISTS (SELECT 1 FROM incidents i
                  WHERE i.raw_message_id = rm.id AND i.is_deleted = false);
DELETE FROM air_violations WHERE id = 867
  AND review_status = 'flagged_for_review' AND review_reason = 'excluded_kinetic_casualty_or_damage';
-- air_violation_id=868 reason=excluded_kinetic_casualty_or_damage
UPDATE raw_messages rm
SET status = 'pending'::message_status,
    match_result = NULL,
    error_message = NULL, processing_claim_stage = NULL,
    processing_claimed_at = NULL, processing_claimed_by = NULL
WHERE rm.id = (SELECT raw_message_id FROM air_violations WHERE id = 868)
  AND rm.status NOT IN ('materialized'::message_status, 'duplicate'::message_status)
  AND NOT EXISTS (SELECT 1 FROM incidents i
                  WHERE i.raw_message_id = rm.id AND i.is_deleted = false);
DELETE FROM air_violations WHERE id = 868
  AND review_status = 'flagged_for_review' AND review_reason = 'excluded_kinetic_casualty_or_damage';
-- air_violation_id=869 reason=excluded_kinetic_casualty_or_damage
UPDATE raw_messages rm
SET status = 'pending'::message_status,
    match_result = NULL,
    error_message = NULL, processing_claim_stage = NULL,
    processing_claimed_at = NULL, processing_claimed_by = NULL
WHERE rm.id = (SELECT raw_message_id FROM air_violations WHERE id = 869)
  AND rm.status NOT IN ('materialized'::message_status, 'duplicate'::message_status)
  AND NOT EXISTS (SELECT 1 FROM incidents i
                  WHERE i.raw_message_id = rm.id AND i.is_deleted = false);
DELETE FROM air_violations WHERE id = 869
  AND review_status = 'flagged_for_review' AND review_reason = 'excluded_kinetic_casualty_or_damage';
-- air_violation_id=870 reason=excluded_kinetic_casualty_or_damage
UPDATE raw_messages rm
SET status = 'pending'::message_status,
    match_result = NULL,
    error_message = NULL, processing_claim_stage = NULL,
    processing_claimed_at = NULL, processing_claimed_by = NULL
WHERE rm.id = (SELECT raw_message_id FROM air_violations WHERE id = 870)
  AND rm.status NOT IN ('materialized'::message_status, 'duplicate'::message_status)
  AND NOT EXISTS (SELECT 1 FROM incidents i
                  WHERE i.raw_message_id = rm.id AND i.is_deleted = false);
DELETE FROM air_violations WHERE id = 870
  AND review_status = 'flagged_for_review' AND review_reason = 'excluded_kinetic_casualty_or_damage';
-- air_violation_id=871 reason=excluded_kinetic_casualty_or_damage
UPDATE raw_messages rm
SET status = 'pending'::message_status,
    match_result = NULL,
    error_message = NULL, processing_claim_stage = NULL,
    processing_claimed_at = NULL, processing_claimed_by = NULL
WHERE rm.id = (SELECT raw_message_id FROM air_violations WHERE id = 871)
  AND rm.status NOT IN ('materialized'::message_status, 'duplicate'::message_status)
  AND NOT EXISTS (SELECT 1 FROM incidents i
                  WHERE i.raw_message_id = rm.id AND i.is_deleted = false);
DELETE FROM air_violations WHERE id = 871
  AND review_status = 'flagged_for_review' AND review_reason = 'excluded_kinetic_casualty_or_damage';
-- air_violation_id=872 reason=excluded_kinetic_casualty_or_damage
UPDATE raw_messages rm
SET status = 'pending'::message_status,
    match_result = NULL,
    error_message = NULL, processing_claim_stage = NULL,
    processing_claimed_at = NULL, processing_claimed_by = NULL
WHERE rm.id = (SELECT raw_message_id FROM air_violations WHERE id = 872)
  AND rm.status NOT IN ('materialized'::message_status, 'duplicate'::message_status)
  AND NOT EXISTS (SELECT 1 FROM incidents i
                  WHERE i.raw_message_id = rm.id AND i.is_deleted = false);
DELETE FROM air_violations WHERE id = 872
  AND review_status = 'flagged_for_review' AND review_reason = 'excluded_kinetic_casualty_or_damage';
-- air_violation_id=873 reason=excluded_kinetic_casualty_or_damage
UPDATE raw_messages rm
SET status = 'pending'::message_status,
    match_result = NULL,
    error_message = NULL, processing_claim_stage = NULL,
    processing_claimed_at = NULL, processing_claimed_by = NULL
WHERE rm.id = (SELECT raw_message_id FROM air_violations WHERE id = 873)
  AND rm.status NOT IN ('materialized'::message_status, 'duplicate'::message_status)
  AND NOT EXISTS (SELECT 1 FROM incidents i
                  WHERE i.raw_message_id = rm.id AND i.is_deleted = false);
DELETE FROM air_violations WHERE id = 873
  AND review_status = 'flagged_for_review' AND review_reason = 'excluded_kinetic_casualty_or_damage';
-- air_violation_id=874 reason=excluded_kinetic_casualty_or_damage
UPDATE raw_messages rm
SET status = 'pending'::message_status,
    match_result = NULL,
    error_message = NULL, processing_claim_stage = NULL,
    processing_claimed_at = NULL, processing_claimed_by = NULL
WHERE rm.id = (SELECT raw_message_id FROM air_violations WHERE id = 874)
  AND rm.status NOT IN ('materialized'::message_status, 'duplicate'::message_status)
  AND NOT EXISTS (SELECT 1 FROM incidents i
                  WHERE i.raw_message_id = rm.id AND i.is_deleted = false);
DELETE FROM air_violations WHERE id = 874
  AND review_status = 'flagged_for_review' AND review_reason = 'excluded_kinetic_casualty_or_damage';
-- air_violation_id=875 reason=excluded_kinetic_casualty_or_damage
UPDATE raw_messages rm
SET status = 'pending'::message_status,
    match_result = NULL,
    error_message = NULL, processing_claim_stage = NULL,
    processing_claimed_at = NULL, processing_claimed_by = NULL
WHERE rm.id = (SELECT raw_message_id FROM air_violations WHERE id = 875)
  AND rm.status NOT IN ('materialized'::message_status, 'duplicate'::message_status)
  AND NOT EXISTS (SELECT 1 FROM incidents i
                  WHERE i.raw_message_id = rm.id AND i.is_deleted = false);
DELETE FROM air_violations WHERE id = 875
  AND review_status = 'flagged_for_review' AND review_reason = 'excluded_kinetic_casualty_or_damage';
-- air_violation_id=876 reason=excluded_kinetic_casualty_or_damage
UPDATE raw_messages rm
SET status = 'pending'::message_status,
    match_result = NULL,
    error_message = NULL, processing_claim_stage = NULL,
    processing_claimed_at = NULL, processing_claimed_by = NULL
WHERE rm.id = (SELECT raw_message_id FROM air_violations WHERE id = 876)
  AND rm.status NOT IN ('materialized'::message_status, 'duplicate'::message_status)
  AND NOT EXISTS (SELECT 1 FROM incidents i
                  WHERE i.raw_message_id = rm.id AND i.is_deleted = false);
DELETE FROM air_violations WHERE id = 876
  AND review_status = 'flagged_for_review' AND review_reason = 'excluded_kinetic_casualty_or_damage';
-- air_violation_id=877 reason=excluded_kinetic_casualty_or_damage
UPDATE raw_messages rm
SET status = 'pending'::message_status,
    match_result = NULL,
    error_message = NULL, processing_claim_stage = NULL,
    processing_claimed_at = NULL, processing_claimed_by = NULL
WHERE rm.id = (SELECT raw_message_id FROM air_violations WHERE id = 877)
  AND rm.status NOT IN ('materialized'::message_status, 'duplicate'::message_status)
  AND NOT EXISTS (SELECT 1 FROM incidents i
                  WHERE i.raw_message_id = rm.id AND i.is_deleted = false);
DELETE FROM air_violations WHERE id = 877
  AND review_status = 'flagged_for_review' AND review_reason = 'excluded_kinetic_casualty_or_damage';
-- air_violation_id=879 reason=excluded_kinetic_casualty_or_damage
UPDATE raw_messages rm
SET status = 'pending'::message_status,
    match_result = NULL,
    error_message = NULL, processing_claim_stage = NULL,
    processing_claimed_at = NULL, processing_claimed_by = NULL
WHERE rm.id = (SELECT raw_message_id FROM air_violations WHERE id = 879)
  AND rm.status NOT IN ('materialized'::message_status, 'duplicate'::message_status)
  AND NOT EXISTS (SELECT 1 FROM incidents i
                  WHERE i.raw_message_id = rm.id AND i.is_deleted = false);
DELETE FROM air_violations WHERE id = 879
  AND review_status = 'flagged_for_review' AND review_reason = 'excluded_kinetic_casualty_or_damage';
-- air_violation_id=880 reason=excluded_kinetic_casualty_or_damage
UPDATE raw_messages rm
SET status = 'pending'::message_status,
    match_result = NULL,
    error_message = NULL, processing_claim_stage = NULL,
    processing_claimed_at = NULL, processing_claimed_by = NULL
WHERE rm.id = (SELECT raw_message_id FROM air_violations WHERE id = 880)
  AND rm.status NOT IN ('materialized'::message_status, 'duplicate'::message_status)
  AND NOT EXISTS (SELECT 1 FROM incidents i
                  WHERE i.raw_message_id = rm.id AND i.is_deleted = false);
DELETE FROM air_violations WHERE id = 880
  AND review_status = 'flagged_for_review' AND review_reason = 'excluded_kinetic_casualty_or_damage';
-- air_violation_id=881 reason=excluded_kinetic_casualty_or_damage
UPDATE raw_messages rm
SET status = 'pending'::message_status,
    match_result = NULL,
    error_message = NULL, processing_claim_stage = NULL,
    processing_claimed_at = NULL, processing_claimed_by = NULL
WHERE rm.id = (SELECT raw_message_id FROM air_violations WHERE id = 881)
  AND rm.status NOT IN ('materialized'::message_status, 'duplicate'::message_status)
  AND NOT EXISTS (SELECT 1 FROM incidents i
                  WHERE i.raw_message_id = rm.id AND i.is_deleted = false);
DELETE FROM air_violations WHERE id = 881
  AND review_status = 'flagged_for_review' AND review_reason = 'excluded_kinetic_casualty_or_damage';
-- air_violation_id=882 reason=excluded_kinetic_casualty_or_damage
UPDATE raw_messages rm
SET status = 'pending'::message_status,
    match_result = NULL,
    error_message = NULL, processing_claim_stage = NULL,
    processing_claimed_at = NULL, processing_claimed_by = NULL
WHERE rm.id = (SELECT raw_message_id FROM air_violations WHERE id = 882)
  AND rm.status NOT IN ('materialized'::message_status, 'duplicate'::message_status)
  AND NOT EXISTS (SELECT 1 FROM incidents i
                  WHERE i.raw_message_id = rm.id AND i.is_deleted = false);
DELETE FROM air_violations WHERE id = 882
  AND review_status = 'flagged_for_review' AND review_reason = 'excluded_kinetic_casualty_or_damage';
-- air_violation_id=883 reason=excluded_kinetic_casualty_or_damage
UPDATE raw_messages rm
SET status = 'pending'::message_status,
    match_result = NULL,
    error_message = NULL, processing_claim_stage = NULL,
    processing_claimed_at = NULL, processing_claimed_by = NULL
WHERE rm.id = (SELECT raw_message_id FROM air_violations WHERE id = 883)
  AND rm.status NOT IN ('materialized'::message_status, 'duplicate'::message_status)
  AND NOT EXISTS (SELECT 1 FROM incidents i
                  WHERE i.raw_message_id = rm.id AND i.is_deleted = false);
DELETE FROM air_violations WHERE id = 883
  AND review_status = 'flagged_for_review' AND review_reason = 'excluded_kinetic_casualty_or_damage';
-- air_violation_id=884 reason=excluded_kinetic_casualty_or_damage
UPDATE raw_messages rm
SET status = 'pending'::message_status,
    match_result = NULL,
    error_message = NULL, processing_claim_stage = NULL,
    processing_claimed_at = NULL, processing_claimed_by = NULL
WHERE rm.id = (SELECT raw_message_id FROM air_violations WHERE id = 884)
  AND rm.status NOT IN ('materialized'::message_status, 'duplicate'::message_status)
  AND NOT EXISTS (SELECT 1 FROM incidents i
                  WHERE i.raw_message_id = rm.id AND i.is_deleted = false);
DELETE FROM air_violations WHERE id = 884
  AND review_status = 'flagged_for_review' AND review_reason = 'excluded_kinetic_casualty_or_damage';
-- air_violation_id=885 reason=excluded_kinetic_casualty_or_damage
UPDATE raw_messages rm
SET status = 'pending'::message_status,
    match_result = NULL,
    error_message = NULL, processing_claim_stage = NULL,
    processing_claimed_at = NULL, processing_claimed_by = NULL
WHERE rm.id = (SELECT raw_message_id FROM air_violations WHERE id = 885)
  AND rm.status NOT IN ('materialized'::message_status, 'duplicate'::message_status)
  AND NOT EXISTS (SELECT 1 FROM incidents i
                  WHERE i.raw_message_id = rm.id AND i.is_deleted = false);
DELETE FROM air_violations WHERE id = 885
  AND review_status = 'flagged_for_review' AND review_reason = 'excluded_kinetic_casualty_or_damage';
-- air_violation_id=886 reason=excluded_kinetic_casualty_or_damage
UPDATE raw_messages rm
SET status = 'pending'::message_status,
    match_result = NULL,
    error_message = NULL, processing_claim_stage = NULL,
    processing_claimed_at = NULL, processing_claimed_by = NULL
WHERE rm.id = (SELECT raw_message_id FROM air_violations WHERE id = 886)
  AND rm.status NOT IN ('materialized'::message_status, 'duplicate'::message_status)
  AND NOT EXISTS (SELECT 1 FROM incidents i
                  WHERE i.raw_message_id = rm.id AND i.is_deleted = false);
DELETE FROM air_violations WHERE id = 886
  AND review_status = 'flagged_for_review' AND review_reason = 'excluded_kinetic_casualty_or_damage';
-- air_violation_id=887 reason=excluded_kinetic_casualty_or_damage
UPDATE raw_messages rm
SET status = 'pending'::message_status,
    match_result = NULL,
    error_message = NULL, processing_claim_stage = NULL,
    processing_claimed_at = NULL, processing_claimed_by = NULL
WHERE rm.id = (SELECT raw_message_id FROM air_violations WHERE id = 887)
  AND rm.status NOT IN ('materialized'::message_status, 'duplicate'::message_status)
  AND NOT EXISTS (SELECT 1 FROM incidents i
                  WHERE i.raw_message_id = rm.id AND i.is_deleted = false);
DELETE FROM air_violations WHERE id = 887
  AND review_status = 'flagged_for_review' AND review_reason = 'excluded_kinetic_casualty_or_damage';
-- air_violation_id=888 reason=excluded_kinetic_casualty_or_damage
UPDATE raw_messages rm
SET status = 'pending'::message_status,
    match_result = NULL,
    error_message = NULL, processing_claim_stage = NULL,
    processing_claimed_at = NULL, processing_claimed_by = NULL
WHERE rm.id = (SELECT raw_message_id FROM air_violations WHERE id = 888)
  AND rm.status NOT IN ('materialized'::message_status, 'duplicate'::message_status)
  AND NOT EXISTS (SELECT 1 FROM incidents i
                  WHERE i.raw_message_id = rm.id AND i.is_deleted = false);
DELETE FROM air_violations WHERE id = 888
  AND review_status = 'flagged_for_review' AND review_reason = 'excluded_kinetic_casualty_or_damage';
-- air_violation_id=889 reason=excluded_kinetic_casualty_or_damage
UPDATE raw_messages rm
SET status = 'pending'::message_status,
    match_result = NULL,
    error_message = NULL, processing_claim_stage = NULL,
    processing_claimed_at = NULL, processing_claimed_by = NULL
WHERE rm.id = (SELECT raw_message_id FROM air_violations WHERE id = 889)
  AND rm.status NOT IN ('materialized'::message_status, 'duplicate'::message_status)
  AND NOT EXISTS (SELECT 1 FROM incidents i
                  WHERE i.raw_message_id = rm.id AND i.is_deleted = false);
DELETE FROM air_violations WHERE id = 889
  AND review_status = 'flagged_for_review' AND review_reason = 'excluded_kinetic_casualty_or_damage';
-- air_violation_id=890 reason=excluded_kinetic_casualty_or_damage
UPDATE raw_messages rm
SET status = 'pending'::message_status,
    match_result = NULL,
    error_message = NULL, processing_claim_stage = NULL,
    processing_claimed_at = NULL, processing_claimed_by = NULL
WHERE rm.id = (SELECT raw_message_id FROM air_violations WHERE id = 890)
  AND rm.status NOT IN ('materialized'::message_status, 'duplicate'::message_status)
  AND NOT EXISTS (SELECT 1 FROM incidents i
                  WHERE i.raw_message_id = rm.id AND i.is_deleted = false);
DELETE FROM air_violations WHERE id = 890
  AND review_status = 'flagged_for_review' AND review_reason = 'excluded_kinetic_casualty_or_damage';
-- air_violation_id=891 reason=excluded_kinetic_casualty_or_damage
UPDATE raw_messages rm
SET status = 'pending'::message_status,
    match_result = NULL,
    error_message = NULL, processing_claim_stage = NULL,
    processing_claimed_at = NULL, processing_claimed_by = NULL
WHERE rm.id = (SELECT raw_message_id FROM air_violations WHERE id = 891)
  AND rm.status NOT IN ('materialized'::message_status, 'duplicate'::message_status)
  AND NOT EXISTS (SELECT 1 FROM incidents i
                  WHERE i.raw_message_id = rm.id AND i.is_deleted = false);
DELETE FROM air_violations WHERE id = 891
  AND review_status = 'flagged_for_review' AND review_reason = 'excluded_kinetic_casualty_or_damage';
-- air_violation_id=892 reason=excluded_kinetic_casualty_or_damage
UPDATE raw_messages rm
SET status = 'pending'::message_status,
    match_result = NULL,
    error_message = NULL, processing_claim_stage = NULL,
    processing_claimed_at = NULL, processing_claimed_by = NULL
WHERE rm.id = (SELECT raw_message_id FROM air_violations WHERE id = 892)
  AND rm.status NOT IN ('materialized'::message_status, 'duplicate'::message_status)
  AND NOT EXISTS (SELECT 1 FROM incidents i
                  WHERE i.raw_message_id = rm.id AND i.is_deleted = false);
DELETE FROM air_violations WHERE id = 892
  AND review_status = 'flagged_for_review' AND review_reason = 'excluded_kinetic_casualty_or_damage';
-- air_violation_id=893 reason=excluded_kinetic_casualty_or_damage
UPDATE raw_messages rm
SET status = 'pending'::message_status,
    match_result = NULL,
    error_message = NULL, processing_claim_stage = NULL,
    processing_claimed_at = NULL, processing_claimed_by = NULL
WHERE rm.id = (SELECT raw_message_id FROM air_violations WHERE id = 893)
  AND rm.status NOT IN ('materialized'::message_status, 'duplicate'::message_status)
  AND NOT EXISTS (SELECT 1 FROM incidents i
                  WHERE i.raw_message_id = rm.id AND i.is_deleted = false);
DELETE FROM air_violations WHERE id = 893
  AND review_status = 'flagged_for_review' AND review_reason = 'excluded_kinetic_casualty_or_damage';
-- air_violation_id=894 reason=excluded_kinetic_casualty_or_damage
UPDATE raw_messages rm
SET status = 'pending'::message_status,
    match_result = NULL,
    error_message = NULL, processing_claim_stage = NULL,
    processing_claimed_at = NULL, processing_claimed_by = NULL
WHERE rm.id = (SELECT raw_message_id FROM air_violations WHERE id = 894)
  AND rm.status NOT IN ('materialized'::message_status, 'duplicate'::message_status)
  AND NOT EXISTS (SELECT 1 FROM incidents i
                  WHERE i.raw_message_id = rm.id AND i.is_deleted = false);
DELETE FROM air_violations WHERE id = 894
  AND review_status = 'flagged_for_review' AND review_reason = 'excluded_kinetic_casualty_or_damage';
-- air_violation_id=895 reason=excluded_kinetic_casualty_or_damage
UPDATE raw_messages rm
SET status = 'pending'::message_status,
    match_result = NULL,
    error_message = NULL, processing_claim_stage = NULL,
    processing_claimed_at = NULL, processing_claimed_by = NULL
WHERE rm.id = (SELECT raw_message_id FROM air_violations WHERE id = 895)
  AND rm.status NOT IN ('materialized'::message_status, 'duplicate'::message_status)
  AND NOT EXISTS (SELECT 1 FROM incidents i
                  WHERE i.raw_message_id = rm.id AND i.is_deleted = false);
DELETE FROM air_violations WHERE id = 895
  AND review_status = 'flagged_for_review' AND review_reason = 'excluded_kinetic_casualty_or_damage';
-- air_violation_id=896 reason=excluded_kinetic_casualty_or_damage
UPDATE raw_messages rm
SET status = 'pending'::message_status,
    match_result = NULL,
    error_message = NULL, processing_claim_stage = NULL,
    processing_claimed_at = NULL, processing_claimed_by = NULL
WHERE rm.id = (SELECT raw_message_id FROM air_violations WHERE id = 896)
  AND rm.status NOT IN ('materialized'::message_status, 'duplicate'::message_status)
  AND NOT EXISTS (SELECT 1 FROM incidents i
                  WHERE i.raw_message_id = rm.id AND i.is_deleted = false);
DELETE FROM air_violations WHERE id = 896
  AND review_status = 'flagged_for_review' AND review_reason = 'excluded_kinetic_casualty_or_damage';
-- air_violation_id=897 reason=excluded_kinetic_casualty_or_damage
UPDATE raw_messages rm
SET status = 'pending'::message_status,
    match_result = NULL,
    error_message = NULL, processing_claim_stage = NULL,
    processing_claimed_at = NULL, processing_claimed_by = NULL
WHERE rm.id = (SELECT raw_message_id FROM air_violations WHERE id = 897)
  AND rm.status NOT IN ('materialized'::message_status, 'duplicate'::message_status)
  AND NOT EXISTS (SELECT 1 FROM incidents i
                  WHERE i.raw_message_id = rm.id AND i.is_deleted = false);
DELETE FROM air_violations WHERE id = 897
  AND review_status = 'flagged_for_review' AND review_reason = 'excluded_kinetic_casualty_or_damage';
-- air_violation_id=898 reason=excluded_kinetic_casualty_or_damage
UPDATE raw_messages rm
SET status = 'pending'::message_status,
    match_result = NULL,
    error_message = NULL, processing_claim_stage = NULL,
    processing_claimed_at = NULL, processing_claimed_by = NULL
WHERE rm.id = (SELECT raw_message_id FROM air_violations WHERE id = 898)
  AND rm.status NOT IN ('materialized'::message_status, 'duplicate'::message_status)
  AND NOT EXISTS (SELECT 1 FROM incidents i
                  WHERE i.raw_message_id = rm.id AND i.is_deleted = false);
DELETE FROM air_violations WHERE id = 898
  AND review_status = 'flagged_for_review' AND review_reason = 'excluded_kinetic_casualty_or_damage';
-- air_violation_id=899 reason=excluded_kinetic_casualty_or_damage
UPDATE raw_messages rm
SET status = 'pending'::message_status,
    match_result = NULL,
    error_message = NULL, processing_claim_stage = NULL,
    processing_claimed_at = NULL, processing_claimed_by = NULL
WHERE rm.id = (SELECT raw_message_id FROM air_violations WHERE id = 899)
  AND rm.status NOT IN ('materialized'::message_status, 'duplicate'::message_status)
  AND NOT EXISTS (SELECT 1 FROM incidents i
                  WHERE i.raw_message_id = rm.id AND i.is_deleted = false);
DELETE FROM air_violations WHERE id = 899
  AND review_status = 'flagged_for_review' AND review_reason = 'excluded_kinetic_casualty_or_damage';
-- air_violation_id=900 reason=excluded_kinetic_casualty_or_damage
UPDATE raw_messages rm
SET status = 'pending'::message_status,
    match_result = NULL,
    error_message = NULL, processing_claim_stage = NULL,
    processing_claimed_at = NULL, processing_claimed_by = NULL
WHERE rm.id = (SELECT raw_message_id FROM air_violations WHERE id = 900)
  AND rm.status NOT IN ('materialized'::message_status, 'duplicate'::message_status)
  AND NOT EXISTS (SELECT 1 FROM incidents i
                  WHERE i.raw_message_id = rm.id AND i.is_deleted = false);
DELETE FROM air_violations WHERE id = 900
  AND review_status = 'flagged_for_review' AND review_reason = 'excluded_kinetic_casualty_or_damage';
-- air_violation_id=901 reason=excluded_kinetic_casualty_or_damage
UPDATE raw_messages rm
SET status = 'pending'::message_status,
    match_result = NULL,
    error_message = NULL, processing_claim_stage = NULL,
    processing_claimed_at = NULL, processing_claimed_by = NULL
WHERE rm.id = (SELECT raw_message_id FROM air_violations WHERE id = 901)
  AND rm.status NOT IN ('materialized'::message_status, 'duplicate'::message_status)
  AND NOT EXISTS (SELECT 1 FROM incidents i
                  WHERE i.raw_message_id = rm.id AND i.is_deleted = false);
DELETE FROM air_violations WHERE id = 901
  AND review_status = 'flagged_for_review' AND review_reason = 'excluded_kinetic_casualty_or_damage';
-- air_violation_id=902 reason=excluded_kinetic_casualty_or_damage
UPDATE raw_messages rm
SET status = 'pending'::message_status,
    match_result = NULL,
    error_message = NULL, processing_claim_stage = NULL,
    processing_claimed_at = NULL, processing_claimed_by = NULL
WHERE rm.id = (SELECT raw_message_id FROM air_violations WHERE id = 902)
  AND rm.status NOT IN ('materialized'::message_status, 'duplicate'::message_status)
  AND NOT EXISTS (SELECT 1 FROM incidents i
                  WHERE i.raw_message_id = rm.id AND i.is_deleted = false);
DELETE FROM air_violations WHERE id = 902
  AND review_status = 'flagged_for_review' AND review_reason = 'excluded_kinetic_casualty_or_damage';
-- air_violation_id=903 reason=excluded_kinetic_casualty_or_damage
UPDATE raw_messages rm
SET status = 'pending'::message_status,
    match_result = NULL,
    error_message = NULL, processing_claim_stage = NULL,
    processing_claimed_at = NULL, processing_claimed_by = NULL
WHERE rm.id = (SELECT raw_message_id FROM air_violations WHERE id = 903)
  AND rm.status NOT IN ('materialized'::message_status, 'duplicate'::message_status)
  AND NOT EXISTS (SELECT 1 FROM incidents i
                  WHERE i.raw_message_id = rm.id AND i.is_deleted = false);
DELETE FROM air_violations WHERE id = 903
  AND review_status = 'flagged_for_review' AND review_reason = 'excluded_kinetic_casualty_or_damage';
-- air_violation_id=904 reason=excluded_kinetic_casualty_or_damage
UPDATE raw_messages rm
SET status = 'pending'::message_status,
    match_result = NULL,
    error_message = NULL, processing_claim_stage = NULL,
    processing_claimed_at = NULL, processing_claimed_by = NULL
WHERE rm.id = (SELECT raw_message_id FROM air_violations WHERE id = 904)
  AND rm.status NOT IN ('materialized'::message_status, 'duplicate'::message_status)
  AND NOT EXISTS (SELECT 1 FROM incidents i
                  WHERE i.raw_message_id = rm.id AND i.is_deleted = false);
DELETE FROM air_violations WHERE id = 904
  AND review_status = 'flagged_for_review' AND review_reason = 'excluded_kinetic_casualty_or_damage';
-- air_violation_id=905 reason=excluded_kinetic_casualty_or_damage
UPDATE raw_messages rm
SET status = 'pending'::message_status,
    match_result = NULL,
    error_message = NULL, processing_claim_stage = NULL,
    processing_claimed_at = NULL, processing_claimed_by = NULL
WHERE rm.id = (SELECT raw_message_id FROM air_violations WHERE id = 905)
  AND rm.status NOT IN ('materialized'::message_status, 'duplicate'::message_status)
  AND NOT EXISTS (SELECT 1 FROM incidents i
                  WHERE i.raw_message_id = rm.id AND i.is_deleted = false);
DELETE FROM air_violations WHERE id = 905
  AND review_status = 'flagged_for_review' AND review_reason = 'excluded_kinetic_casualty_or_damage';
-- air_violation_id=906 reason=excluded_kinetic_casualty_or_damage
UPDATE raw_messages rm
SET status = 'pending'::message_status,
    match_result = NULL,
    error_message = NULL, processing_claim_stage = NULL,
    processing_claimed_at = NULL, processing_claimed_by = NULL
WHERE rm.id = (SELECT raw_message_id FROM air_violations WHERE id = 906)
  AND rm.status NOT IN ('materialized'::message_status, 'duplicate'::message_status)
  AND NOT EXISTS (SELECT 1 FROM incidents i
                  WHERE i.raw_message_id = rm.id AND i.is_deleted = false);
DELETE FROM air_violations WHERE id = 906
  AND review_status = 'flagged_for_review' AND review_reason = 'excluded_kinetic_casualty_or_damage';
-- air_violation_id=907 reason=excluded_kinetic_casualty_or_damage
UPDATE raw_messages rm
SET status = 'pending'::message_status,
    match_result = NULL,
    error_message = NULL, processing_claim_stage = NULL,
    processing_claimed_at = NULL, processing_claimed_by = NULL
WHERE rm.id = (SELECT raw_message_id FROM air_violations WHERE id = 907)
  AND rm.status NOT IN ('materialized'::message_status, 'duplicate'::message_status)
  AND NOT EXISTS (SELECT 1 FROM incidents i
                  WHERE i.raw_message_id = rm.id AND i.is_deleted = false);
DELETE FROM air_violations WHERE id = 907
  AND review_status = 'flagged_for_review' AND review_reason = 'excluded_kinetic_casualty_or_damage';
-- air_violation_id=908 reason=excluded_kinetic_casualty_or_damage
UPDATE raw_messages rm
SET status = 'pending'::message_status,
    match_result = NULL,
    error_message = NULL, processing_claim_stage = NULL,
    processing_claimed_at = NULL, processing_claimed_by = NULL
WHERE rm.id = (SELECT raw_message_id FROM air_violations WHERE id = 908)
  AND rm.status NOT IN ('materialized'::message_status, 'duplicate'::message_status)
  AND NOT EXISTS (SELECT 1 FROM incidents i
                  WHERE i.raw_message_id = rm.id AND i.is_deleted = false);
DELETE FROM air_violations WHERE id = 908
  AND review_status = 'flagged_for_review' AND review_reason = 'excluded_kinetic_casualty_or_damage';
-- air_violation_id=909 reason=excluded_kinetic_casualty_or_damage
UPDATE raw_messages rm
SET status = 'pending'::message_status,
    match_result = NULL,
    error_message = NULL, processing_claim_stage = NULL,
    processing_claimed_at = NULL, processing_claimed_by = NULL
WHERE rm.id = (SELECT raw_message_id FROM air_violations WHERE id = 909)
  AND rm.status NOT IN ('materialized'::message_status, 'duplicate'::message_status)
  AND NOT EXISTS (SELECT 1 FROM incidents i
                  WHERE i.raw_message_id = rm.id AND i.is_deleted = false);
DELETE FROM air_violations WHERE id = 909
  AND review_status = 'flagged_for_review' AND review_reason = 'excluded_kinetic_casualty_or_damage';
-- air_violation_id=910 reason=excluded_kinetic_casualty_or_damage
UPDATE raw_messages rm
SET status = 'pending'::message_status,
    match_result = NULL,
    error_message = NULL, processing_claim_stage = NULL,
    processing_claimed_at = NULL, processing_claimed_by = NULL
WHERE rm.id = (SELECT raw_message_id FROM air_violations WHERE id = 910)
  AND rm.status NOT IN ('materialized'::message_status, 'duplicate'::message_status)
  AND NOT EXISTS (SELECT 1 FROM incidents i
                  WHERE i.raw_message_id = rm.id AND i.is_deleted = false);
DELETE FROM air_violations WHERE id = 910
  AND review_status = 'flagged_for_review' AND review_reason = 'excluded_kinetic_casualty_or_damage';
-- air_violation_id=911 reason=excluded_kinetic_casualty_or_damage
UPDATE raw_messages rm
SET status = 'pending'::message_status,
    match_result = NULL,
    error_message = NULL, processing_claim_stage = NULL,
    processing_claimed_at = NULL, processing_claimed_by = NULL
WHERE rm.id = (SELECT raw_message_id FROM air_violations WHERE id = 911)
  AND rm.status NOT IN ('materialized'::message_status, 'duplicate'::message_status)
  AND NOT EXISTS (SELECT 1 FROM incidents i
                  WHERE i.raw_message_id = rm.id AND i.is_deleted = false);
DELETE FROM air_violations WHERE id = 911
  AND review_status = 'flagged_for_review' AND review_reason = 'excluded_kinetic_casualty_or_damage';
-- air_violation_id=912 reason=excluded_kinetic_casualty_or_damage
UPDATE raw_messages rm
SET status = 'pending'::message_status,
    match_result = NULL,
    error_message = NULL, processing_claim_stage = NULL,
    processing_claimed_at = NULL, processing_claimed_by = NULL
WHERE rm.id = (SELECT raw_message_id FROM air_violations WHERE id = 912)
  AND rm.status NOT IN ('materialized'::message_status, 'duplicate'::message_status)
  AND NOT EXISTS (SELECT 1 FROM incidents i
                  WHERE i.raw_message_id = rm.id AND i.is_deleted = false);
DELETE FROM air_violations WHERE id = 912
  AND review_status = 'flagged_for_review' AND review_reason = 'excluded_kinetic_casualty_or_damage';
-- air_violation_id=913 reason=excluded_kinetic_casualty_or_damage
UPDATE raw_messages rm
SET status = 'pending'::message_status,
    match_result = NULL,
    error_message = NULL, processing_claim_stage = NULL,
    processing_claimed_at = NULL, processing_claimed_by = NULL
WHERE rm.id = (SELECT raw_message_id FROM air_violations WHERE id = 913)
  AND rm.status NOT IN ('materialized'::message_status, 'duplicate'::message_status)
  AND NOT EXISTS (SELECT 1 FROM incidents i
                  WHERE i.raw_message_id = rm.id AND i.is_deleted = false);
DELETE FROM air_violations WHERE id = 913
  AND review_status = 'flagged_for_review' AND review_reason = 'excluded_kinetic_casualty_or_damage';
-- air_violation_id=914 reason=excluded_kinetic_casualty_or_damage
UPDATE raw_messages rm
SET status = 'pending'::message_status,
    match_result = NULL,
    error_message = NULL, processing_claim_stage = NULL,
    processing_claimed_at = NULL, processing_claimed_by = NULL
WHERE rm.id = (SELECT raw_message_id FROM air_violations WHERE id = 914)
  AND rm.status NOT IN ('materialized'::message_status, 'duplicate'::message_status)
  AND NOT EXISTS (SELECT 1 FROM incidents i
                  WHERE i.raw_message_id = rm.id AND i.is_deleted = false);
DELETE FROM air_violations WHERE id = 914
  AND review_status = 'flagged_for_review' AND review_reason = 'excluded_kinetic_casualty_or_damage';
-- air_violation_id=915 reason=excluded_kinetic_casualty_or_damage
UPDATE raw_messages rm
SET status = 'pending'::message_status,
    match_result = NULL,
    error_message = NULL, processing_claim_stage = NULL,
    processing_claimed_at = NULL, processing_claimed_by = NULL
WHERE rm.id = (SELECT raw_message_id FROM air_violations WHERE id = 915)
  AND rm.status NOT IN ('materialized'::message_status, 'duplicate'::message_status)
  AND NOT EXISTS (SELECT 1 FROM incidents i
                  WHERE i.raw_message_id = rm.id AND i.is_deleted = false);
DELETE FROM air_violations WHERE id = 915
  AND review_status = 'flagged_for_review' AND review_reason = 'excluded_kinetic_casualty_or_damage';
-- air_violation_id=916 reason=excluded_kinetic_casualty_or_damage
UPDATE raw_messages rm
SET status = 'pending'::message_status,
    match_result = NULL,
    error_message = NULL, processing_claim_stage = NULL,
    processing_claimed_at = NULL, processing_claimed_by = NULL
WHERE rm.id = (SELECT raw_message_id FROM air_violations WHERE id = 916)
  AND rm.status NOT IN ('materialized'::message_status, 'duplicate'::message_status)
  AND NOT EXISTS (SELECT 1 FROM incidents i
                  WHERE i.raw_message_id = rm.id AND i.is_deleted = false);
DELETE FROM air_violations WHERE id = 916
  AND review_status = 'flagged_for_review' AND review_reason = 'excluded_kinetic_casualty_or_damage';
-- air_violation_id=917 reason=excluded_kinetic_casualty_or_damage
UPDATE raw_messages rm
SET status = 'pending'::message_status,
    match_result = NULL,
    error_message = NULL, processing_claim_stage = NULL,
    processing_claimed_at = NULL, processing_claimed_by = NULL
WHERE rm.id = (SELECT raw_message_id FROM air_violations WHERE id = 917)
  AND rm.status NOT IN ('materialized'::message_status, 'duplicate'::message_status)
  AND NOT EXISTS (SELECT 1 FROM incidents i
                  WHERE i.raw_message_id = rm.id AND i.is_deleted = false);
DELETE FROM air_violations WHERE id = 917
  AND review_status = 'flagged_for_review' AND review_reason = 'excluded_kinetic_casualty_or_damage';
-- air_violation_id=918 reason=excluded_kinetic_casualty_or_damage
UPDATE raw_messages rm
SET status = 'pending'::message_status,
    match_result = NULL,
    error_message = NULL, processing_claim_stage = NULL,
    processing_claimed_at = NULL, processing_claimed_by = NULL
WHERE rm.id = (SELECT raw_message_id FROM air_violations WHERE id = 918)
  AND rm.status NOT IN ('materialized'::message_status, 'duplicate'::message_status)
  AND NOT EXISTS (SELECT 1 FROM incidents i
                  WHERE i.raw_message_id = rm.id AND i.is_deleted = false);
DELETE FROM air_violations WHERE id = 918
  AND review_status = 'flagged_for_review' AND review_reason = 'excluded_kinetic_casualty_or_damage';
-- air_violation_id=919 reason=excluded_kinetic_casualty_or_damage
UPDATE raw_messages rm
SET status = 'pending'::message_status,
    match_result = NULL,
    error_message = NULL, processing_claim_stage = NULL,
    processing_claimed_at = NULL, processing_claimed_by = NULL
WHERE rm.id = (SELECT raw_message_id FROM air_violations WHERE id = 919)
  AND rm.status NOT IN ('materialized'::message_status, 'duplicate'::message_status)
  AND NOT EXISTS (SELECT 1 FROM incidents i
                  WHERE i.raw_message_id = rm.id AND i.is_deleted = false);
DELETE FROM air_violations WHERE id = 919
  AND review_status = 'flagged_for_review' AND review_reason = 'excluded_kinetic_casualty_or_damage';
-- air_violation_id=920 reason=excluded_kinetic_casualty_or_damage
UPDATE raw_messages rm
SET status = 'pending'::message_status,
    match_result = NULL,
    error_message = NULL, processing_claim_stage = NULL,
    processing_claimed_at = NULL, processing_claimed_by = NULL
WHERE rm.id = (SELECT raw_message_id FROM air_violations WHERE id = 920)
  AND rm.status NOT IN ('materialized'::message_status, 'duplicate'::message_status)
  AND NOT EXISTS (SELECT 1 FROM incidents i
                  WHERE i.raw_message_id = rm.id AND i.is_deleted = false);
DELETE FROM air_violations WHERE id = 920
  AND review_status = 'flagged_for_review' AND review_reason = 'excluded_kinetic_casualty_or_damage';
-- air_violation_id=921 reason=excluded_kinetic_casualty_or_damage
UPDATE raw_messages rm
SET status = 'pending'::message_status,
    match_result = NULL,
    error_message = NULL, processing_claim_stage = NULL,
    processing_claimed_at = NULL, processing_claimed_by = NULL
WHERE rm.id = (SELECT raw_message_id FROM air_violations WHERE id = 921)
  AND rm.status NOT IN ('materialized'::message_status, 'duplicate'::message_status)
  AND NOT EXISTS (SELECT 1 FROM incidents i
                  WHERE i.raw_message_id = rm.id AND i.is_deleted = false);
DELETE FROM air_violations WHERE id = 921
  AND review_status = 'flagged_for_review' AND review_reason = 'excluded_kinetic_casualty_or_damage';
-- air_violation_id=922 reason=excluded_kinetic_casualty_or_damage
UPDATE raw_messages rm
SET status = 'pending'::message_status,
    match_result = NULL,
    error_message = NULL, processing_claim_stage = NULL,
    processing_claimed_at = NULL, processing_claimed_by = NULL
WHERE rm.id = (SELECT raw_message_id FROM air_violations WHERE id = 922)
  AND rm.status NOT IN ('materialized'::message_status, 'duplicate'::message_status)
  AND NOT EXISTS (SELECT 1 FROM incidents i
                  WHERE i.raw_message_id = rm.id AND i.is_deleted = false);
DELETE FROM air_violations WHERE id = 922
  AND review_status = 'flagged_for_review' AND review_reason = 'excluded_kinetic_casualty_or_damage';
-- air_violation_id=923 reason=excluded_kinetic_casualty_or_damage
UPDATE raw_messages rm
SET status = 'pending'::message_status,
    match_result = NULL,
    error_message = NULL, processing_claim_stage = NULL,
    processing_claimed_at = NULL, processing_claimed_by = NULL
WHERE rm.id = (SELECT raw_message_id FROM air_violations WHERE id = 923)
  AND rm.status NOT IN ('materialized'::message_status, 'duplicate'::message_status)
  AND NOT EXISTS (SELECT 1 FROM incidents i
                  WHERE i.raw_message_id = rm.id AND i.is_deleted = false);
DELETE FROM air_violations WHERE id = 923
  AND review_status = 'flagged_for_review' AND review_reason = 'excluded_kinetic_casualty_or_damage';
-- air_violation_id=924 reason=excluded_kinetic_casualty_or_damage
UPDATE raw_messages rm
SET status = 'pending'::message_status,
    match_result = NULL,
    error_message = NULL, processing_claim_stage = NULL,
    processing_claimed_at = NULL, processing_claimed_by = NULL
WHERE rm.id = (SELECT raw_message_id FROM air_violations WHERE id = 924)
  AND rm.status NOT IN ('materialized'::message_status, 'duplicate'::message_status)
  AND NOT EXISTS (SELECT 1 FROM incidents i
                  WHERE i.raw_message_id = rm.id AND i.is_deleted = false);
DELETE FROM air_violations WHERE id = 924
  AND review_status = 'flagged_for_review' AND review_reason = 'excluded_kinetic_casualty_or_damage';
-- air_violation_id=925 reason=excluded_kinetic_casualty_or_damage
UPDATE raw_messages rm
SET status = 'pending'::message_status,
    match_result = NULL,
    error_message = NULL, processing_claim_stage = NULL,
    processing_claimed_at = NULL, processing_claimed_by = NULL
WHERE rm.id = (SELECT raw_message_id FROM air_violations WHERE id = 925)
  AND rm.status NOT IN ('materialized'::message_status, 'duplicate'::message_status)
  AND NOT EXISTS (SELECT 1 FROM incidents i
                  WHERE i.raw_message_id = rm.id AND i.is_deleted = false);
DELETE FROM air_violations WHERE id = 925
  AND review_status = 'flagged_for_review' AND review_reason = 'excluded_kinetic_casualty_or_damage';
-- air_violation_id=926 reason=excluded_kinetic_casualty_or_damage
UPDATE raw_messages rm
SET status = 'pending'::message_status,
    match_result = NULL,
    error_message = NULL, processing_claim_stage = NULL,
    processing_claimed_at = NULL, processing_claimed_by = NULL
WHERE rm.id = (SELECT raw_message_id FROM air_violations WHERE id = 926)
  AND rm.status NOT IN ('materialized'::message_status, 'duplicate'::message_status)
  AND NOT EXISTS (SELECT 1 FROM incidents i
                  WHERE i.raw_message_id = rm.id AND i.is_deleted = false);
DELETE FROM air_violations WHERE id = 926
  AND review_status = 'flagged_for_review' AND review_reason = 'excluded_kinetic_casualty_or_damage';
-- air_violation_id=927 reason=excluded_kinetic_casualty_or_damage
UPDATE raw_messages rm
SET status = 'pending'::message_status,
    match_result = NULL,
    error_message = NULL, processing_claim_stage = NULL,
    processing_claimed_at = NULL, processing_claimed_by = NULL
WHERE rm.id = (SELECT raw_message_id FROM air_violations WHERE id = 927)
  AND rm.status NOT IN ('materialized'::message_status, 'duplicate'::message_status)
  AND NOT EXISTS (SELECT 1 FROM incidents i
                  WHERE i.raw_message_id = rm.id AND i.is_deleted = false);
DELETE FROM air_violations WHERE id = 927
  AND review_status = 'flagged_for_review' AND review_reason = 'excluded_kinetic_casualty_or_damage';
-- air_violation_id=928 reason=excluded_kinetic_casualty_or_damage
UPDATE raw_messages rm
SET status = 'pending'::message_status,
    match_result = NULL,
    error_message = NULL, processing_claim_stage = NULL,
    processing_claimed_at = NULL, processing_claimed_by = NULL
WHERE rm.id = (SELECT raw_message_id FROM air_violations WHERE id = 928)
  AND rm.status NOT IN ('materialized'::message_status, 'duplicate'::message_status)
  AND NOT EXISTS (SELECT 1 FROM incidents i
                  WHERE i.raw_message_id = rm.id AND i.is_deleted = false);
DELETE FROM air_violations WHERE id = 928
  AND review_status = 'flagged_for_review' AND review_reason = 'excluded_kinetic_casualty_or_damage';
-- air_violation_id=929 reason=excluded_kinetic_casualty_or_damage
UPDATE raw_messages rm
SET status = 'pending'::message_status,
    match_result = NULL,
    error_message = NULL, processing_claim_stage = NULL,
    processing_claimed_at = NULL, processing_claimed_by = NULL
WHERE rm.id = (SELECT raw_message_id FROM air_violations WHERE id = 929)
  AND rm.status NOT IN ('materialized'::message_status, 'duplicate'::message_status)
  AND NOT EXISTS (SELECT 1 FROM incidents i
                  WHERE i.raw_message_id = rm.id AND i.is_deleted = false);
DELETE FROM air_violations WHERE id = 929
  AND review_status = 'flagged_for_review' AND review_reason = 'excluded_kinetic_casualty_or_damage';
-- air_violation_id=930 reason=excluded_kinetic_casualty_or_damage
UPDATE raw_messages rm
SET status = 'pending'::message_status,
    match_result = NULL,
    error_message = NULL, processing_claim_stage = NULL,
    processing_claimed_at = NULL, processing_claimed_by = NULL
WHERE rm.id = (SELECT raw_message_id FROM air_violations WHERE id = 930)
  AND rm.status NOT IN ('materialized'::message_status, 'duplicate'::message_status)
  AND NOT EXISTS (SELECT 1 FROM incidents i
                  WHERE i.raw_message_id = rm.id AND i.is_deleted = false);
DELETE FROM air_violations WHERE id = 930
  AND review_status = 'flagged_for_review' AND review_reason = 'excluded_kinetic_casualty_or_damage';
-- air_violation_id=931 reason=excluded_kinetic_casualty_or_damage
UPDATE raw_messages rm
SET status = 'pending'::message_status,
    match_result = NULL,
    error_message = NULL, processing_claim_stage = NULL,
    processing_claimed_at = NULL, processing_claimed_by = NULL
WHERE rm.id = (SELECT raw_message_id FROM air_violations WHERE id = 931)
  AND rm.status NOT IN ('materialized'::message_status, 'duplicate'::message_status)
  AND NOT EXISTS (SELECT 1 FROM incidents i
                  WHERE i.raw_message_id = rm.id AND i.is_deleted = false);
DELETE FROM air_violations WHERE id = 931
  AND review_status = 'flagged_for_review' AND review_reason = 'excluded_kinetic_casualty_or_damage';
-- air_violation_id=932 reason=excluded_kinetic_casualty_or_damage
UPDATE raw_messages rm
SET status = 'pending'::message_status,
    match_result = NULL,
    error_message = NULL, processing_claim_stage = NULL,
    processing_claimed_at = NULL, processing_claimed_by = NULL
WHERE rm.id = (SELECT raw_message_id FROM air_violations WHERE id = 932)
  AND rm.status NOT IN ('materialized'::message_status, 'duplicate'::message_status)
  AND NOT EXISTS (SELECT 1 FROM incidents i
                  WHERE i.raw_message_id = rm.id AND i.is_deleted = false);
DELETE FROM air_violations WHERE id = 932
  AND review_status = 'flagged_for_review' AND review_reason = 'excluded_kinetic_casualty_or_damage';
-- air_violation_id=933 reason=excluded_kinetic_casualty_or_damage
UPDATE raw_messages rm
SET status = 'pending'::message_status,
    match_result = NULL,
    error_message = NULL, processing_claim_stage = NULL,
    processing_claimed_at = NULL, processing_claimed_by = NULL
WHERE rm.id = (SELECT raw_message_id FROM air_violations WHERE id = 933)
  AND rm.status NOT IN ('materialized'::message_status, 'duplicate'::message_status)
  AND NOT EXISTS (SELECT 1 FROM incidents i
                  WHERE i.raw_message_id = rm.id AND i.is_deleted = false);
DELETE FROM air_violations WHERE id = 933
  AND review_status = 'flagged_for_review' AND review_reason = 'excluded_kinetic_casualty_or_damage';
-- air_violation_id=934 reason=excluded_kinetic_casualty_or_damage
UPDATE raw_messages rm
SET status = 'pending'::message_status,
    match_result = NULL,
    error_message = NULL, processing_claim_stage = NULL,
    processing_claimed_at = NULL, processing_claimed_by = NULL
WHERE rm.id = (SELECT raw_message_id FROM air_violations WHERE id = 934)
  AND rm.status NOT IN ('materialized'::message_status, 'duplicate'::message_status)
  AND NOT EXISTS (SELECT 1 FROM incidents i
                  WHERE i.raw_message_id = rm.id AND i.is_deleted = false);
DELETE FROM air_violations WHERE id = 934
  AND review_status = 'flagged_for_review' AND review_reason = 'excluded_kinetic_casualty_or_damage';
-- air_violation_id=935 reason=excluded_kinetic_casualty_or_damage
UPDATE raw_messages rm
SET status = 'pending'::message_status,
    match_result = NULL,
    error_message = NULL, processing_claim_stage = NULL,
    processing_claimed_at = NULL, processing_claimed_by = NULL
WHERE rm.id = (SELECT raw_message_id FROM air_violations WHERE id = 935)
  AND rm.status NOT IN ('materialized'::message_status, 'duplicate'::message_status)
  AND NOT EXISTS (SELECT 1 FROM incidents i
                  WHERE i.raw_message_id = rm.id AND i.is_deleted = false);
DELETE FROM air_violations WHERE id = 935
  AND review_status = 'flagged_for_review' AND review_reason = 'excluded_kinetic_casualty_or_damage';
-- air_violation_id=936 reason=excluded_kinetic_casualty_or_damage
UPDATE raw_messages rm
SET status = 'pending'::message_status,
    match_result = NULL,
    error_message = NULL, processing_claim_stage = NULL,
    processing_claimed_at = NULL, processing_claimed_by = NULL
WHERE rm.id = (SELECT raw_message_id FROM air_violations WHERE id = 936)
  AND rm.status NOT IN ('materialized'::message_status, 'duplicate'::message_status)
  AND NOT EXISTS (SELECT 1 FROM incidents i
                  WHERE i.raw_message_id = rm.id AND i.is_deleted = false);
DELETE FROM air_violations WHERE id = 936
  AND review_status = 'flagged_for_review' AND review_reason = 'excluded_kinetic_casualty_or_damage';
-- air_violation_id=937 reason=excluded_kinetic_casualty_or_damage
UPDATE raw_messages rm
SET status = 'pending'::message_status,
    match_result = NULL,
    error_message = NULL, processing_claim_stage = NULL,
    processing_claimed_at = NULL, processing_claimed_by = NULL
WHERE rm.id = (SELECT raw_message_id FROM air_violations WHERE id = 937)
  AND rm.status NOT IN ('materialized'::message_status, 'duplicate'::message_status)
  AND NOT EXISTS (SELECT 1 FROM incidents i
                  WHERE i.raw_message_id = rm.id AND i.is_deleted = false);
DELETE FROM air_violations WHERE id = 937
  AND review_status = 'flagged_for_review' AND review_reason = 'excluded_kinetic_casualty_or_damage';
-- air_violation_id=938 reason=excluded_kinetic_casualty_or_damage
UPDATE raw_messages rm
SET status = 'pending'::message_status,
    match_result = NULL,
    error_message = NULL, processing_claim_stage = NULL,
    processing_claimed_at = NULL, processing_claimed_by = NULL
WHERE rm.id = (SELECT raw_message_id FROM air_violations WHERE id = 938)
  AND rm.status NOT IN ('materialized'::message_status, 'duplicate'::message_status)
  AND NOT EXISTS (SELECT 1 FROM incidents i
                  WHERE i.raw_message_id = rm.id AND i.is_deleted = false);
DELETE FROM air_violations WHERE id = 938
  AND review_status = 'flagged_for_review' AND review_reason = 'excluded_kinetic_casualty_or_damage';
-- air_violation_id=939 reason=excluded_kinetic_casualty_or_damage
UPDATE raw_messages rm
SET status = 'pending'::message_status,
    match_result = NULL,
    error_message = NULL, processing_claim_stage = NULL,
    processing_claimed_at = NULL, processing_claimed_by = NULL
WHERE rm.id = (SELECT raw_message_id FROM air_violations WHERE id = 939)
  AND rm.status NOT IN ('materialized'::message_status, 'duplicate'::message_status)
  AND NOT EXISTS (SELECT 1 FROM incidents i
                  WHERE i.raw_message_id = rm.id AND i.is_deleted = false);
DELETE FROM air_violations WHERE id = 939
  AND review_status = 'flagged_for_review' AND review_reason = 'excluded_kinetic_casualty_or_damage';
-- air_violation_id=940 reason=excluded_kinetic_casualty_or_damage
UPDATE raw_messages rm
SET status = 'pending'::message_status,
    match_result = NULL,
    error_message = NULL, processing_claim_stage = NULL,
    processing_claimed_at = NULL, processing_claimed_by = NULL
WHERE rm.id = (SELECT raw_message_id FROM air_violations WHERE id = 940)
  AND rm.status NOT IN ('materialized'::message_status, 'duplicate'::message_status)
  AND NOT EXISTS (SELECT 1 FROM incidents i
                  WHERE i.raw_message_id = rm.id AND i.is_deleted = false);
DELETE FROM air_violations WHERE id = 940
  AND review_status = 'flagged_for_review' AND review_reason = 'excluded_kinetic_casualty_or_damage';
-- air_violation_id=941 reason=excluded_kinetic_casualty_or_damage
UPDATE raw_messages rm
SET status = 'pending'::message_status,
    match_result = NULL,
    error_message = NULL, processing_claim_stage = NULL,
    processing_claimed_at = NULL, processing_claimed_by = NULL
WHERE rm.id = (SELECT raw_message_id FROM air_violations WHERE id = 941)
  AND rm.status NOT IN ('materialized'::message_status, 'duplicate'::message_status)
  AND NOT EXISTS (SELECT 1 FROM incidents i
                  WHERE i.raw_message_id = rm.id AND i.is_deleted = false);
DELETE FROM air_violations WHERE id = 941
  AND review_status = 'flagged_for_review' AND review_reason = 'excluded_kinetic_casualty_or_damage';
-- air_violation_id=942 reason=excluded_kinetic_casualty_or_damage
UPDATE raw_messages rm
SET status = 'pending'::message_status,
    match_result = NULL,
    error_message = NULL, processing_claim_stage = NULL,
    processing_claimed_at = NULL, processing_claimed_by = NULL
WHERE rm.id = (SELECT raw_message_id FROM air_violations WHERE id = 942)
  AND rm.status NOT IN ('materialized'::message_status, 'duplicate'::message_status)
  AND NOT EXISTS (SELECT 1 FROM incidents i
                  WHERE i.raw_message_id = rm.id AND i.is_deleted = false);
DELETE FROM air_violations WHERE id = 942
  AND review_status = 'flagged_for_review' AND review_reason = 'excluded_kinetic_casualty_or_damage';
-- air_violation_id=943 reason=excluded_kinetic_casualty_or_damage
UPDATE raw_messages rm
SET status = 'pending'::message_status,
    match_result = NULL,
    error_message = NULL, processing_claim_stage = NULL,
    processing_claimed_at = NULL, processing_claimed_by = NULL
WHERE rm.id = (SELECT raw_message_id FROM air_violations WHERE id = 943)
  AND rm.status NOT IN ('materialized'::message_status, 'duplicate'::message_status)
  AND NOT EXISTS (SELECT 1 FROM incidents i
                  WHERE i.raw_message_id = rm.id AND i.is_deleted = false);
DELETE FROM air_violations WHERE id = 943
  AND review_status = 'flagged_for_review' AND review_reason = 'excluded_kinetic_casualty_or_damage';
-- air_violation_id=944 reason=excluded_kinetic_casualty_or_damage
UPDATE raw_messages rm
SET status = 'pending'::message_status,
    match_result = NULL,
    error_message = NULL, processing_claim_stage = NULL,
    processing_claimed_at = NULL, processing_claimed_by = NULL
WHERE rm.id = (SELECT raw_message_id FROM air_violations WHERE id = 944)
  AND rm.status NOT IN ('materialized'::message_status, 'duplicate'::message_status)
  AND NOT EXISTS (SELECT 1 FROM incidents i
                  WHERE i.raw_message_id = rm.id AND i.is_deleted = false);
DELETE FROM air_violations WHERE id = 944
  AND review_status = 'flagged_for_review' AND review_reason = 'excluded_kinetic_casualty_or_damage';
-- air_violation_id=945 reason=excluded_kinetic_casualty_or_damage
UPDATE raw_messages rm
SET status = 'pending'::message_status,
    match_result = NULL,
    error_message = NULL, processing_claim_stage = NULL,
    processing_claimed_at = NULL, processing_claimed_by = NULL
WHERE rm.id = (SELECT raw_message_id FROM air_violations WHERE id = 945)
  AND rm.status NOT IN ('materialized'::message_status, 'duplicate'::message_status)
  AND NOT EXISTS (SELECT 1 FROM incidents i
                  WHERE i.raw_message_id = rm.id AND i.is_deleted = false);
DELETE FROM air_violations WHERE id = 945
  AND review_status = 'flagged_for_review' AND review_reason = 'excluded_kinetic_casualty_or_damage';
-- air_violation_id=946 reason=excluded_kinetic_casualty_or_damage
UPDATE raw_messages rm
SET status = 'pending'::message_status,
    match_result = NULL,
    error_message = NULL, processing_claim_stage = NULL,
    processing_claimed_at = NULL, processing_claimed_by = NULL
WHERE rm.id = (SELECT raw_message_id FROM air_violations WHERE id = 946)
  AND rm.status NOT IN ('materialized'::message_status, 'duplicate'::message_status)
  AND NOT EXISTS (SELECT 1 FROM incidents i
                  WHERE i.raw_message_id = rm.id AND i.is_deleted = false);
DELETE FROM air_violations WHERE id = 946
  AND review_status = 'flagged_for_review' AND review_reason = 'excluded_kinetic_casualty_or_damage';
-- air_violation_id=947 reason=excluded_kinetic_casualty_or_damage
UPDATE raw_messages rm
SET status = 'pending'::message_status,
    match_result = NULL,
    error_message = NULL, processing_claim_stage = NULL,
    processing_claimed_at = NULL, processing_claimed_by = NULL
WHERE rm.id = (SELECT raw_message_id FROM air_violations WHERE id = 947)
  AND rm.status NOT IN ('materialized'::message_status, 'duplicate'::message_status)
  AND NOT EXISTS (SELECT 1 FROM incidents i
                  WHERE i.raw_message_id = rm.id AND i.is_deleted = false);
DELETE FROM air_violations WHERE id = 947
  AND review_status = 'flagged_for_review' AND review_reason = 'excluded_kinetic_casualty_or_damage';
-- air_violation_id=948 reason=excluded_kinetic_casualty_or_damage
UPDATE raw_messages rm
SET status = 'pending'::message_status,
    match_result = NULL,
    error_message = NULL, processing_claim_stage = NULL,
    processing_claimed_at = NULL, processing_claimed_by = NULL
WHERE rm.id = (SELECT raw_message_id FROM air_violations WHERE id = 948)
  AND rm.status NOT IN ('materialized'::message_status, 'duplicate'::message_status)
  AND NOT EXISTS (SELECT 1 FROM incidents i
                  WHERE i.raw_message_id = rm.id AND i.is_deleted = false);
DELETE FROM air_violations WHERE id = 948
  AND review_status = 'flagged_for_review' AND review_reason = 'excluded_kinetic_casualty_or_damage';
-- air_violation_id=949 reason=excluded_kinetic_casualty_or_damage
UPDATE raw_messages rm
SET status = 'pending'::message_status,
    match_result = NULL,
    error_message = NULL, processing_claim_stage = NULL,
    processing_claimed_at = NULL, processing_claimed_by = NULL
WHERE rm.id = (SELECT raw_message_id FROM air_violations WHERE id = 949)
  AND rm.status NOT IN ('materialized'::message_status, 'duplicate'::message_status)
  AND NOT EXISTS (SELECT 1 FROM incidents i
                  WHERE i.raw_message_id = rm.id AND i.is_deleted = false);
DELETE FROM air_violations WHERE id = 949
  AND review_status = 'flagged_for_review' AND review_reason = 'excluded_kinetic_casualty_or_damage';
-- air_violation_id=950 reason=excluded_kinetic_casualty_or_damage
UPDATE raw_messages rm
SET status = 'pending'::message_status,
    match_result = NULL,
    error_message = NULL, processing_claim_stage = NULL,
    processing_claimed_at = NULL, processing_claimed_by = NULL
WHERE rm.id = (SELECT raw_message_id FROM air_violations WHERE id = 950)
  AND rm.status NOT IN ('materialized'::message_status, 'duplicate'::message_status)
  AND NOT EXISTS (SELECT 1 FROM incidents i
                  WHERE i.raw_message_id = rm.id AND i.is_deleted = false);
DELETE FROM air_violations WHERE id = 950
  AND review_status = 'flagged_for_review' AND review_reason = 'excluded_kinetic_casualty_or_damage';
-- air_violation_id=951 reason=excluded_kinetic_casualty_or_damage
UPDATE raw_messages rm
SET status = 'pending'::message_status,
    match_result = NULL,
    error_message = NULL, processing_claim_stage = NULL,
    processing_claimed_at = NULL, processing_claimed_by = NULL
WHERE rm.id = (SELECT raw_message_id FROM air_violations WHERE id = 951)
  AND rm.status NOT IN ('materialized'::message_status, 'duplicate'::message_status)
  AND NOT EXISTS (SELECT 1 FROM incidents i
                  WHERE i.raw_message_id = rm.id AND i.is_deleted = false);
DELETE FROM air_violations WHERE id = 951
  AND review_status = 'flagged_for_review' AND review_reason = 'excluded_kinetic_casualty_or_damage';
-- air_violation_id=952 reason=excluded_kinetic_casualty_or_damage
UPDATE raw_messages rm
SET status = 'pending'::message_status,
    match_result = NULL,
    error_message = NULL, processing_claim_stage = NULL,
    processing_claimed_at = NULL, processing_claimed_by = NULL
WHERE rm.id = (SELECT raw_message_id FROM air_violations WHERE id = 952)
  AND rm.status NOT IN ('materialized'::message_status, 'duplicate'::message_status)
  AND NOT EXISTS (SELECT 1 FROM incidents i
                  WHERE i.raw_message_id = rm.id AND i.is_deleted = false);
DELETE FROM air_violations WHERE id = 952
  AND review_status = 'flagged_for_review' AND review_reason = 'excluded_kinetic_casualty_or_damage';
-- air_violation_id=953 reason=excluded_kinetic_casualty_or_damage
UPDATE raw_messages rm
SET status = 'pending'::message_status,
    match_result = NULL,
    error_message = NULL, processing_claim_stage = NULL,
    processing_claimed_at = NULL, processing_claimed_by = NULL
WHERE rm.id = (SELECT raw_message_id FROM air_violations WHERE id = 953)
  AND rm.status NOT IN ('materialized'::message_status, 'duplicate'::message_status)
  AND NOT EXISTS (SELECT 1 FROM incidents i
                  WHERE i.raw_message_id = rm.id AND i.is_deleted = false);
DELETE FROM air_violations WHERE id = 953
  AND review_status = 'flagged_for_review' AND review_reason = 'excluded_kinetic_casualty_or_damage';
-- air_violation_id=954 reason=excluded_kinetic_casualty_or_damage
UPDATE raw_messages rm
SET status = 'pending'::message_status,
    match_result = NULL,
    error_message = NULL, processing_claim_stage = NULL,
    processing_claimed_at = NULL, processing_claimed_by = NULL
WHERE rm.id = (SELECT raw_message_id FROM air_violations WHERE id = 954)
  AND rm.status NOT IN ('materialized'::message_status, 'duplicate'::message_status)
  AND NOT EXISTS (SELECT 1 FROM incidents i
                  WHERE i.raw_message_id = rm.id AND i.is_deleted = false);
DELETE FROM air_violations WHERE id = 954
  AND review_status = 'flagged_for_review' AND review_reason = 'excluded_kinetic_casualty_or_damage';
-- air_violation_id=959 reason=excluded_kinetic_casualty_or_damage
UPDATE raw_messages rm
SET status = 'pending'::message_status,
    match_result = NULL,
    error_message = NULL, processing_claim_stage = NULL,
    processing_claimed_at = NULL, processing_claimed_by = NULL
WHERE rm.id = (SELECT raw_message_id FROM air_violations WHERE id = 959)
  AND rm.status NOT IN ('materialized'::message_status, 'duplicate'::message_status)
  AND NOT EXISTS (SELECT 1 FROM incidents i
                  WHERE i.raw_message_id = rm.id AND i.is_deleted = false);
DELETE FROM air_violations WHERE id = 959
  AND review_status = 'flagged_for_review' AND review_reason = 'excluded_kinetic_casualty_or_damage';
-- air_violation_id=960 reason=excluded_kinetic_casualty_or_damage
UPDATE raw_messages rm
SET status = 'pending'::message_status,
    match_result = NULL,
    error_message = NULL, processing_claim_stage = NULL,
    processing_claimed_at = NULL, processing_claimed_by = NULL
WHERE rm.id = (SELECT raw_message_id FROM air_violations WHERE id = 960)
  AND rm.status NOT IN ('materialized'::message_status, 'duplicate'::message_status)
  AND NOT EXISTS (SELECT 1 FROM incidents i
                  WHERE i.raw_message_id = rm.id AND i.is_deleted = false);
DELETE FROM air_violations WHERE id = 960
  AND review_status = 'flagged_for_review' AND review_reason = 'excluded_kinetic_casualty_or_damage';
-- air_violation_id=961 reason=excluded_kinetic_casualty_or_damage
UPDATE raw_messages rm
SET status = 'pending'::message_status,
    match_result = NULL,
    error_message = NULL, processing_claim_stage = NULL,
    processing_claimed_at = NULL, processing_claimed_by = NULL
WHERE rm.id = (SELECT raw_message_id FROM air_violations WHERE id = 961)
  AND rm.status NOT IN ('materialized'::message_status, 'duplicate'::message_status)
  AND NOT EXISTS (SELECT 1 FROM incidents i
                  WHERE i.raw_message_id = rm.id AND i.is_deleted = false);
DELETE FROM air_violations WHERE id = 961
  AND review_status = 'flagged_for_review' AND review_reason = 'excluded_kinetic_casualty_or_damage';
-- air_violation_id=962 reason=excluded_kinetic_casualty_or_damage
UPDATE raw_messages rm
SET status = 'pending'::message_status,
    match_result = NULL,
    error_message = NULL, processing_claim_stage = NULL,
    processing_claimed_at = NULL, processing_claimed_by = NULL
WHERE rm.id = (SELECT raw_message_id FROM air_violations WHERE id = 962)
  AND rm.status NOT IN ('materialized'::message_status, 'duplicate'::message_status)
  AND NOT EXISTS (SELECT 1 FROM incidents i
                  WHERE i.raw_message_id = rm.id AND i.is_deleted = false);
DELETE FROM air_violations WHERE id = 962
  AND review_status = 'flagged_for_review' AND review_reason = 'excluded_kinetic_casualty_or_damage';
-- air_violation_id=963 reason=excluded_kinetic_casualty_or_damage
UPDATE raw_messages rm
SET status = 'pending'::message_status,
    match_result = NULL,
    error_message = NULL, processing_claim_stage = NULL,
    processing_claimed_at = NULL, processing_claimed_by = NULL
WHERE rm.id = (SELECT raw_message_id FROM air_violations WHERE id = 963)
  AND rm.status NOT IN ('materialized'::message_status, 'duplicate'::message_status)
  AND NOT EXISTS (SELECT 1 FROM incidents i
                  WHERE i.raw_message_id = rm.id AND i.is_deleted = false);
DELETE FROM air_violations WHERE id = 963
  AND review_status = 'flagged_for_review' AND review_reason = 'excluded_kinetic_casualty_or_damage';
-- air_violation_id=965 reason=excluded_kinetic_casualty_or_damage
UPDATE raw_messages rm
SET status = 'pending'::message_status,
    match_result = NULL,
    error_message = NULL, processing_claim_stage = NULL,
    processing_claimed_at = NULL, processing_claimed_by = NULL
WHERE rm.id = (SELECT raw_message_id FROM air_violations WHERE id = 965)
  AND rm.status NOT IN ('materialized'::message_status, 'duplicate'::message_status)
  AND NOT EXISTS (SELECT 1 FROM incidents i
                  WHERE i.raw_message_id = rm.id AND i.is_deleted = false);
DELETE FROM air_violations WHERE id = 965
  AND review_status = 'flagged_for_review' AND review_reason = 'excluded_kinetic_casualty_or_damage';
-- air_violation_id=966 reason=excluded_kinetic_casualty_or_damage
UPDATE raw_messages rm
SET status = 'pending'::message_status,
    match_result = NULL,
    error_message = NULL, processing_claim_stage = NULL,
    processing_claimed_at = NULL, processing_claimed_by = NULL
WHERE rm.id = (SELECT raw_message_id FROM air_violations WHERE id = 966)
  AND rm.status NOT IN ('materialized'::message_status, 'duplicate'::message_status)
  AND NOT EXISTS (SELECT 1 FROM incidents i
                  WHERE i.raw_message_id = rm.id AND i.is_deleted = false);
DELETE FROM air_violations WHERE id = 966
  AND review_status = 'flagged_for_review' AND review_reason = 'excluded_kinetic_casualty_or_damage';
-- air_violation_id=967 reason=excluded_kinetic_casualty_or_damage
UPDATE raw_messages rm
SET status = 'pending'::message_status,
    match_result = NULL,
    error_message = NULL, processing_claim_stage = NULL,
    processing_claimed_at = NULL, processing_claimed_by = NULL
WHERE rm.id = (SELECT raw_message_id FROM air_violations WHERE id = 967)
  AND rm.status NOT IN ('materialized'::message_status, 'duplicate'::message_status)
  AND NOT EXISTS (SELECT 1 FROM incidents i
                  WHERE i.raw_message_id = rm.id AND i.is_deleted = false);
DELETE FROM air_violations WHERE id = 967
  AND review_status = 'flagged_for_review' AND review_reason = 'excluded_kinetic_casualty_or_damage';
-- air_violation_id=968 reason=excluded_kinetic_casualty_or_damage
UPDATE raw_messages rm
SET status = 'pending'::message_status,
    match_result = NULL,
    error_message = NULL, processing_claim_stage = NULL,
    processing_claimed_at = NULL, processing_claimed_by = NULL
WHERE rm.id = (SELECT raw_message_id FROM air_violations WHERE id = 968)
  AND rm.status NOT IN ('materialized'::message_status, 'duplicate'::message_status)
  AND NOT EXISTS (SELECT 1 FROM incidents i
                  WHERE i.raw_message_id = rm.id AND i.is_deleted = false);
DELETE FROM air_violations WHERE id = 968
  AND review_status = 'flagged_for_review' AND review_reason = 'excluded_kinetic_casualty_or_damage';
-- air_violation_id=969 reason=excluded_kinetic_casualty_or_damage
UPDATE raw_messages rm
SET status = 'pending'::message_status,
    match_result = NULL,
    error_message = NULL, processing_claim_stage = NULL,
    processing_claimed_at = NULL, processing_claimed_by = NULL
WHERE rm.id = (SELECT raw_message_id FROM air_violations WHERE id = 969)
  AND rm.status NOT IN ('materialized'::message_status, 'duplicate'::message_status)
  AND NOT EXISTS (SELECT 1 FROM incidents i
                  WHERE i.raw_message_id = rm.id AND i.is_deleted = false);
DELETE FROM air_violations WHERE id = 969
  AND review_status = 'flagged_for_review' AND review_reason = 'excluded_kinetic_casualty_or_damage';
-- air_violation_id=970 reason=excluded_kinetic_casualty_or_damage
UPDATE raw_messages rm
SET status = 'pending'::message_status,
    match_result = NULL,
    error_message = NULL, processing_claim_stage = NULL,
    processing_claimed_at = NULL, processing_claimed_by = NULL
WHERE rm.id = (SELECT raw_message_id FROM air_violations WHERE id = 970)
  AND rm.status NOT IN ('materialized'::message_status, 'duplicate'::message_status)
  AND NOT EXISTS (SELECT 1 FROM incidents i
                  WHERE i.raw_message_id = rm.id AND i.is_deleted = false);
DELETE FROM air_violations WHERE id = 970
  AND review_status = 'flagged_for_review' AND review_reason = 'excluded_kinetic_casualty_or_damage';
-- air_violation_id=971 reason=excluded_kinetic_casualty_or_damage
UPDATE raw_messages rm
SET status = 'pending'::message_status,
    match_result = NULL,
    error_message = NULL, processing_claim_stage = NULL,
    processing_claimed_at = NULL, processing_claimed_by = NULL
WHERE rm.id = (SELECT raw_message_id FROM air_violations WHERE id = 971)
  AND rm.status NOT IN ('materialized'::message_status, 'duplicate'::message_status)
  AND NOT EXISTS (SELECT 1 FROM incidents i
                  WHERE i.raw_message_id = rm.id AND i.is_deleted = false);
DELETE FROM air_violations WHERE id = 971
  AND review_status = 'flagged_for_review' AND review_reason = 'excluded_kinetic_casualty_or_damage';
-- air_violation_id=972 reason=excluded_kinetic_casualty_or_damage
UPDATE raw_messages rm
SET status = 'pending'::message_status,
    match_result = NULL,
    error_message = NULL, processing_claim_stage = NULL,
    processing_claimed_at = NULL, processing_claimed_by = NULL
WHERE rm.id = (SELECT raw_message_id FROM air_violations WHERE id = 972)
  AND rm.status NOT IN ('materialized'::message_status, 'duplicate'::message_status)
  AND NOT EXISTS (SELECT 1 FROM incidents i
                  WHERE i.raw_message_id = rm.id AND i.is_deleted = false);
DELETE FROM air_violations WHERE id = 972
  AND review_status = 'flagged_for_review' AND review_reason = 'excluded_kinetic_casualty_or_damage';
-- air_violation_id=973 reason=excluded_kinetic_casualty_or_damage
UPDATE raw_messages rm
SET status = 'pending'::message_status,
    match_result = NULL,
    error_message = NULL, processing_claim_stage = NULL,
    processing_claimed_at = NULL, processing_claimed_by = NULL
WHERE rm.id = (SELECT raw_message_id FROM air_violations WHERE id = 973)
  AND rm.status NOT IN ('materialized'::message_status, 'duplicate'::message_status)
  AND NOT EXISTS (SELECT 1 FROM incidents i
                  WHERE i.raw_message_id = rm.id AND i.is_deleted = false);
DELETE FROM air_violations WHERE id = 973
  AND review_status = 'flagged_for_review' AND review_reason = 'excluded_kinetic_casualty_or_damage';
-- air_violation_id=974 reason=excluded_kinetic_casualty_or_damage
UPDATE raw_messages rm
SET status = 'pending'::message_status,
    match_result = NULL,
    error_message = NULL, processing_claim_stage = NULL,
    processing_claimed_at = NULL, processing_claimed_by = NULL
WHERE rm.id = (SELECT raw_message_id FROM air_violations WHERE id = 974)
  AND rm.status NOT IN ('materialized'::message_status, 'duplicate'::message_status)
  AND NOT EXISTS (SELECT 1 FROM incidents i
                  WHERE i.raw_message_id = rm.id AND i.is_deleted = false);
DELETE FROM air_violations WHERE id = 974
  AND review_status = 'flagged_for_review' AND review_reason = 'excluded_kinetic_casualty_or_damage';
-- air_violation_id=975 reason=excluded_kinetic_casualty_or_damage
UPDATE raw_messages rm
SET status = 'pending'::message_status,
    match_result = NULL,
    error_message = NULL, processing_claim_stage = NULL,
    processing_claimed_at = NULL, processing_claimed_by = NULL
WHERE rm.id = (SELECT raw_message_id FROM air_violations WHERE id = 975)
  AND rm.status NOT IN ('materialized'::message_status, 'duplicate'::message_status)
  AND NOT EXISTS (SELECT 1 FROM incidents i
                  WHERE i.raw_message_id = rm.id AND i.is_deleted = false);
DELETE FROM air_violations WHERE id = 975
  AND review_status = 'flagged_for_review' AND review_reason = 'excluded_kinetic_casualty_or_damage';
-- air_violation_id=976 reason=excluded_kinetic_casualty_or_damage
UPDATE raw_messages rm
SET status = 'pending'::message_status,
    match_result = NULL,
    error_message = NULL, processing_claim_stage = NULL,
    processing_claimed_at = NULL, processing_claimed_by = NULL
WHERE rm.id = (SELECT raw_message_id FROM air_violations WHERE id = 976)
  AND rm.status NOT IN ('materialized'::message_status, 'duplicate'::message_status)
  AND NOT EXISTS (SELECT 1 FROM incidents i
                  WHERE i.raw_message_id = rm.id AND i.is_deleted = false);
DELETE FROM air_violations WHERE id = 976
  AND review_status = 'flagged_for_review' AND review_reason = 'excluded_kinetic_casualty_or_damage';
-- air_violation_id=977 reason=excluded_kinetic_casualty_or_damage
UPDATE raw_messages rm
SET status = 'pending'::message_status,
    match_result = NULL,
    error_message = NULL, processing_claim_stage = NULL,
    processing_claimed_at = NULL, processing_claimed_by = NULL
WHERE rm.id = (SELECT raw_message_id FROM air_violations WHERE id = 977)
  AND rm.status NOT IN ('materialized'::message_status, 'duplicate'::message_status)
  AND NOT EXISTS (SELECT 1 FROM incidents i
                  WHERE i.raw_message_id = rm.id AND i.is_deleted = false);
DELETE FROM air_violations WHERE id = 977
  AND review_status = 'flagged_for_review' AND review_reason = 'excluded_kinetic_casualty_or_damage';
-- air_violation_id=978 reason=excluded_kinetic_casualty_or_damage
UPDATE raw_messages rm
SET status = 'pending'::message_status,
    match_result = NULL,
    error_message = NULL, processing_claim_stage = NULL,
    processing_claimed_at = NULL, processing_claimed_by = NULL
WHERE rm.id = (SELECT raw_message_id FROM air_violations WHERE id = 978)
  AND rm.status NOT IN ('materialized'::message_status, 'duplicate'::message_status)
  AND NOT EXISTS (SELECT 1 FROM incidents i
                  WHERE i.raw_message_id = rm.id AND i.is_deleted = false);
DELETE FROM air_violations WHERE id = 978
  AND review_status = 'flagged_for_review' AND review_reason = 'excluded_kinetic_casualty_or_damage';
-- air_violation_id=979 reason=excluded_kinetic_casualty_or_damage
UPDATE raw_messages rm
SET status = 'pending'::message_status,
    match_result = NULL,
    error_message = NULL, processing_claim_stage = NULL,
    processing_claimed_at = NULL, processing_claimed_by = NULL
WHERE rm.id = (SELECT raw_message_id FROM air_violations WHERE id = 979)
  AND rm.status NOT IN ('materialized'::message_status, 'duplicate'::message_status)
  AND NOT EXISTS (SELECT 1 FROM incidents i
                  WHERE i.raw_message_id = rm.id AND i.is_deleted = false);
DELETE FROM air_violations WHERE id = 979
  AND review_status = 'flagged_for_review' AND review_reason = 'excluded_kinetic_casualty_or_damage';
-- air_violation_id=980 reason=excluded_kinetic_casualty_or_damage
UPDATE raw_messages rm
SET status = 'pending'::message_status,
    match_result = NULL,
    error_message = NULL, processing_claim_stage = NULL,
    processing_claimed_at = NULL, processing_claimed_by = NULL
WHERE rm.id = (SELECT raw_message_id FROM air_violations WHERE id = 980)
  AND rm.status NOT IN ('materialized'::message_status, 'duplicate'::message_status)
  AND NOT EXISTS (SELECT 1 FROM incidents i
                  WHERE i.raw_message_id = rm.id AND i.is_deleted = false);
DELETE FROM air_violations WHERE id = 980
  AND review_status = 'flagged_for_review' AND review_reason = 'excluded_kinetic_casualty_or_damage';
-- air_violation_id=981 reason=excluded_kinetic_casualty_or_damage
UPDATE raw_messages rm
SET status = 'pending'::message_status,
    match_result = NULL,
    error_message = NULL, processing_claim_stage = NULL,
    processing_claimed_at = NULL, processing_claimed_by = NULL
WHERE rm.id = (SELECT raw_message_id FROM air_violations WHERE id = 981)
  AND rm.status NOT IN ('materialized'::message_status, 'duplicate'::message_status)
  AND NOT EXISTS (SELECT 1 FROM incidents i
                  WHERE i.raw_message_id = rm.id AND i.is_deleted = false);
DELETE FROM air_violations WHERE id = 981
  AND review_status = 'flagged_for_review' AND review_reason = 'excluded_kinetic_casualty_or_damage';
-- air_violation_id=982 reason=excluded_kinetic_casualty_or_damage
UPDATE raw_messages rm
SET status = 'pending'::message_status,
    match_result = NULL,
    error_message = NULL, processing_claim_stage = NULL,
    processing_claimed_at = NULL, processing_claimed_by = NULL
WHERE rm.id = (SELECT raw_message_id FROM air_violations WHERE id = 982)
  AND rm.status NOT IN ('materialized'::message_status, 'duplicate'::message_status)
  AND NOT EXISTS (SELECT 1 FROM incidents i
                  WHERE i.raw_message_id = rm.id AND i.is_deleted = false);
DELETE FROM air_violations WHERE id = 982
  AND review_status = 'flagged_for_review' AND review_reason = 'excluded_kinetic_casualty_or_damage';
-- air_violation_id=983 reason=excluded_kinetic_casualty_or_damage
UPDATE raw_messages rm
SET status = 'pending'::message_status,
    match_result = NULL,
    error_message = NULL, processing_claim_stage = NULL,
    processing_claimed_at = NULL, processing_claimed_by = NULL
WHERE rm.id = (SELECT raw_message_id FROM air_violations WHERE id = 983)
  AND rm.status NOT IN ('materialized'::message_status, 'duplicate'::message_status)
  AND NOT EXISTS (SELECT 1 FROM incidents i
                  WHERE i.raw_message_id = rm.id AND i.is_deleted = false);
DELETE FROM air_violations WHERE id = 983
  AND review_status = 'flagged_for_review' AND review_reason = 'excluded_kinetic_casualty_or_damage';
-- air_violation_id=984 reason=excluded_kinetic_casualty_or_damage
UPDATE raw_messages rm
SET status = 'pending'::message_status,
    match_result = NULL,
    error_message = NULL, processing_claim_stage = NULL,
    processing_claimed_at = NULL, processing_claimed_by = NULL
WHERE rm.id = (SELECT raw_message_id FROM air_violations WHERE id = 984)
  AND rm.status NOT IN ('materialized'::message_status, 'duplicate'::message_status)
  AND NOT EXISTS (SELECT 1 FROM incidents i
                  WHERE i.raw_message_id = rm.id AND i.is_deleted = false);
DELETE FROM air_violations WHERE id = 984
  AND review_status = 'flagged_for_review' AND review_reason = 'excluded_kinetic_casualty_or_damage';
-- air_violation_id=985 reason=excluded_kinetic_casualty_or_damage
UPDATE raw_messages rm
SET status = 'pending'::message_status,
    match_result = NULL,
    error_message = NULL, processing_claim_stage = NULL,
    processing_claimed_at = NULL, processing_claimed_by = NULL
WHERE rm.id = (SELECT raw_message_id FROM air_violations WHERE id = 985)
  AND rm.status NOT IN ('materialized'::message_status, 'duplicate'::message_status)
  AND NOT EXISTS (SELECT 1 FROM incidents i
                  WHERE i.raw_message_id = rm.id AND i.is_deleted = false);
DELETE FROM air_violations WHERE id = 985
  AND review_status = 'flagged_for_review' AND review_reason = 'excluded_kinetic_casualty_or_damage';
-- air_violation_id=986 reason=excluded_kinetic_casualty_or_damage
UPDATE raw_messages rm
SET status = 'pending'::message_status,
    match_result = NULL,
    error_message = NULL, processing_claim_stage = NULL,
    processing_claimed_at = NULL, processing_claimed_by = NULL
WHERE rm.id = (SELECT raw_message_id FROM air_violations WHERE id = 986)
  AND rm.status NOT IN ('materialized'::message_status, 'duplicate'::message_status)
  AND NOT EXISTS (SELECT 1 FROM incidents i
                  WHERE i.raw_message_id = rm.id AND i.is_deleted = false);
DELETE FROM air_violations WHERE id = 986
  AND review_status = 'flagged_for_review' AND review_reason = 'excluded_kinetic_casualty_or_damage';
-- air_violation_id=987 reason=excluded_kinetic_casualty_or_damage
UPDATE raw_messages rm
SET status = 'pending'::message_status,
    match_result = NULL,
    error_message = NULL, processing_claim_stage = NULL,
    processing_claimed_at = NULL, processing_claimed_by = NULL
WHERE rm.id = (SELECT raw_message_id FROM air_violations WHERE id = 987)
  AND rm.status NOT IN ('materialized'::message_status, 'duplicate'::message_status)
  AND NOT EXISTS (SELECT 1 FROM incidents i
                  WHERE i.raw_message_id = rm.id AND i.is_deleted = false);
DELETE FROM air_violations WHERE id = 987
  AND review_status = 'flagged_for_review' AND review_reason = 'excluded_kinetic_casualty_or_damage';
-- air_violation_id=988 reason=excluded_kinetic_casualty_or_damage
UPDATE raw_messages rm
SET status = 'pending'::message_status,
    match_result = NULL,
    error_message = NULL, processing_claim_stage = NULL,
    processing_claimed_at = NULL, processing_claimed_by = NULL
WHERE rm.id = (SELECT raw_message_id FROM air_violations WHERE id = 988)
  AND rm.status NOT IN ('materialized'::message_status, 'duplicate'::message_status)
  AND NOT EXISTS (SELECT 1 FROM incidents i
                  WHERE i.raw_message_id = rm.id AND i.is_deleted = false);
DELETE FROM air_violations WHERE id = 988
  AND review_status = 'flagged_for_review' AND review_reason = 'excluded_kinetic_casualty_or_damage';
-- air_violation_id=989 reason=excluded_kinetic_casualty_or_damage
UPDATE raw_messages rm
SET status = 'pending'::message_status,
    match_result = NULL,
    error_message = NULL, processing_claim_stage = NULL,
    processing_claimed_at = NULL, processing_claimed_by = NULL
WHERE rm.id = (SELECT raw_message_id FROM air_violations WHERE id = 989)
  AND rm.status NOT IN ('materialized'::message_status, 'duplicate'::message_status)
  AND NOT EXISTS (SELECT 1 FROM incidents i
                  WHERE i.raw_message_id = rm.id AND i.is_deleted = false);
DELETE FROM air_violations WHERE id = 989
  AND review_status = 'flagged_for_review' AND review_reason = 'excluded_kinetic_casualty_or_damage';
-- air_violation_id=990 reason=excluded_kinetic_casualty_or_damage
UPDATE raw_messages rm
SET status = 'pending'::message_status,
    match_result = NULL,
    error_message = NULL, processing_claim_stage = NULL,
    processing_claimed_at = NULL, processing_claimed_by = NULL
WHERE rm.id = (SELECT raw_message_id FROM air_violations WHERE id = 990)
  AND rm.status NOT IN ('materialized'::message_status, 'duplicate'::message_status)
  AND NOT EXISTS (SELECT 1 FROM incidents i
                  WHERE i.raw_message_id = rm.id AND i.is_deleted = false);
DELETE FROM air_violations WHERE id = 990
  AND review_status = 'flagged_for_review' AND review_reason = 'excluded_kinetic_casualty_or_damage';
-- air_violation_id=991 reason=excluded_kinetic_casualty_or_damage
UPDATE raw_messages rm
SET status = 'pending'::message_status,
    match_result = NULL,
    error_message = NULL, processing_claim_stage = NULL,
    processing_claimed_at = NULL, processing_claimed_by = NULL
WHERE rm.id = (SELECT raw_message_id FROM air_violations WHERE id = 991)
  AND rm.status NOT IN ('materialized'::message_status, 'duplicate'::message_status)
  AND NOT EXISTS (SELECT 1 FROM incidents i
                  WHERE i.raw_message_id = rm.id AND i.is_deleted = false);
DELETE FROM air_violations WHERE id = 991
  AND review_status = 'flagged_for_review' AND review_reason = 'excluded_kinetic_casualty_or_damage';
-- air_violation_id=992 reason=excluded_kinetic_casualty_or_damage
UPDATE raw_messages rm
SET status = 'pending'::message_status,
    match_result = NULL,
    error_message = NULL, processing_claim_stage = NULL,
    processing_claimed_at = NULL, processing_claimed_by = NULL
WHERE rm.id = (SELECT raw_message_id FROM air_violations WHERE id = 992)
  AND rm.status NOT IN ('materialized'::message_status, 'duplicate'::message_status)
  AND NOT EXISTS (SELECT 1 FROM incidents i
                  WHERE i.raw_message_id = rm.id AND i.is_deleted = false);
DELETE FROM air_violations WHERE id = 992
  AND review_status = 'flagged_for_review' AND review_reason = 'excluded_kinetic_casualty_or_damage';
-- air_violation_id=993 reason=excluded_kinetic_casualty_or_damage
UPDATE raw_messages rm
SET status = 'pending'::message_status,
    match_result = NULL,
    error_message = NULL, processing_claim_stage = NULL,
    processing_claimed_at = NULL, processing_claimed_by = NULL
WHERE rm.id = (SELECT raw_message_id FROM air_violations WHERE id = 993)
  AND rm.status NOT IN ('materialized'::message_status, 'duplicate'::message_status)
  AND NOT EXISTS (SELECT 1 FROM incidents i
                  WHERE i.raw_message_id = rm.id AND i.is_deleted = false);
DELETE FROM air_violations WHERE id = 993
  AND review_status = 'flagged_for_review' AND review_reason = 'excluded_kinetic_casualty_or_damage';
-- air_violation_id=994 reason=excluded_kinetic_casualty_or_damage
UPDATE raw_messages rm
SET status = 'pending'::message_status,
    match_result = NULL,
    error_message = NULL, processing_claim_stage = NULL,
    processing_claimed_at = NULL, processing_claimed_by = NULL
WHERE rm.id = (SELECT raw_message_id FROM air_violations WHERE id = 994)
  AND rm.status NOT IN ('materialized'::message_status, 'duplicate'::message_status)
  AND NOT EXISTS (SELECT 1 FROM incidents i
                  WHERE i.raw_message_id = rm.id AND i.is_deleted = false);
DELETE FROM air_violations WHERE id = 994
  AND review_status = 'flagged_for_review' AND review_reason = 'excluded_kinetic_casualty_or_damage';
-- air_violation_id=996 reason=excluded_kinetic_casualty_or_damage
UPDATE raw_messages rm
SET status = 'pending'::message_status,
    match_result = NULL,
    error_message = NULL, processing_claim_stage = NULL,
    processing_claimed_at = NULL, processing_claimed_by = NULL
WHERE rm.id = (SELECT raw_message_id FROM air_violations WHERE id = 996)
  AND rm.status NOT IN ('materialized'::message_status, 'duplicate'::message_status)
  AND NOT EXISTS (SELECT 1 FROM incidents i
                  WHERE i.raw_message_id = rm.id AND i.is_deleted = false);
DELETE FROM air_violations WHERE id = 996
  AND review_status = 'flagged_for_review' AND review_reason = 'excluded_kinetic_casualty_or_damage';
-- air_violation_id=997 reason=excluded_kinetic_casualty_or_damage
UPDATE raw_messages rm
SET status = 'pending'::message_status,
    match_result = NULL,
    error_message = NULL, processing_claim_stage = NULL,
    processing_claimed_at = NULL, processing_claimed_by = NULL
WHERE rm.id = (SELECT raw_message_id FROM air_violations WHERE id = 997)
  AND rm.status NOT IN ('materialized'::message_status, 'duplicate'::message_status)
  AND NOT EXISTS (SELECT 1 FROM incidents i
                  WHERE i.raw_message_id = rm.id AND i.is_deleted = false);
DELETE FROM air_violations WHERE id = 997
  AND review_status = 'flagged_for_review' AND review_reason = 'excluded_kinetic_casualty_or_damage';
-- air_violation_id=998 reason=excluded_kinetic_casualty_or_damage
UPDATE raw_messages rm
SET status = 'pending'::message_status,
    match_result = NULL,
    error_message = NULL, processing_claim_stage = NULL,
    processing_claimed_at = NULL, processing_claimed_by = NULL
WHERE rm.id = (SELECT raw_message_id FROM air_violations WHERE id = 998)
  AND rm.status NOT IN ('materialized'::message_status, 'duplicate'::message_status)
  AND NOT EXISTS (SELECT 1 FROM incidents i
                  WHERE i.raw_message_id = rm.id AND i.is_deleted = false);
DELETE FROM air_violations WHERE id = 998
  AND review_status = 'flagged_for_review' AND review_reason = 'excluded_kinetic_casualty_or_damage';
-- air_violation_id=999 reason=excluded_kinetic_casualty_or_damage
UPDATE raw_messages rm
SET status = 'pending'::message_status,
    match_result = NULL,
    error_message = NULL, processing_claim_stage = NULL,
    processing_claimed_at = NULL, processing_claimed_by = NULL
WHERE rm.id = (SELECT raw_message_id FROM air_violations WHERE id = 999)
  AND rm.status NOT IN ('materialized'::message_status, 'duplicate'::message_status)
  AND NOT EXISTS (SELECT 1 FROM incidents i
                  WHERE i.raw_message_id = rm.id AND i.is_deleted = false);
DELETE FROM air_violations WHERE id = 999
  AND review_status = 'flagged_for_review' AND review_reason = 'excluded_kinetic_casualty_or_damage';
-- air_violation_id=1000 reason=excluded_kinetic_casualty_or_damage
UPDATE raw_messages rm
SET status = 'pending'::message_status,
    match_result = NULL,
    error_message = NULL, processing_claim_stage = NULL,
    processing_claimed_at = NULL, processing_claimed_by = NULL
WHERE rm.id = (SELECT raw_message_id FROM air_violations WHERE id = 1000)
  AND rm.status NOT IN ('materialized'::message_status, 'duplicate'::message_status)
  AND NOT EXISTS (SELECT 1 FROM incidents i
                  WHERE i.raw_message_id = rm.id AND i.is_deleted = false);
DELETE FROM air_violations WHERE id = 1000
  AND review_status = 'flagged_for_review' AND review_reason = 'excluded_kinetic_casualty_or_damage';
-- air_violation_id=1003 reason=excluded_kinetic_casualty_or_damage
UPDATE raw_messages rm
SET status = 'pending'::message_status,
    match_result = NULL,
    error_message = NULL, processing_claim_stage = NULL,
    processing_claimed_at = NULL, processing_claimed_by = NULL
WHERE rm.id = (SELECT raw_message_id FROM air_violations WHERE id = 1003)
  AND rm.status NOT IN ('materialized'::message_status, 'duplicate'::message_status)
  AND NOT EXISTS (SELECT 1 FROM incidents i
                  WHERE i.raw_message_id = rm.id AND i.is_deleted = false);
DELETE FROM air_violations WHERE id = 1003
  AND review_status = 'flagged_for_review' AND review_reason = 'excluded_kinetic_casualty_or_damage';
-- air_violation_id=1007 reason=excluded_kinetic_casualty_or_damage
UPDATE raw_messages rm
SET status = 'pending'::message_status,
    match_result = NULL,
    error_message = NULL, processing_claim_stage = NULL,
    processing_claimed_at = NULL, processing_claimed_by = NULL
WHERE rm.id = (SELECT raw_message_id FROM air_violations WHERE id = 1007)
  AND rm.status NOT IN ('materialized'::message_status, 'duplicate'::message_status)
  AND NOT EXISTS (SELECT 1 FROM incidents i
                  WHERE i.raw_message_id = rm.id AND i.is_deleted = false);
DELETE FROM air_violations WHERE id = 1007
  AND review_status = 'flagged_for_review' AND review_reason = 'excluded_kinetic_casualty_or_damage';
-- air_violation_id=1009 reason=excluded_kinetic_casualty_or_damage
UPDATE raw_messages rm
SET status = 'pending'::message_status,
    match_result = NULL,
    error_message = NULL, processing_claim_stage = NULL,
    processing_claimed_at = NULL, processing_claimed_by = NULL
WHERE rm.id = (SELECT raw_message_id FROM air_violations WHERE id = 1009)
  AND rm.status NOT IN ('materialized'::message_status, 'duplicate'::message_status)
  AND NOT EXISTS (SELECT 1 FROM incidents i
                  WHERE i.raw_message_id = rm.id AND i.is_deleted = false);
DELETE FROM air_violations WHERE id = 1009
  AND review_status = 'flagged_for_review' AND review_reason = 'excluded_kinetic_casualty_or_damage';
-- air_violation_id=1459 reason=excluded_kinetic_casualty_or_damage
UPDATE raw_messages rm
SET status = 'pending'::message_status,
    match_result = NULL,
    error_message = NULL, processing_claim_stage = NULL,
    processing_claimed_at = NULL, processing_claimed_by = NULL
WHERE rm.id = (SELECT raw_message_id FROM air_violations WHERE id = 1459)
  AND rm.status NOT IN ('materialized'::message_status, 'duplicate'::message_status)
  AND NOT EXISTS (SELECT 1 FROM incidents i
                  WHERE i.raw_message_id = rm.id AND i.is_deleted = false);
DELETE FROM air_violations WHERE id = 1459
  AND review_status = 'flagged_for_review' AND review_reason = 'excluded_kinetic_casualty_or_damage';
-- air_violation_id=1460 reason=excluded_kinetic_casualty_or_damage
UPDATE raw_messages rm
SET status = 'pending'::message_status,
    match_result = NULL,
    error_message = NULL, processing_claim_stage = NULL,
    processing_claimed_at = NULL, processing_claimed_by = NULL
WHERE rm.id = (SELECT raw_message_id FROM air_violations WHERE id = 1460)
  AND rm.status NOT IN ('materialized'::message_status, 'duplicate'::message_status)
  AND NOT EXISTS (SELECT 1 FROM incidents i
                  WHERE i.raw_message_id = rm.id AND i.is_deleted = false);
DELETE FROM air_violations WHERE id = 1460
  AND review_status = 'flagged_for_review' AND review_reason = 'excluded_kinetic_casualty_or_damage';
-- air_violation_id=1461 reason=excluded_kinetic_casualty_or_damage
UPDATE raw_messages rm
SET status = 'pending'::message_status,
    match_result = NULL,
    error_message = NULL, processing_claim_stage = NULL,
    processing_claimed_at = NULL, processing_claimed_by = NULL
WHERE rm.id = (SELECT raw_message_id FROM air_violations WHERE id = 1461)
  AND rm.status NOT IN ('materialized'::message_status, 'duplicate'::message_status)
  AND NOT EXISTS (SELECT 1 FROM incidents i
                  WHERE i.raw_message_id = rm.id AND i.is_deleted = false);
DELETE FROM air_violations WHERE id = 1461
  AND review_status = 'flagged_for_review' AND review_reason = 'excluded_kinetic_casualty_or_damage';
-- air_violation_id=1462 reason=excluded_kinetic_casualty_or_damage
UPDATE raw_messages rm
SET status = 'pending'::message_status,
    match_result = NULL,
    error_message = NULL, processing_claim_stage = NULL,
    processing_claimed_at = NULL, processing_claimed_by = NULL
WHERE rm.id = (SELECT raw_message_id FROM air_violations WHERE id = 1462)
  AND rm.status NOT IN ('materialized'::message_status, 'duplicate'::message_status)
  AND NOT EXISTS (SELECT 1 FROM incidents i
                  WHERE i.raw_message_id = rm.id AND i.is_deleted = false);
DELETE FROM air_violations WHERE id = 1462
  AND review_status = 'flagged_for_review' AND review_reason = 'excluded_kinetic_casualty_or_damage';
-- air_violation_id=1464 reason=excluded_kinetic_casualty_or_damage
UPDATE raw_messages rm
SET status = 'pending'::message_status,
    match_result = NULL,
    error_message = NULL, processing_claim_stage = NULL,
    processing_claimed_at = NULL, processing_claimed_by = NULL
WHERE rm.id = (SELECT raw_message_id FROM air_violations WHERE id = 1464)
  AND rm.status NOT IN ('materialized'::message_status, 'duplicate'::message_status)
  AND NOT EXISTS (SELECT 1 FROM incidents i
                  WHERE i.raw_message_id = rm.id AND i.is_deleted = false);
DELETE FROM air_violations WHERE id = 1464
  AND review_status = 'flagged_for_review' AND review_reason = 'excluded_kinetic_casualty_or_damage';
-- air_violation_id=1465 reason=excluded_kinetic_casualty_or_damage
UPDATE raw_messages rm
SET status = 'pending'::message_status,
    match_result = NULL,
    error_message = NULL, processing_claim_stage = NULL,
    processing_claimed_at = NULL, processing_claimed_by = NULL
WHERE rm.id = (SELECT raw_message_id FROM air_violations WHERE id = 1465)
  AND rm.status NOT IN ('materialized'::message_status, 'duplicate'::message_status)
  AND NOT EXISTS (SELECT 1 FROM incidents i
                  WHERE i.raw_message_id = rm.id AND i.is_deleted = false);
DELETE FROM air_violations WHERE id = 1465
  AND review_status = 'flagged_for_review' AND review_reason = 'excluded_kinetic_casualty_or_damage';
-- air_violation_id=1466 reason=excluded_kinetic_casualty_or_damage
UPDATE raw_messages rm
SET status = 'pending'::message_status,
    match_result = NULL,
    error_message = NULL, processing_claim_stage = NULL,
    processing_claimed_at = NULL, processing_claimed_by = NULL
WHERE rm.id = (SELECT raw_message_id FROM air_violations WHERE id = 1466)
  AND rm.status NOT IN ('materialized'::message_status, 'duplicate'::message_status)
  AND NOT EXISTS (SELECT 1 FROM incidents i
                  WHERE i.raw_message_id = rm.id AND i.is_deleted = false);
DELETE FROM air_violations WHERE id = 1466
  AND review_status = 'flagged_for_review' AND review_reason = 'excluded_kinetic_casualty_or_damage';
-- air_violation_id=1467 reason=excluded_kinetic_casualty_or_damage
UPDATE raw_messages rm
SET status = 'pending'::message_status,
    match_result = NULL,
    error_message = NULL, processing_claim_stage = NULL,
    processing_claimed_at = NULL, processing_claimed_by = NULL
WHERE rm.id = (SELECT raw_message_id FROM air_violations WHERE id = 1467)
  AND rm.status NOT IN ('materialized'::message_status, 'duplicate'::message_status)
  AND NOT EXISTS (SELECT 1 FROM incidents i
                  WHERE i.raw_message_id = rm.id AND i.is_deleted = false);
DELETE FROM air_violations WHERE id = 1467
  AND review_status = 'flagged_for_review' AND review_reason = 'excluded_kinetic_casualty_or_damage';
-- air_violation_id=1468 reason=excluded_kinetic_casualty_or_damage
UPDATE raw_messages rm
SET status = 'pending'::message_status,
    match_result = NULL,
    error_message = NULL, processing_claim_stage = NULL,
    processing_claimed_at = NULL, processing_claimed_by = NULL
WHERE rm.id = (SELECT raw_message_id FROM air_violations WHERE id = 1468)
  AND rm.status NOT IN ('materialized'::message_status, 'duplicate'::message_status)
  AND NOT EXISTS (SELECT 1 FROM incidents i
                  WHERE i.raw_message_id = rm.id AND i.is_deleted = false);
DELETE FROM air_violations WHERE id = 1468
  AND review_status = 'flagged_for_review' AND review_reason = 'excluded_kinetic_casualty_or_damage';
-- air_violation_id=1469 reason=excluded_kinetic_casualty_or_damage
UPDATE raw_messages rm
SET status = 'pending'::message_status,
    match_result = NULL,
    error_message = NULL, processing_claim_stage = NULL,
    processing_claimed_at = NULL, processing_claimed_by = NULL
WHERE rm.id = (SELECT raw_message_id FROM air_violations WHERE id = 1469)
  AND rm.status NOT IN ('materialized'::message_status, 'duplicate'::message_status)
  AND NOT EXISTS (SELECT 1 FROM incidents i
                  WHERE i.raw_message_id = rm.id AND i.is_deleted = false);
DELETE FROM air_violations WHERE id = 1469
  AND review_status = 'flagged_for_review' AND review_reason = 'excluded_kinetic_casualty_or_damage';
-- air_violation_id=1470 reason=excluded_kinetic_casualty_or_damage
UPDATE raw_messages rm
SET status = 'pending'::message_status,
    match_result = NULL,
    error_message = NULL, processing_claim_stage = NULL,
    processing_claimed_at = NULL, processing_claimed_by = NULL
WHERE rm.id = (SELECT raw_message_id FROM air_violations WHERE id = 1470)
  AND rm.status NOT IN ('materialized'::message_status, 'duplicate'::message_status)
  AND NOT EXISTS (SELECT 1 FROM incidents i
                  WHERE i.raw_message_id = rm.id AND i.is_deleted = false);
DELETE FROM air_violations WHERE id = 1470
  AND review_status = 'flagged_for_review' AND review_reason = 'excluded_kinetic_casualty_or_damage';
-- air_violation_id=1471 reason=excluded_kinetic_casualty_or_damage
UPDATE raw_messages rm
SET status = 'pending'::message_status,
    match_result = NULL,
    error_message = NULL, processing_claim_stage = NULL,
    processing_claimed_at = NULL, processing_claimed_by = NULL
WHERE rm.id = (SELECT raw_message_id FROM air_violations WHERE id = 1471)
  AND rm.status NOT IN ('materialized'::message_status, 'duplicate'::message_status)
  AND NOT EXISTS (SELECT 1 FROM incidents i
                  WHERE i.raw_message_id = rm.id AND i.is_deleted = false);
DELETE FROM air_violations WHERE id = 1471
  AND review_status = 'flagged_for_review' AND review_reason = 'excluded_kinetic_casualty_or_damage';
-- air_violation_id=1472 reason=excluded_kinetic_casualty_or_damage
UPDATE raw_messages rm
SET status = 'pending'::message_status,
    match_result = NULL,
    error_message = NULL, processing_claim_stage = NULL,
    processing_claimed_at = NULL, processing_claimed_by = NULL
WHERE rm.id = (SELECT raw_message_id FROM air_violations WHERE id = 1472)
  AND rm.status NOT IN ('materialized'::message_status, 'duplicate'::message_status)
  AND NOT EXISTS (SELECT 1 FROM incidents i
                  WHERE i.raw_message_id = rm.id AND i.is_deleted = false);
DELETE FROM air_violations WHERE id = 1472
  AND review_status = 'flagged_for_review' AND review_reason = 'excluded_kinetic_casualty_or_damage';
-- air_violation_id=1473 reason=excluded_kinetic_casualty_or_damage
UPDATE raw_messages rm
SET status = 'pending'::message_status,
    match_result = NULL,
    error_message = NULL, processing_claim_stage = NULL,
    processing_claimed_at = NULL, processing_claimed_by = NULL
WHERE rm.id = (SELECT raw_message_id FROM air_violations WHERE id = 1473)
  AND rm.status NOT IN ('materialized'::message_status, 'duplicate'::message_status)
  AND NOT EXISTS (SELECT 1 FROM incidents i
                  WHERE i.raw_message_id = rm.id AND i.is_deleted = false);
DELETE FROM air_violations WHERE id = 1473
  AND review_status = 'flagged_for_review' AND review_reason = 'excluded_kinetic_casualty_or_damage';
-- air_violation_id=1474 reason=excluded_kinetic_casualty_or_damage
UPDATE raw_messages rm
SET status = 'pending'::message_status,
    match_result = NULL,
    error_message = NULL, processing_claim_stage = NULL,
    processing_claimed_at = NULL, processing_claimed_by = NULL
WHERE rm.id = (SELECT raw_message_id FROM air_violations WHERE id = 1474)
  AND rm.status NOT IN ('materialized'::message_status, 'duplicate'::message_status)
  AND NOT EXISTS (SELECT 1 FROM incidents i
                  WHERE i.raw_message_id = rm.id AND i.is_deleted = false);
DELETE FROM air_violations WHERE id = 1474
  AND review_status = 'flagged_for_review' AND review_reason = 'excluded_kinetic_casualty_or_damage';
-- air_violation_id=1475 reason=excluded_kinetic_casualty_or_damage
UPDATE raw_messages rm
SET status = 'pending'::message_status,
    match_result = NULL,
    error_message = NULL, processing_claim_stage = NULL,
    processing_claimed_at = NULL, processing_claimed_by = NULL
WHERE rm.id = (SELECT raw_message_id FROM air_violations WHERE id = 1475)
  AND rm.status NOT IN ('materialized'::message_status, 'duplicate'::message_status)
  AND NOT EXISTS (SELECT 1 FROM incidents i
                  WHERE i.raw_message_id = rm.id AND i.is_deleted = false);
DELETE FROM air_violations WHERE id = 1475
  AND review_status = 'flagged_for_review' AND review_reason = 'excluded_kinetic_casualty_or_damage';
-- air_violation_id=1476 reason=excluded_kinetic_casualty_or_damage
UPDATE raw_messages rm
SET status = 'pending'::message_status,
    match_result = NULL,
    error_message = NULL, processing_claim_stage = NULL,
    processing_claimed_at = NULL, processing_claimed_by = NULL
WHERE rm.id = (SELECT raw_message_id FROM air_violations WHERE id = 1476)
  AND rm.status NOT IN ('materialized'::message_status, 'duplicate'::message_status)
  AND NOT EXISTS (SELECT 1 FROM incidents i
                  WHERE i.raw_message_id = rm.id AND i.is_deleted = false);
DELETE FROM air_violations WHERE id = 1476
  AND review_status = 'flagged_for_review' AND review_reason = 'excluded_kinetic_casualty_or_damage';
-- air_violation_id=1477 reason=excluded_kinetic_casualty_or_damage
UPDATE raw_messages rm
SET status = 'pending'::message_status,
    match_result = NULL,
    error_message = NULL, processing_claim_stage = NULL,
    processing_claimed_at = NULL, processing_claimed_by = NULL
WHERE rm.id = (SELECT raw_message_id FROM air_violations WHERE id = 1477)
  AND rm.status NOT IN ('materialized'::message_status, 'duplicate'::message_status)
  AND NOT EXISTS (SELECT 1 FROM incidents i
                  WHERE i.raw_message_id = rm.id AND i.is_deleted = false);
DELETE FROM air_violations WHERE id = 1477
  AND review_status = 'flagged_for_review' AND review_reason = 'excluded_kinetic_casualty_or_damage';
-- air_violation_id=1478 reason=excluded_kinetic_casualty_or_damage
UPDATE raw_messages rm
SET status = 'pending'::message_status,
    match_result = NULL,
    error_message = NULL, processing_claim_stage = NULL,
    processing_claimed_at = NULL, processing_claimed_by = NULL
WHERE rm.id = (SELECT raw_message_id FROM air_violations WHERE id = 1478)
  AND rm.status NOT IN ('materialized'::message_status, 'duplicate'::message_status)
  AND NOT EXISTS (SELECT 1 FROM incidents i
                  WHERE i.raw_message_id = rm.id AND i.is_deleted = false);
DELETE FROM air_violations WHERE id = 1478
  AND review_status = 'flagged_for_review' AND review_reason = 'excluded_kinetic_casualty_or_damage';
-- air_violation_id=1479 reason=excluded_kinetic_casualty_or_damage
UPDATE raw_messages rm
SET status = 'pending'::message_status,
    match_result = NULL,
    error_message = NULL, processing_claim_stage = NULL,
    processing_claimed_at = NULL, processing_claimed_by = NULL
WHERE rm.id = (SELECT raw_message_id FROM air_violations WHERE id = 1479)
  AND rm.status NOT IN ('materialized'::message_status, 'duplicate'::message_status)
  AND NOT EXISTS (SELECT 1 FROM incidents i
                  WHERE i.raw_message_id = rm.id AND i.is_deleted = false);
DELETE FROM air_violations WHERE id = 1479
  AND review_status = 'flagged_for_review' AND review_reason = 'excluded_kinetic_casualty_or_damage';
-- air_violation_id=1480 reason=excluded_kinetic_casualty_or_damage
UPDATE raw_messages rm
SET status = 'pending'::message_status,
    match_result = NULL,
    error_message = NULL, processing_claim_stage = NULL,
    processing_claimed_at = NULL, processing_claimed_by = NULL
WHERE rm.id = (SELECT raw_message_id FROM air_violations WHERE id = 1480)
  AND rm.status NOT IN ('materialized'::message_status, 'duplicate'::message_status)
  AND NOT EXISTS (SELECT 1 FROM incidents i
                  WHERE i.raw_message_id = rm.id AND i.is_deleted = false);
DELETE FROM air_violations WHERE id = 1480
  AND review_status = 'flagged_for_review' AND review_reason = 'excluded_kinetic_casualty_or_damage';
-- air_violation_id=1481 reason=excluded_kinetic_casualty_or_damage
UPDATE raw_messages rm
SET status = 'pending'::message_status,
    match_result = NULL,
    error_message = NULL, processing_claim_stage = NULL,
    processing_claimed_at = NULL, processing_claimed_by = NULL
WHERE rm.id = (SELECT raw_message_id FROM air_violations WHERE id = 1481)
  AND rm.status NOT IN ('materialized'::message_status, 'duplicate'::message_status)
  AND NOT EXISTS (SELECT 1 FROM incidents i
                  WHERE i.raw_message_id = rm.id AND i.is_deleted = false);
DELETE FROM air_violations WHERE id = 1481
  AND review_status = 'flagged_for_review' AND review_reason = 'excluded_kinetic_casualty_or_damage';
-- air_violation_id=1485 reason=excluded_kinetic_casualty_or_damage
UPDATE raw_messages rm
SET status = 'pending'::message_status,
    match_result = NULL,
    error_message = NULL, processing_claim_stage = NULL,
    processing_claimed_at = NULL, processing_claimed_by = NULL
WHERE rm.id = (SELECT raw_message_id FROM air_violations WHERE id = 1485)
  AND rm.status NOT IN ('materialized'::message_status, 'duplicate'::message_status)
  AND NOT EXISTS (SELECT 1 FROM incidents i
                  WHERE i.raw_message_id = rm.id AND i.is_deleted = false);
DELETE FROM air_violations WHERE id = 1485
  AND review_status = 'flagged_for_review' AND review_reason = 'excluded_kinetic_casualty_or_damage';
-- air_violation_id=1486 reason=excluded_kinetic_casualty_or_damage
UPDATE raw_messages rm
SET status = 'pending'::message_status,
    match_result = NULL,
    error_message = NULL, processing_claim_stage = NULL,
    processing_claimed_at = NULL, processing_claimed_by = NULL
WHERE rm.id = (SELECT raw_message_id FROM air_violations WHERE id = 1486)
  AND rm.status NOT IN ('materialized'::message_status, 'duplicate'::message_status)
  AND NOT EXISTS (SELECT 1 FROM incidents i
                  WHERE i.raw_message_id = rm.id AND i.is_deleted = false);
DELETE FROM air_violations WHERE id = 1486
  AND review_status = 'flagged_for_review' AND review_reason = 'excluded_kinetic_casualty_or_damage';
-- air_violation_id=1487 reason=excluded_kinetic_casualty_or_damage
UPDATE raw_messages rm
SET status = 'pending'::message_status,
    match_result = NULL,
    error_message = NULL, processing_claim_stage = NULL,
    processing_claimed_at = NULL, processing_claimed_by = NULL
WHERE rm.id = (SELECT raw_message_id FROM air_violations WHERE id = 1487)
  AND rm.status NOT IN ('materialized'::message_status, 'duplicate'::message_status)
  AND NOT EXISTS (SELECT 1 FROM incidents i
                  WHERE i.raw_message_id = rm.id AND i.is_deleted = false);
DELETE FROM air_violations WHERE id = 1487
  AND review_status = 'flagged_for_review' AND review_reason = 'excluded_kinetic_casualty_or_damage';
-- air_violation_id=1488 reason=excluded_kinetic_casualty_or_damage
UPDATE raw_messages rm
SET status = 'pending'::message_status,
    match_result = NULL,
    error_message = NULL, processing_claim_stage = NULL,
    processing_claimed_at = NULL, processing_claimed_by = NULL
WHERE rm.id = (SELECT raw_message_id FROM air_violations WHERE id = 1488)
  AND rm.status NOT IN ('materialized'::message_status, 'duplicate'::message_status)
  AND NOT EXISTS (SELECT 1 FROM incidents i
                  WHERE i.raw_message_id = rm.id AND i.is_deleted = false);
DELETE FROM air_violations WHERE id = 1488
  AND review_status = 'flagged_for_review' AND review_reason = 'excluded_kinetic_casualty_or_damage';
-- air_violation_id=1490 reason=excluded_kinetic_casualty_or_damage
UPDATE raw_messages rm
SET status = 'pending'::message_status,
    match_result = NULL,
    error_message = NULL, processing_claim_stage = NULL,
    processing_claimed_at = NULL, processing_claimed_by = NULL
WHERE rm.id = (SELECT raw_message_id FROM air_violations WHERE id = 1490)
  AND rm.status NOT IN ('materialized'::message_status, 'duplicate'::message_status)
  AND NOT EXISTS (SELECT 1 FROM incidents i
                  WHERE i.raw_message_id = rm.id AND i.is_deleted = false);
DELETE FROM air_violations WHERE id = 1490
  AND review_status = 'flagged_for_review' AND review_reason = 'excluded_kinetic_casualty_or_damage';
-- air_violation_id=1491 reason=excluded_kinetic_casualty_or_damage
UPDATE raw_messages rm
SET status = 'pending'::message_status,
    match_result = NULL,
    error_message = NULL, processing_claim_stage = NULL,
    processing_claimed_at = NULL, processing_claimed_by = NULL
WHERE rm.id = (SELECT raw_message_id FROM air_violations WHERE id = 1491)
  AND rm.status NOT IN ('materialized'::message_status, 'duplicate'::message_status)
  AND NOT EXISTS (SELECT 1 FROM incidents i
                  WHERE i.raw_message_id = rm.id AND i.is_deleted = false);
DELETE FROM air_violations WHERE id = 1491
  AND review_status = 'flagged_for_review' AND review_reason = 'excluded_kinetic_casualty_or_damage';
-- air_violation_id=1493 reason=excluded_kinetic_casualty_or_damage
UPDATE raw_messages rm
SET status = 'pending'::message_status,
    match_result = NULL,
    error_message = NULL, processing_claim_stage = NULL,
    processing_claimed_at = NULL, processing_claimed_by = NULL
WHERE rm.id = (SELECT raw_message_id FROM air_violations WHERE id = 1493)
  AND rm.status NOT IN ('materialized'::message_status, 'duplicate'::message_status)
  AND NOT EXISTS (SELECT 1 FROM incidents i
                  WHERE i.raw_message_id = rm.id AND i.is_deleted = false);
DELETE FROM air_violations WHERE id = 1493
  AND review_status = 'flagged_for_review' AND review_reason = 'excluded_kinetic_casualty_or_damage';
-- air_violation_id=1495 reason=excluded_kinetic_casualty_or_damage
UPDATE raw_messages rm
SET status = 'pending'::message_status,
    match_result = NULL,
    error_message = NULL, processing_claim_stage = NULL,
    processing_claimed_at = NULL, processing_claimed_by = NULL
WHERE rm.id = (SELECT raw_message_id FROM air_violations WHERE id = 1495)
  AND rm.status NOT IN ('materialized'::message_status, 'duplicate'::message_status)
  AND NOT EXISTS (SELECT 1 FROM incidents i
                  WHERE i.raw_message_id = rm.id AND i.is_deleted = false);
DELETE FROM air_violations WHERE id = 1495
  AND review_status = 'flagged_for_review' AND review_reason = 'excluded_kinetic_casualty_or_damage';
-- air_violation_id=1496 reason=excluded_kinetic_casualty_or_damage
UPDATE raw_messages rm
SET status = 'pending'::message_status,
    match_result = NULL,
    error_message = NULL, processing_claim_stage = NULL,
    processing_claimed_at = NULL, processing_claimed_by = NULL
WHERE rm.id = (SELECT raw_message_id FROM air_violations WHERE id = 1496)
  AND rm.status NOT IN ('materialized'::message_status, 'duplicate'::message_status)
  AND NOT EXISTS (SELECT 1 FROM incidents i
                  WHERE i.raw_message_id = rm.id AND i.is_deleted = false);
DELETE FROM air_violations WHERE id = 1496
  AND review_status = 'flagged_for_review' AND review_reason = 'excluded_kinetic_casualty_or_damage';
-- air_violation_id=1497 reason=excluded_kinetic_casualty_or_damage
UPDATE raw_messages rm
SET status = 'pending'::message_status,
    match_result = NULL,
    error_message = NULL, processing_claim_stage = NULL,
    processing_claimed_at = NULL, processing_claimed_by = NULL
WHERE rm.id = (SELECT raw_message_id FROM air_violations WHERE id = 1497)
  AND rm.status NOT IN ('materialized'::message_status, 'duplicate'::message_status)
  AND NOT EXISTS (SELECT 1 FROM incidents i
                  WHERE i.raw_message_id = rm.id AND i.is_deleted = false);
DELETE FROM air_violations WHERE id = 1497
  AND review_status = 'flagged_for_review' AND review_reason = 'excluded_kinetic_casualty_or_damage';
-- air_violation_id=1498 reason=excluded_kinetic_casualty_or_damage
UPDATE raw_messages rm
SET status = 'pending'::message_status,
    match_result = NULL,
    error_message = NULL, processing_claim_stage = NULL,
    processing_claimed_at = NULL, processing_claimed_by = NULL
WHERE rm.id = (SELECT raw_message_id FROM air_violations WHERE id = 1498)
  AND rm.status NOT IN ('materialized'::message_status, 'duplicate'::message_status)
  AND NOT EXISTS (SELECT 1 FROM incidents i
                  WHERE i.raw_message_id = rm.id AND i.is_deleted = false);
DELETE FROM air_violations WHERE id = 1498
  AND review_status = 'flagged_for_review' AND review_reason = 'excluded_kinetic_casualty_or_damage';
-- air_violation_id=1499 reason=excluded_kinetic_casualty_or_damage
UPDATE raw_messages rm
SET status = 'pending'::message_status,
    match_result = NULL,
    error_message = NULL, processing_claim_stage = NULL,
    processing_claimed_at = NULL, processing_claimed_by = NULL
WHERE rm.id = (SELECT raw_message_id FROM air_violations WHERE id = 1499)
  AND rm.status NOT IN ('materialized'::message_status, 'duplicate'::message_status)
  AND NOT EXISTS (SELECT 1 FROM incidents i
                  WHERE i.raw_message_id = rm.id AND i.is_deleted = false);
DELETE FROM air_violations WHERE id = 1499
  AND review_status = 'flagged_for_review' AND review_reason = 'excluded_kinetic_casualty_or_damage';
-- air_violation_id=1500 reason=excluded_kinetic_casualty_or_damage
UPDATE raw_messages rm
SET status = 'pending'::message_status,
    match_result = NULL,
    error_message = NULL, processing_claim_stage = NULL,
    processing_claimed_at = NULL, processing_claimed_by = NULL
WHERE rm.id = (SELECT raw_message_id FROM air_violations WHERE id = 1500)
  AND rm.status NOT IN ('materialized'::message_status, 'duplicate'::message_status)
  AND NOT EXISTS (SELECT 1 FROM incidents i
                  WHERE i.raw_message_id = rm.id AND i.is_deleted = false);
DELETE FROM air_violations WHERE id = 1500
  AND review_status = 'flagged_for_review' AND review_reason = 'excluded_kinetic_casualty_or_damage';
-- air_violation_id=1502 reason=excluded_kinetic_casualty_or_damage
UPDATE raw_messages rm
SET status = 'pending'::message_status,
    match_result = NULL,
    error_message = NULL, processing_claim_stage = NULL,
    processing_claimed_at = NULL, processing_claimed_by = NULL
WHERE rm.id = (SELECT raw_message_id FROM air_violations WHERE id = 1502)
  AND rm.status NOT IN ('materialized'::message_status, 'duplicate'::message_status)
  AND NOT EXISTS (SELECT 1 FROM incidents i
                  WHERE i.raw_message_id = rm.id AND i.is_deleted = false);
DELETE FROM air_violations WHERE id = 1502
  AND review_status = 'flagged_for_review' AND review_reason = 'excluded_kinetic_casualty_or_damage';
-- air_violation_id=1504 reason=excluded_kinetic_casualty_or_damage
UPDATE raw_messages rm
SET status = 'pending'::message_status,
    match_result = NULL,
    error_message = NULL, processing_claim_stage = NULL,
    processing_claimed_at = NULL, processing_claimed_by = NULL
WHERE rm.id = (SELECT raw_message_id FROM air_violations WHERE id = 1504)
  AND rm.status NOT IN ('materialized'::message_status, 'duplicate'::message_status)
  AND NOT EXISTS (SELECT 1 FROM incidents i
                  WHERE i.raw_message_id = rm.id AND i.is_deleted = false);
DELETE FROM air_violations WHERE id = 1504
  AND review_status = 'flagged_for_review' AND review_reason = 'excluded_kinetic_casualty_or_damage';
-- air_violation_id=1505 reason=excluded_kinetic_casualty_or_damage
UPDATE raw_messages rm
SET status = 'pending'::message_status,
    match_result = NULL,
    error_message = NULL, processing_claim_stage = NULL,
    processing_claimed_at = NULL, processing_claimed_by = NULL
WHERE rm.id = (SELECT raw_message_id FROM air_violations WHERE id = 1505)
  AND rm.status NOT IN ('materialized'::message_status, 'duplicate'::message_status)
  AND NOT EXISTS (SELECT 1 FROM incidents i
                  WHERE i.raw_message_id = rm.id AND i.is_deleted = false);
DELETE FROM air_violations WHERE id = 1505
  AND review_status = 'flagged_for_review' AND review_reason = 'excluded_kinetic_casualty_or_damage';
-- air_violation_id=1506 reason=excluded_kinetic_casualty_or_damage
UPDATE raw_messages rm
SET status = 'pending'::message_status,
    match_result = NULL,
    error_message = NULL, processing_claim_stage = NULL,
    processing_claimed_at = NULL, processing_claimed_by = NULL
WHERE rm.id = (SELECT raw_message_id FROM air_violations WHERE id = 1506)
  AND rm.status NOT IN ('materialized'::message_status, 'duplicate'::message_status)
  AND NOT EXISTS (SELECT 1 FROM incidents i
                  WHERE i.raw_message_id = rm.id AND i.is_deleted = false);
DELETE FROM air_violations WHERE id = 1506
  AND review_status = 'flagged_for_review' AND review_reason = 'excluded_kinetic_casualty_or_damage';
-- air_violation_id=1507 reason=excluded_kinetic_casualty_or_damage
UPDATE raw_messages rm
SET status = 'pending'::message_status,
    match_result = NULL,
    error_message = NULL, processing_claim_stage = NULL,
    processing_claimed_at = NULL, processing_claimed_by = NULL
WHERE rm.id = (SELECT raw_message_id FROM air_violations WHERE id = 1507)
  AND rm.status NOT IN ('materialized'::message_status, 'duplicate'::message_status)
  AND NOT EXISTS (SELECT 1 FROM incidents i
                  WHERE i.raw_message_id = rm.id AND i.is_deleted = false);
DELETE FROM air_violations WHERE id = 1507
  AND review_status = 'flagged_for_review' AND review_reason = 'excluded_kinetic_casualty_or_damage';
-- air_violation_id=1508 reason=excluded_kinetic_casualty_or_damage
UPDATE raw_messages rm
SET status = 'pending'::message_status,
    match_result = NULL,
    error_message = NULL, processing_claim_stage = NULL,
    processing_claimed_at = NULL, processing_claimed_by = NULL
WHERE rm.id = (SELECT raw_message_id FROM air_violations WHERE id = 1508)
  AND rm.status NOT IN ('materialized'::message_status, 'duplicate'::message_status)
  AND NOT EXISTS (SELECT 1 FROM incidents i
                  WHERE i.raw_message_id = rm.id AND i.is_deleted = false);
DELETE FROM air_violations WHERE id = 1508
  AND review_status = 'flagged_for_review' AND review_reason = 'excluded_kinetic_casualty_or_damage';
-- COMMIT only after checking affected row counts.
COMMIT;

-- Imported rows with no source message. Decide each one by hand:
--   id=1289 condition=Warplane :: صفحة الإعلامي الشهيد علي شعيب: الطيران الحربي المعادي أغار مستهدفا منطقة مشاع المنصوري و وادي عدشيت القصير
--   id=1290 condition=Warplane :: غارات من الطيران الحربي على المنصوري وعدشيت القصير
--   id=1291 condition=Warplane :: غارة من الطيران الحربي استهدفت مشاع المنصوري
--   id=1292 condition=Warplane :: سلسلة غارات شنّها الطيران الحربي الإسرائيلي صباحًا على بلدة المنصوري Video
--   id=1293 condition=Warplane :: مراسل #الجديد : سلسلة غارات شنها الطيران الحربي الإسرائيلي على بلدة المنصوري جنوب صور Video
--   id=1294 condition=Warplane :: الطيران الحربي الإسرائيلي اغار على دفعات عدة منذ ساعات الفجر حتى الان مستهدفا بلدة المنصوري ────────────── isr
--   id=1295 condition=Warplane :: عاجل | مراسل المنار: الطيران الحربي المعادي اغار على دفعات عدة منذ ساعات الفجر حتى الان مستهدفا بلدة المنصوري
--   id=1296 condition=Warplane :: قرابة الساعة الرابعة والنصف الطيران الحربي المعادي يعتدي على بلدة المنصوري بعدت غارات في جنوب لبنان
--   id=1297 condition=Warplane :: غارة حربية ثالثة على المنصوري
--   id=1298 condition=Warplane :: من جديد الطيران الحربي الإسرائيلي أغار مستهدفًا بلدة المنصوري بغارتين
--   id=1299 condition=Warplane :: مجددا.. ‏الطيران الحربي الإسرائيلي أغار مستهدفًا بلدة المنصوري بغارتين
--   id=1300 condition=Warplane :: غارة حربية إســـرائيلية استهدفت بلدة المنصوري
--   id=1301 condition=Warplane :: عاجل | مراسل المنار: الطيران الحربي المعادي اغار مستهدفا بلدة المنصوري جنوب لبنان
--   id=1303 condition=Warplane :: غارة من الطيران الحربي استهدفت بلدة المنصوري
