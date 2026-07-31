To successfully build a proof of concept for the **"Real-Time AI Insights"** use case without using real sensitive information, your team will need a robust set of synthetic or "mock" data. This data should be designed to test the AI's ability to parse, reason, and automate as described in the assignment.

Here is the specific mock data I recommend they prepare:

### 1. Unstructured Prospect Data (For Step 1)

To demonstrate the AI's ability to "digest" financial information, the team needs samples that mimic what a real prospect would provide.

- **Synthetic Bank/Brokerage Statements:** Create 3–5 PDF or CSV files containing fake transaction histories, account balances (e.g., Checking, Savings, 401k), and current holdings. Ensure these include a variety of asset types (Cash, Stocks, Bonds).
- **Meeting Transcripts/Notes:** Draft 2–3 text files representing a conversation between an advisor and a prospect. These should include "messy" data like: _"I want to retire at 60," "I'm worried about market volatility,"_ or _"I need to save for my daughter’s university in 5 years"_.
- **Client Questionnaires:** A set of mock "Risk Profile" questionnaires with varied answers (e.g., "Conservative," "Aggressive," "Growth-oriented") to test the asset mix generation.

### 2. Product & Research Material (For Step 1)

The AI needs a "knowledge base" to tap into for determining risk and alignment.

- **Mock Investment Fund Fact Sheets:** Create 5–10 brief documents describing various "fictional" investment products (e.g., "Global Tech Growth Fund," "Safe-Harbor Bond Fund"). Include their risk ratings (1–10 scale) and historical performance.
- **Risk Alignment Rules:** A text-based guide that the AI can use to match a prospect's risk tolerance score to a specific asset mix (e.g., "If risk is 4, assign 40% Equities and 60% Fixed Income").

### 3. Downstream System Data (For Step 2 & 3)

To simulate the automated account opening and rebalancing, the team will need structured data schemas.

- **IPS (Investment Policy Statement) Templates:** A JSON or XML schema representing the data fields required for downstream systems like **Broadridge** or **Client Source** (e.g., ClientID, AccountType, TargetAssetMix, ComplianceFlag).
- **Mock Portfolio Snapshots:** A small database (in **MongoDB**) representing "Existing Portfolios." This will allow the team to demonstrate the **Step 3 rebalancing trigger**—showing how the AI identifies the gap between the "Current" state and the "New Plan" state.

### 4. Application State Data (For the "Tweak" Feature)

Since they are using **LangGraph** for state management, they need to define the "State" object.

- **Proposal Version History:** Sample data representing "Version 1" of a proposal (AI-generated) vs. "Version 2" (after the advisor/client "tweaks" a variable like retirement age or risk level).

### Mentor Tip for the Team:

Encourage the team to make the mock data **diverse**. If all the mock prospects are "Aggressive Growth" types, they won't be able to effectively demonstrate the AI's reasoning capabilities during the 7-minute demo. Having a "Conservative" profile and an "Aggressive" profile will better showcase **GenAI Leverage & Application (20 pts)**.

Would you like me to suggest some specific prompts they could use to generate this mock data using an LLM?
