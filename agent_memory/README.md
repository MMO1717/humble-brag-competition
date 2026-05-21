# Agent Memory Directory

This directory stores the three-tier memory system for the BRAG pipeline.

## Structure

- `static/` - Static knowledge files (markdown with English Prompt Notes sections)
- `active/` - Active memory items (memory.jsonl)
- `candidate/` - Candidate memory items pending review (memory_candidates.jsonl)

## Memory Modes

- `no_memory`: No dynamic memory injection (static wiki still loaded separately)
- `static_only`: Only static memory items from static/*.md files
- `active`: Static + active memory items
- `active_plus_candidate`: Static + active + candidate memory items

## Static Memory Files

Place markdown files in `static/` with `## English Prompt Notes` sections:

- `label_schema.md` - Label definitions and distinctions
- `bragging_mechanism_guide.md` - Mechanism classification guidance
- `response_strategy_guide.md` - Strategy selection guidance
- `risk_policy.md` - Risk assessment policies
- `platform_relationship_style.md` - Platform/relationship-specific style notes

## Usage

```bash
python -m humble_brag.runner --backend llm --use-skillflow --use-agent-memory --memory-mode active
```
