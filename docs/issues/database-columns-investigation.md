# Investigation: Database Columns Audit & Migration

## Summary
Conduct a thorough review of all columns in the current database schema. The goal is to identify which columns are actively used by the application and which are obsolete or unnecessary, with a focus on cleaning up unused or redundant fields—especially those related to YouTube metadata.

## Background
Over time, the database has accumulated a number of columns, particularly from YouTube metadata, that are rarely or never used. In practice, the application only relies on a small subset of these fields (e.g., YouTube video ID, thumbnail, and media content). Most other YouTube-related columns are not needed, as their data can be refetched if necessary. The majority of metadata used in the app comes from iTunes, not YouTube.

Additionally, there are some inconsistencies, such as the use of the `mbid` (MusicBrainz ID) column to store iTunes metadata IDs, which should be addressed in a future migration.

## Task
- Review all columns in the current database schema.
- For each column, determine if it is actively used by the application (frontend or backend).
- Identify columns that are obsolete, redundant, or never populated (e.g., most YouTube metadata fields).
- Prepare a list of columns to keep and a list of columns to remove.
- Do **not** make schema changes yet—this is an investigation and planning task only.
- Provide a brief rationale for any columns recommended for removal.

### Example Guidance
- Many YouTube metadata columns are likely not needed (other than video ID, thumbnail, and media content).
- Most metadata used in the app comes from iTunes, not YouTube.
- Do not rely solely on current null/empty values—consider future use cases and the ability to refetch data if needed.

## Deliverables
- A written summary of which columns are used and which are not, with recommendations for removal.
- A rationale for each recommendation.
- No database migrations or code changes should be made as part of this task.

## Notes
- The schema may be more complete by the time this task is picked up, so review the latest state.
- Do not overfit to current usage—consider maintainability and future-proofing.
- This task is a prerequisite for a future migration to clean up the schema.
