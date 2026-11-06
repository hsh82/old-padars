# School assessment schemes

Education Assessment Plan/Criteria, Grading Scale and Assessment Result remain
authoritative. School Assessment Scheme owns versioned school calculation
configuration for one School Course Offering and optional Academic Term.
School Assessment Component child rows select one submitted plan criterion and
an explicit positive percentage weight. Every plan must match the offering;
term schemes require its exact term. Weights total 100. Output maximum and
decimal precision are explicit school configuration, not national defaults.

The offering row serializes version allocation. A unique version key prevents
duplicate offering/term/version records. Saved context cannot be changed.
Only school managers/platform administrators create or approve schemes. Native
submission records the approver and timestamp, freezes configuration and keeps
approved versions as history. Corrections require a new version; cancellation
and deletion of approved schemes are blocked.

Calculation requires an approved scheme, a submitted matching annual enrollment,
and one submitted Education result per selected plan/student. Each selected
criterion must exist exactly once with a finite score within its positive
maximum. Calculations use the source maximum retained on the approved result,
decimal arithmetic and school-selected output scale, precision and Half Up or
Half Even rounding. Approved schemes retain a snapshot of grading intervals.
Missing results
or inconsistent source data fail rather than being treated as zero. Grading
uses the selected submitted Education Grading Scale. Private comments are not
returned. A preview does not publish a report card; immutable publication and
student delivery are subsequent workflows.
