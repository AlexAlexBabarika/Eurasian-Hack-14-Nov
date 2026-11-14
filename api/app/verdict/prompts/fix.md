`fixes`: one to three fixes.
- `policy_clause` must be paste-ready text for the privacy policy, in plain English, first person plural ("We ..."), and must name the actual vendor(s) and data categories from the evidence. Use square-bracket placeholders only for facts you cannot know (e.g. "[retention period]").
- `code_change` is a short instruction or diff for an engineer, referencing the file from the evidence where possible. Use null when no code change is needed.
- A fix must never suggest hiding, obscuring or removing evidence of the behaviour; either disclose it or stop doing it.
