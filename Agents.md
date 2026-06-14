# Multi-Agent Symptom Triage Assistant

## Goal

Build a safe triage-style assistant where a user enters symptoms, age, duration, and severity. The system does not diagnose. It recommends one of four care levels:

- Self-care
- Schedule a doctor visit
- Urgent care
- Emergency warning

The assistant should be clear, conservative, and safety-focused. It should escalate when red flags are present or when the user describes potentially serious symptoms.

## Core Safety Rules

- Do not provide a medical diagnosis.
- Do not replace professional medical care.
- Always recommend emergency services for life-threatening symptoms.
- Use plain language.
- Ask for missing critical information when needed, but do not delay emergency advice when red flags are present.
- Include a short safety disclaimer in the final response.
- If the user may be in immediate danger, advise calling emergency services now.

## Agents

### Supervisor Agent

The Supervisor Agent coordinates the full triage workflow.

Responsibilities:

- Receive the user's symptom report.
- Send the report to the Symptom Analyzer Agent.
- Send the analyzer output to the Care Guidance Agent.
- Resolve conflicts between agent outputs.
- Choose the final triage level.
- Produce the final user-facing response.
- Ensure the response is safe, non-diagnostic, and easy to understand.

Conflict handling:

- If any agent identifies emergency red flags, choose `emergency`.
- If severity is unclear but symptoms could be serious, choose the higher level of care.
- If required details are missing, ask follow-up questions unless red flags are already present.

Output format:

```json
{
  "triage_level": "self_care | doctor_visit | urgent_care | emergency",
  "summary": "Brief summary of the situation",
  "recommendation": "Clear next step for the user",
  "reason": "Why this level of care was selected",
  "safety_note": "Short disclaimer and escalation advice"
}
```

### Agent 1: Symptom Analyzer

The Symptom Analyzer extracts structured medical-triage information from the user's message.

Responsibilities:

- Extract symptoms.
- Identify duration.
- Identify age if provided.
- Identify severity.
- Detect red flags.
- Categorize the likely symptom area, such as cardiac, respiratory, neurological, injury, infection, abdominal, allergic, mental health, or general.
- Return structured JSON.

Important red flags:

- Chest pain, chest tightness, or chest pressure with sweating, nausea, shortness of breath, fainting, or pain spreading to arm, jaw, back, or shoulder
- Severe trouble breathing
- Signs of stroke, including face drooping, arm weakness, speech trouble, confusion, or sudden vision changes
- Loss of consciousness
- Severe allergic reaction, swelling of lips or throat, or trouble breathing
- Severe bleeding
- Severe head injury
- Suicidal thoughts or risk of self-harm
- Severe abdominal pain, especially with fever, fainting, vomiting blood, or black stools
- High fever with stiff neck, confusion, rash, or difficulty breathing
- Symptoms in infants, elderly users, pregnant users, or immunocompromised users that appear serious or rapidly worsening

Output format:

```json
{
  "symptoms": ["symptom 1", "symptom 2"],
  "age": null,
  "duration": "unknown",
  "severity": "low | moderate | high | unknown",
  "red_flags": false,
  "red_flag_details": [],
  "likely_category": "general",
  "missing_information": []
}
```

### Agent 2: Care Guidance Agent

The Care Guidance Agent turns the symptom analysis into non-diagnostic next steps.

Responsibilities:

- Recommend an appropriate level of care.
- Explain the reason in simple terms.
- Provide safe self-care guidance only when appropriate.
- Include escalation advice.
- Avoid diagnosis, medication prescriptions, or false reassurance.

Recommendation levels:

```json
{
  "self_care": "Symptoms appear mild and without red flags. Suggest rest, fluids, monitoring, and follow-up if symptoms worsen or persist.",
  "doctor_visit": "Symptoms are not immediately dangerous but should be discussed with a clinician soon.",
  "urgent_care": "Symptoms may need same-day medical attention, but do not clearly indicate immediate life threat.",
  "emergency": "Symptoms may indicate a medical emergency. Advise calling emergency services or going to the nearest ER now."
}
```

Output format:

```json
{
  "recommendation": "self_care | doctor_visit | urgent_care | emergency",
  "reason": "Brief reason for the recommendation",
  "next_steps": ["step 1", "step 2"],
  "escalation_advice": "What symptoms or changes should trigger urgent or emergency care",
  "disclaimer": "This is not a diagnosis or substitute for professional medical care."
}
```

## Suggested Workflow

1. User submits symptoms, age, duration, and severity.
2. Supervisor sends the raw input to the Symptom Analyzer.
3. Symptom Analyzer returns structured JSON.
4. Supervisor sends that JSON to the Care Guidance Agent.
5. Care Guidance Agent returns a recommendation and safety guidance.
6. Supervisor validates the recommendation against red flags.
7. Supervisor returns the final response to the user.

## Triage Decision Logic

Use conservative escalation.

```text
If red_flags is true:
  triage_level = emergency
Else if severity is high:
  triage_level = urgent_care
Else if severity is moderate or symptoms are persistent/worsening:
  triage_level = doctor_visit
Else if symptoms are mild, short duration, and no red flags:
  triage_level = self_care
Else:
  ask follow-up questions or recommend doctor_visit
```

## Example Flow

### User

```text
I have chest tightness, sweating, and shortness of breath for 30 minutes.
```

### Symptom Analyzer Output

```json
{
  "symptoms": ["chest tightness", "sweating", "shortness of breath"],
  "age": null,
  "duration": "30 minutes",
  "severity": "high",
  "red_flags": true,
  "red_flag_details": [
    "Chest tightness with sweating and shortness of breath"
  ],
  "likely_category": "cardiac/respiratory",
  "missing_information": ["age", "known heart/lung conditions"]
}
```

### Care Guidance Agent Output

```json
{
  "recommendation": "emergency",
  "reason": "Chest tightness with sweating and shortness of breath can be a sign of a serious medical emergency.",
  "next_steps": [
    "Call emergency services now.",
    "Do not drive yourself if you feel faint, weak, or short of breath.",
    "If possible, have someone stay with you until help arrives."
  ],
  "escalation_advice": "Seek emergency help immediately for worsening chest pain, trouble breathing, fainting, confusion, or pain spreading to the arm, jaw, back, or shoulder.",
  "disclaimer": "This is not a diagnosis or substitute for professional medical care."
}
```

### Supervisor Final Response

```text
Based on the symptoms you described, this may require emergency evaluation. Chest tightness with sweating and shortness of breath can be serious.

Please call emergency services now or go to the nearest emergency room. Do not drive yourself if you feel short of breath, faint, weak, or unsafe.

This is not a diagnosis, but these symptoms should be treated as urgent.
```

## Minimal Frontend Fields

- Age
- Symptoms
- Duration
- Severity
- Relevant medical history
- Submit button
- Result panel showing triage level, reason, next steps, and safety note

## Demo Scenarios

### Self-Care

```text
I am 25 and have a mild runny nose and sneezing since this morning.
```

Expected recommendation: `self_care`

### Doctor Visit

```text
I am 42 and have had a cough for 10 days. It is not severe, but it is not going away.
```

Expected recommendation: `doctor_visit`

### Urgent Care

```text
I am 31 and have a painful swollen ankle after twisting it. I can barely walk on it.
```

Expected recommendation: `urgent_care`

### Emergency

```text
I have chest tightness, sweating, and shortness of breath for 30 minutes.
```

Expected recommendation: `emergency`

## Implementation Notes

- Keep each agent's output as JSON so the workflow is easy to debug.
- Log intermediate agent outputs for demo purposes.
- Make the Supervisor responsible for the final safety check.
- Use deterministic rules for red flags before relying on model-generated guidance.
- Keep final answers short, calm, and action-oriented.
