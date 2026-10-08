**\[AGENT NAME\]**  
*Product Requirements Document: Agent Build*

*HOW TO USE THIS TEMPLATE*  
   
*1\.  Make a copy of this file. Work on your copy — do not edit the original.*  
*2\.  Fill in each section. As you complete a section, delete the direction box (the shaded blue boxes like this one).*  
*3\.  When you submit, the doc should contain only your content — no direction boxes, no placeholder text.*  
   
*If you’re unsure what goes in a section, re-read the direction box before deleting it. **Delete this box when done.***

**Agent name:**  \[Agent name\]

**Owner(s):**  \[Your name(s)\]

**Date:**  \[Date\]

# **1\. PROBLEM**

*In a few sentences: What problem are you solving and for whom? Focus on the problem, not the agent. A strong problem statement names the user, the pain, and the consequence. Use the sentence starter below if it helps. **Delete this box when done.***  
   
**Sentence starter:**  
*\[User\] experiences \[problem\] in \[context\] because of \[root cause\], resulting in \[impact\].*  
   
**Example:**  
*CS managers at a B2B SaaS company spend hours every week manually checking dashboards for churn signals, because account health data is scattered across the CRM, the support desk, and product analytics — resulting in at-risk accounts being discovered too late to save.*

\[Write your problem description here.\]

### **Supporting Context (optional)**

*Add 2–3 data points, research findings, or user pain points that support your problem statement. This section is optional — delete it entirely if you don’t have supporting data. **Delete this box when done.***  
   
**Examples:**  
*•  CSMs at Acme manage 30–60 accounts each; account health data lives in 3 disconnected systems.*  
*•  In exit interviews, 40% of churned customers showed warning signs 60+ days before renewal.*

* \[Insert data point or research finding\]

* \[Insert user pain point observed or validated\]

* \[Insert workflow or business context\]

## **1a. Opportunity**

*Write 1–2 sentences: What opportunity does this problem create? Frame it as what becomes possible if the agent takes this work over — for your users and for the business. Then add 1–2 supporting data points below. **Delete this box when done.***  
   
**Example:**  
*Give every CSM an automated daily view of account risk — recovering \~5 hours per CSM per week and surfacing churn signals weeks earlier, protecting renewal revenue.*

\[Write your opportunity statement here.\]

### **Size of the Opportunity**

* \[Insert the size of the pain: hours spent, revenue at risk, error rates\]

* \[Insert link to supporting doc or analysis, if available\]

## 

## **1b. Users & Needs**

*Identify your primary and secondary user groups. Be specific — generic descriptions don’t help the team build the right thing.* *Then list key user needs using the sentence starter below.* ***Delete this box when done.***

**Sentence starter for needs:**  
*As \[primary user\], I need to \[goal\] because \[reason\].*

**Examples:**  
*•  Primary users: Customer success managers managing 30–60 accounts who value catching risk early over exhaustive detail.*  
*•  Need: As a CSM, I need a prioritized list of at-risk accounts each morning because I don’t have time to check every dashboard.*  
*•  Need: As a CS team lead, I need to see why each account was flagged because I have to trust the report before my team acts on it.*

**Primary user(s):**  \[Who they are and what they care about\]

**Secondary users:**  \[Who else interacts with this product, if anyone\]

### **Key User Needs**

As \[primary user\], I need to \[goal\] because \[reason\].

As \[primary user\], I need to \[goal\] because \[reason\].

# **2\. PROPOSED SOLUTION**

*Describe what your agent is and how it works in 3–4 sentences. Write for a reader with no background on this project. Be concrete: what triggers it, what it does, and what it hands back to the human. The specifics — tools, system prompt, blast radius, evals — go in Section 3 below. Use the sentence starter if it helps. **Delete this box when done.***  
   
**Sentence starter:**  
*\[Agent name\] is an AI agent for \[role\] that \[core action\]. It runs \[trigger — on a schedule / when X happens / on request\], uses its tools to \[gather / check / draft\], and delivers \[output\] to \[user\]. The \[user\] then \[what the human does with it\].*  
   
**Example:**  
*RenewalRadar is an AI agent for Customer Success that finds at-risk accounts before it’s too late to save them. It runs every morning before standup, pulls health signals for every assigned account from the CRM, support desk, and product analytics, and delivers a prioritized risk report with a suggested next step per account. The CSM reviews the report and decides which accounts to act on — the agent informs the human; the human makes the call.*

\[Write your solution description here.\]

## **2a. Value Proposition**

*In 1–2 sentences, clearly state who this is for, what problem it solves, how it helps, and what the differentiator is. Use the sentence starter below if it helps. **Delete this box when done.***  
   
**Sentence starter:**  
*\[Primary user\] who struggle with \[specific problem \+ root cause\] use \[agent name\], an AI agent that \[core action it takes\]. Unlike \[current alternatives or status quo\], it \[specific, concrete differentiator\], helping them \[clear, measurable or concrete benefit\].*  
   
**Example:**  
*CSMs who struggle to spot churn risk early — because health signals are scattered across CRM, support, and product data — use RenewalRadar, an AI agent that reviews every account overnight and delivers a prioritized risk report each morning. Unlike static dashboards, it reads across all three systems and explains why each account was flagged, helping CSMs act weeks earlier.*

\[Write your value proposition here.\]

## **2b. Top 3 MVP Value Props**

*Fill in each value prop type, one sentence each. **Delete this box when done.***  
  *•  The Vitamin:  a baseline capability users expect (table stakes). Without it, the agent feels incomplete.*  
  *•  The Painkiller:  directly eliminates the most painful part of the problem.*  
  *•  The Steroid:  the standout moment that makes users choose your agent over the manual way.*  
   
**Examples:**  
*•  Vitamin:  Every assigned account is checked every single day — nothing slips through.*  
*•  Painkiller:  No more dashboard-hopping — risk signals from three systems arrive in one prioritized report.*  
*•  Steroid:  Every flagged account comes with a suggested next step, drafted and ready for the CSM to act on.*

**The Vitamin**  *(must-have baseline)*:  \[Write your vitamin value prop\]

**The Painkiller**  *(solves the core pain)*:  \[Write your painkiller value prop\]

**The Steroid**  *(the magic moment)*:  \[Write your steroid value prop\]

## **2c. Success Metrics**

*Complete one row per goal. Every metric needs a specific, numeric target — not “improve” or “increase.”*  
  *•  Goal:  What you’re trying to achieve — tie it to your value props in 2a–2b*  
  *•  Signal:  A measurable user behavior that indicates success*  
  *•  Metric:  How you’ll track that signal*  
  *•  Target:  A specific number or threshold that means you’ve succeeded*  
*For agents: include at least one quality metric (accuracy, false-flag rate) alongside usage metrics — an agent no one trusts is an agent no one uses. Add rows as needed. **Delete this box when done.***  
   
**Example rows:**  
*Goal: Save CSM time  |  Signal: CSMs stop manual dashboard checks  |  Metric: Hours per CSM per week on account review  |  Target: \<1 hour by week 4*  
*Goal: Trustworthy flags  |  Signal: Flagged accounts are genuinely at risk  |  Metric: False-flag rate on weekly CSM review  |  Target: \<20%*

| Goal | Signal | Metric | Target |
| :---- | :---- | :---- | :---- |
| \[Goal — tied to a value prop above\] | \[Measurable indicator\] | \[How you’ll track it\] | \[Specific number or threshold\] |
| \[Goal — tied to a value prop above\] | \[Measurable indicator\] | \[How you’ll track it\] | \[Specific number or threshold\] |
| \[Goal — quality metric\] | \[Measurable indicator\] | \[How you’ll track it\] | \[Specific number or threshold\] |

# **3\. AGENT REQUIREMENTS**

*This is the spec of the agent itself — the four things you define before you build: the tools the agent can call, the system prompt it runs on, the worst case if it goes wrong, and the tests that tell you it actually works.*

***Delete this box when done.***

## **3a. Tools**

*List every tool your agent can call. For each tool: its name, what it does, the API it calls, and the data it returns. Rules of thumb:*  
  *•  If the agent can’t reach the data through a tool, the agent doesn’t have it.*  
  *•  Start with the smallest set of tools that gets the job done — aim for 2–4.*  
  *•  Prefer read-only tools. Every tool that can write, send, or delete grows your blast radius (3c).*  
   
**Example row:**  
*get\_account\_health  |  Pulls current health signals for one account  |  HubSpot CRM API — GET /accounts/{id}  |  Plan tier, last login date, open ticket count, NPS score*

*Add rows as needed. **Delete this box when done.***

| Tool name | What it does | API it calls | Data it returns |
| :---- | :---- | :---- | :---- |
| \[tool\_name\] | \[One sentence: what this tool does for the agent\] | \[Service \+ endpoint\] | \[Fields the tool returns\] |
| \[tool\_name\] | \[One sentence: what this tool does for the agent\] | \[Service \+ endpoint\] | \[Fields the tool returns\] |
| \[tool\_name\] | \[One sentence: what this tool does for the agent\] | \[Service \+ endpoint\] | \[Fields the tool returns\] |

## 

## **3b. System Prompt v0**

*Write the first version of your agent’s system prompt. A solid v0 covers:*  
  *•  Identity — who the agent is and who it works for*  
  *•  Task — what it should do, step by step*  
  *•  Tool guidance — when to use each tool from 3a*  
  *•  Constraints — what it must never do*  
  *•  Output format — exactly what the final answer should look like*  
  *•  Escalation — when to stop and hand off to a human*  
   
**Example opening:**  
*You are a customer success assistant for Acme’s CSM team. Each morning, review every account assigned to your CSM. For each account, call get\_account\_health and check for churn signals: no logins in 14+ days, 3+ open tickets, or NPS below 6\. Rank flagged accounts by renewal date, nearest first. Output a report with one line per account: name, risk signals, suggested next step. Never contact customers. If you cannot retrieve data for an account, list it under “Needs manual review” instead of guessing.*  
   
***Delete this box when done.***

\[Write your full system prompt v0 here.\]

## 

## **3c. Blast Radius**

*If the agent does the wrong thing, what’s the worst case? Your blast radius is everything the agent can touch: the data it can read, the systems it can write to, and the people who see its output. Work through it with your pair:*  
  *•  What’s the single worst action the agent could take with the tools you gave it in 3a?*  
  *•  Who is affected — and can the damage be undone?*  
  *•  What safeguard limits the damage (read-only tools, human approval before send, scoped API keys)?*  
   
*Rule of thumb: if the worst case is “a human reviews a wrong draft,” you’re fine. If the worst case is “a customer receives a wrong email,” add a safeguard. **Delete this box when done.***  
   
**Example:**  
*Worst case: the agent misreads health data and flags a healthy account as at-risk. Impact: one CSM wastes an hour investigating — annoying, but fully recoverable. The radius stays small because every tool is read-only and the report goes only to the CSM, never to a customer.*

**Worst-case scenario:**  \[Describe the single worst thing your agent could do, who it affects, and whether it can be undone\]

### **Failure Modes & Safeguards**

| Failure mode | Worst-case impact | Safeguard |
| :---- | :---- | :---- |
| \[What could go wrong\] | \[Who is affected and how badly\] | \[What limits the damage\] |
| \[What could go wrong\] | \[Who is affected and how badly\] | \[What limits the damage\] |
| \[What could go wrong\] | \[Who is affected and how badly\] | \[What limits the damage\] |

## 

## **3d. Eval Card**

*How do you know your agent is actually good? AI agent evaluation is the process of testing and measuring how well an autonomous AI agent executes multi-step tasks, reasons through problems, and interacts with tools.*

*Before you build, define your Eval Card: three test cases you write in advance and re-run every time you make a significant change. Write each expected output before you ever see an actual output — otherwise you’ll rationalize whatever the agent returns.*

  *•  Case 1 — Golden example (normal input): a realistic input your agent should handle well. Write the correct output specifically — not “a useful summary” but the actual structure a real user in your role would act on.*  
  *•  Case 2 — Golden example (edge case): an input that’s valid but harder — sparse data, a conflicting signal, an unusual situation your role actually encounters.*  
  *•  Case 3 — Adversarial input: an input designed to make your agent fail — an empty API response, a tool that returns nothing, conflicting data across two tools. Define what graceful failure looks like: a useful message, not a stack trace. Your failure modes in 3c are a good source.*  
   
*The regression problem: every system prompt change or new tool risks quietly breaking something that was working. Your Eval Card catches this — re-run all three cases after every significant change to 3a or 3b. And the bar to clear is the would-I-use-this test: is the output better than what someone in your role could produce in 5 minutes manually? **Delete this box when done.***  
   
**Example:**  
*Case 1: Account with no logins in 20 days and 4 open tickets → Expected: flagged, ranked by renewal date, with both signals named in the reason.*  
*Case 2: Account with heavy product usage but an NPS of 4 from its champion → Expected: flagged with the conflicting signals called out — not skipped because usage looks healthy.*  
*Case 3: CRM returns an error for one account → Expected: listed under “Needs manual review” — no invented data, no stack trace.*

| Case | Input | Expected output — written before you run |
| :---- | :---- | :---- |
| 1 — Golden example (normal input) | \[A realistic input your agent should handle well\] | \[The correct output, specifically — structure, priorities, content a real user would act on\] |
| 2 — Golden example (edge case) | \[Valid but harder — sparse data, a conflicting signal, an unusual situation\] | \[What the agent should do with it\] |
| 3 — Adversarial input | \[Designed to make your agent fail — empty API response, conflicting data across tools\] | \[What graceful failure looks like — a useful message, not a stack trace\] |

