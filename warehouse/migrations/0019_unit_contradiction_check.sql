-- A number lifted out of a sentence keeps the sentence's arithmetic and none of
-- its meaning. Australia's 2009 public debt is recorded as 2006 -- the year in
-- "the Commonwealth government eliminated its net debt in 2006" -- carrying the
-- unit 'percent'. China's is 10.72 trillion, an absolute renminbi figure, also
-- under 'percent' and also carrying a currency. Neither is detectable by range
-- alone: 2006 is a plausible percentage of GDP for a heavily indebted state,
-- and every one of these rows has valid provenance back to a real field value.
--
-- What gives them away is self-contradiction between the value and the unit it
-- claims. A percentage is not denominated in a currency; a percentage that is
-- exactly a year in the corpus's own publication range is almost never a
-- measurement. This check names that class so it is visible in the quality
-- report rather than sitting in obs.observation looking like data.
--
-- It is a warning, not a release gate: the rows are wrong, but they are wrong
-- in the extractor, and gating a release on them would block every load until
-- the prose-extraction problem is solved rather than making it visible now.

INSERT INTO meta.quality_check
    (code, label, category, description, default_severity, is_release_gate)
VALUES
    ('value_contradicts_unit',
     'Value contradicts its unit',
     'semantic',
     'A typed value that cannot mean what its unit says: a percentage carrying '
     'a currency, or a percentage that is exactly a year within the corpus''s '
     'publication range. Both are signatures of a number extracted from '
     'explanatory prose rather than from a published figure.',
     'warning',
     false)
ON CONFLICT (code) DO NOTHING;
