-- 0013_unclassified_entity_type — a type for entities that exist but are not yet judged.
--
-- Bootstrapping an entity per source entry is a legitimate and auditable act:
-- it asserts "this source has a distinct entry with this code", which is
-- exactly what the source says, and nothing more. What it must NOT do is assert
-- a kind. The Factbook does not reliably state whether an entry is a sovereign
-- state, a dependency or a disputed territory, and inferring it from the text
-- would be the platform inventing a political judgement it has no evidence for.
--
-- So bootstrapped entities get this type. It is deliberately uncomfortable to
-- leave in place: `api.entity` will show it, the coverage report counts it, and
-- it reads as unfinished work because it is. The alternative -- defaulting to
-- 'sovereign_state' -- would be comfortable and wrong, and would quietly
-- classify Antarctica, the Gaza Strip and the Indian Ocean as countries. §82,
-- §168.

INSERT INTO core.entity_type (code, label, is_territorial, is_sovereign, description)
VALUES ('unclassified', 'Unclassified', true, false,
        'Created from a source entry whose kind has not yet been determined. Asserts only that the source has a distinct entry with this identifier; asserts nothing about sovereignty, territoriality or status. Curation replaces this with a real type, and its presence in a report is a measure of outstanding work rather than a property of the world.')
ON CONFLICT (code) DO NOTHING;

-- is_territorial defaults to true above only because most entries are places;
-- it is not a claim about any particular one, and nothing in geo.* may create a
-- geometry for an entity on the strength of it.
COMMENT ON TABLE core.entity_type IS
  'What kind of thing an entity is. A reference table rather than an enum because this list has grown while writing the schema and will grow again — supranational unions, condominiums and unrecognised states all arrive without warning. The ''unclassified'' member is the honest resting place for an entity created from a source entry before anyone has judged what it is. ADR-0004.';
