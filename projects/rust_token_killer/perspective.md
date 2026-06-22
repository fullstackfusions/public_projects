## Personal Demo angle
Hook: "I cut my coding-agent token bill 70% with a local proxy — here's the proof."

Shape: Concrete, narrow, evidence-first. You install Headroom, point it at one real call path, screenshot the before/after token counts, walk through what got compressed and why.

Audience pull: Engineers who want something they can run this afternoon. High practical value, low abstraction.

The catch: This angle lives or dies on real numbers from your own stack — not the maintainer's benchmark. The research brief flags the Localz spike as a backlog item, not a completed experiment. Per your own rule (real benchmarks are the credibility differentiator over illustrative ones), this angle isn't ready to draft today — you'd need to actually run headroom proxy against a Localz RAG call first and capture real before/after numbers, including whether prompt-cache hit rate survives.

Payoff: "Here's exactly how much this saves you, reproducibly."


## Thesis angle
Hook: Something closer to a position — e.g. "Context compression is becoming its own infrastructure layer, and most teams are still treating it as a prompt-engineering trick."

Shape: Broader, opinionated, structural. Headroom becomes the case study that proves the thesis, not the whole story. You'd pull in the comparison table (Headroom vs. RTK vs. lean-ctx vs. provider-native compaction), the CacheAligner insight, the CCR reversibility design — and frame all of it as evidence for "harness engineering beats model engineering" at the token-economics layer.

Audience pull: Principal/Staff-track engineers and architects thinking about systems, not just tools — closer to your "MCP is distribution, not moat" register.

The catch: Needs a sharp, falsifiable claim near the top, not just "this is a cool tool." The research brief gives you raw material for that claim (it's basically already drafted in §4's "category here is context engineering as infrastructure") but you'd need to commit to defending it.

Payoff: "Here's the architectural pattern this points to, and why it matters beyond this one repo."
