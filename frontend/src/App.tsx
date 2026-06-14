import {
  Activity,
  AlertTriangle,
  ArrowRight,
  Brain,
  Check,
  ClipboardList,
  HeartPulse,
  Info,
  ListChecks,
  Route,
  Send,
  ShieldCheck,
  Sparkles,
  Stethoscope,
} from "lucide-react";
import { AnimatePresence, motion } from "framer-motion";
import { FormEvent, useEffect, useMemo, useState } from "react";

type Severity = "low" | "moderate" | "high";
type TriageLevel = "self_care" | "doctor_visit" | "urgent_care" | "emergency";

type Intake = {
  age: string;
  symptoms: string;
  duration: string;
  severity: Severity | "";
  medical_history: string;
  current_medications: string;
  allergies: string;
  pregnant_or_immunocompromised: boolean;
};

type SymptomAnalyzerOutput = {
  symptoms: string[];
  age: number | null;
  duration: string;
  severity: Severity | "unknown";
  red_flags: boolean;
  red_flag_details: string[];
  likely_category: string;
  missing_information: string[];
};

type CareGuidanceOutput = {
  recommendation: TriageLevel;
  reason: string;
  next_steps: string[];
  escalation_advice: string;
  disclaimer: string;
};

type SupervisorOutput = {
  triage_level: TriageLevel;
  summary: string;
  recommendation: string;
  reason: string;
  safety_note: string;
};

type TriageResponse = {
  case_id: string;
  triage_level: TriageLevel;
  final: SupervisorOutput;
  symptom_analyzer: SymptomAnalyzerOutput | null;
  care_guidance: CareGuidanceOutput | null;
  supervisor: SupervisorOutput;
  graph: {
    visited_nodes: string[];
    used_llm: boolean;
    provider: string;
    model_name: string;
    fallback_reason?: string | null;
  };
};

type GraphNodeId = "intake" | "symptom_analyzer_node" | "care_guidance_node" | "supervisor_node" | "final_response";

const API_BASE = import.meta.env.VITE_API_BASE ?? "http://127.0.0.1:8000";

const initialIntake: Intake = {
  age: "",
  symptoms: "",
  duration: "",
  severity: "",
  medical_history: "",
  current_medications: "",
  allergies: "",
  pregnant_or_immunocompromised: false,
};

const demoCases = [
  {
    label: "Mild Cold",
    detail: "Self-care",
    icon: Sparkles,
    intake: { age: "25", symptoms: "mild runny nose and sneezing", duration: "since this morning", severity: "low" as Severity },
  },
  {
    label: "Long Cough",
    detail: "Doctor visit",
    icon: Stethoscope,
    intake: { age: "42", symptoms: "cough that is not going away", duration: "10 days", severity: "moderate" as Severity },
  },
  {
    label: "Ankle Injury",
    detail: "Urgent care",
    icon: Activity,
    intake: { age: "31", symptoms: "painful swollen ankle after twisting it and can barely walk", duration: "2 hours", severity: "high" as Severity },
  },
  {
    label: "Chest Symptoms",
    detail: "Emergency",
    icon: HeartPulse,
    intake: { age: "54", symptoms: "chest tightness, sweating, and shortness of breath", duration: "30 minutes", severity: "high" as Severity },
  },
];

const severityOptions: Array<{ value: Severity; label: string; helper: string }> = [
  { value: "low", label: "Low", helper: "Mild and stable" },
  { value: "moderate", label: "Moderate", helper: "Noticeable or persistent" },
  { value: "high", label: "High", helper: "Severe or worsening" },
];

const graphNodes: Array<{ id: GraphNodeId; backendNode?: string; label: string; description: string; icon: typeof ClipboardList }> = [
  { id: "intake", label: "Intake", description: "User symptom details enter the workflow.", icon: ClipboardList },
  { id: "symptom_analyzer_node", backendNode: "symptom_analyzer_node", label: "Symptom Analyzer", description: "Extracts symptoms, severity, category, and red flags.", icon: Brain },
  { id: "care_guidance_node", backendNode: "care_guidance_node", label: "Care Guidance", description: "Creates safe next steps and escalation advice.", icon: ListChecks },
  { id: "supervisor_node", backendNode: "supervisor_node", label: "Supervisor", description: "Combines outputs and applies safety overrides.", icon: ShieldCheck },
  { id: "final_response", label: "Final Response", description: "Shows a user-facing triage recommendation.", icon: HeartPulse },
];

const loadingMessages = ["Validating intake", "Analyzing symptoms", "Checking red flags", "Preparing care guidance", "Finalizing recommendation"];

const fadeUp = {
  hidden: { opacity: 0, y: 18 },
  show: { opacity: 1, y: 0 },
};

function titleCaseLevel(level: string) {
  return level.replace("_", " ").replace(/\b\w/g, (letter) => letter.toUpperCase());
}

function graphStatus(result: TriageResponse | null) {
  if (!result) return "Ready for Groq-backed triage";
  if (result.graph.used_llm) {
    const provider = result.graph.provider === "groq" ? "Groq" : result.graph.provider;
    return `${provider} LLM connected: ${result.graph.model_name}`;
  }
  if (result.graph.fallback_reason) return `Deterministic fallback: ${result.graph.fallback_reason}`;
  return "Deterministic fallback";
}

function nodeIsComplete(node: (typeof graphNodes)[number], result: TriageResponse | null) {
  if (!result) return false;
  if (node.id === "intake" || node.id === "final_response") return true;
  return result.graph.visited_nodes.includes(node.backendNode ?? node.id);
}

function nodeSummary(nodeId: GraphNodeId, intake: Intake, result: TriageResponse | null) {
  if (nodeId === "intake") {
    return [
      `Age: ${intake.age || "not provided"}`,
      `Duration: ${intake.duration || "not provided"}`,
      `Severity: ${intake.severity ? titleCaseLevel(intake.severity) : "not selected"}`,
    ];
  }
  if (!result) return ["Select a demo or submit symptoms to see this agent respond."];

  if (nodeId === "symptom_analyzer_node" && result.symptom_analyzer) {
    const analyzer = result.symptom_analyzer;
    return [
      `Symptoms: ${analyzer.symptoms.join(", ")}`,
      `Category: ${analyzer.likely_category}`,
      analyzer.red_flags ? `Red flags: ${analyzer.red_flag_details.join(", ") || "Yes"}` : "Red flags: none detected",
    ];
  }
  if (nodeId === "care_guidance_node" && result.care_guidance) {
    return [
      `Recommendation: ${titleCaseLevel(result.care_guidance.recommendation)}`,
      `Reason: ${result.care_guidance.reason}`,
      `Next steps: ${result.care_guidance.next_steps.slice(0, 3).join("; ")}`,
    ];
  }
  if (nodeId === "supervisor_node") {
    return [
      `Final level: ${titleCaseLevel(result.supervisor.triage_level)}`,
      `Safety reason: ${result.supervisor.reason}`,
      `Model path: ${result.graph.used_llm ? result.graph.model_name : "deterministic fallback"}`,
    ];
  }
  return [result.final.recommendation, result.final.safety_note];
}

function DeveloperTrace({ result }: { result: TriageResponse | null }) {
  if (!result) return null;
  return (
    <motion.details className="developer-trace" variants={fadeUp} initial="hidden" animate="show">
      <summary>Developer trace</summary>
      <div className="trace-grid">
        <pre>{JSON.stringify({ graph: result.graph }, null, 2)}</pre>
        <pre>{JSON.stringify({ symptom_analyzer: result.symptom_analyzer, care_guidance: result.care_guidance, supervisor: result.supervisor }, null, 2)}</pre>
      </div>
    </motion.details>
  );
}

function LangGraphFlow({
  intake,
  result,
  loading,
}: {
  intake: Intake;
  result: TriageResponse | null;
  loading: boolean;
}) {
  const [activeNode, setActiveNode] = useState<GraphNodeId>("intake");
  const [loadingIndex, setLoadingIndex] = useState(0);

  useEffect(() => {
    if (!loading) {
      setLoadingIndex(0);
      return;
    }
    const timer = window.setInterval(() => {
      setLoadingIndex((current) => {
        const next = (current + 1) % graphNodes.length;
        setActiveNode(graphNodes[next].id);
        return next;
      });
    }, 820);
    return () => window.clearInterval(timer);
  }, [loading]);

  useEffect(() => {
    if (result) setActiveNode("final_response");
  }, [result]);

  return (
    <motion.section className="graph-panel" aria-label="LangGraph workflow visualization" variants={fadeUp} initial="hidden" animate="show">
      <div className="section-title graph-title">
        <Route size={20} />
        <div>
          <h2>Agent Flow</h2>
          <p>{loading ? loadingMessages[loadingIndex] : result ? "Completed workflow trace" : "Watch the nodes activate during analysis"}</p>
        </div>
      </div>

      <div className="node-rail">
        <div className="flow-line" />
        {graphNodes.map((node, index) => {
          const Icon = node.icon;
          const complete = nodeIsComplete(node, result);
          const active = loading ? index === loadingIndex : activeNode === node.id;
          return (
            <motion.button
              type="button"
              className={`flow-node ${complete ? "complete" : ""} ${active ? "active" : ""}`}
              key={node.id}
              onClick={() => setActiveNode(node.id)}
              whileHover={{ y: -4, scale: 1.015 }}
              whileTap={{ scale: 0.98 }}
              animate={{
                opacity: loading && !active ? 0.66 : 1,
                boxShadow: active ? "0 22px 55px rgba(73, 224, 201, 0.22)" : "0 10px 30px rgba(0, 0, 0, 0.18)",
              }}
              transition={{ type: "spring", stiffness: 320, damping: 24 }}
            >
              {active && <motion.span className="node-halo" layoutId="active-node-halo" />}
              <span className="node-icon">{complete ? <Check size={18} /> : <Icon size={18} />}</span>
              <span>
                <strong>{node.label}</strong>
                <small>{active ? "Selected" : index === 0 ? "Start" : `Step ${index}`}</small>
              </span>
              {index < graphNodes.length - 1 && <ArrowRight className="node-arrow" size={18} />}
            </motion.button>
          );
        })}
        {loading && <motion.div className="flow-pulse" layout style={{ left: `${loadingIndex * 20 + 8}%` }} />}
      </div>

      <AnimatePresence mode="wait">
        <motion.div
          className="node-detail"
          key={activeNode}
          initial={{ opacity: 0, y: 10, filter: "blur(8px)" }}
          animate={{ opacity: 1, y: 0, filter: "blur(0px)" }}
          exit={{ opacity: 0, y: -8, filter: "blur(8px)" }}
          transition={{ duration: 0.22 }}
        >
          <div>
            <span className="detail-kicker">Selected node</span>
            <h3>{graphNodes.find((node) => node.id === activeNode)?.label}</h3>
          </div>
          <div className="detail-chips">
            {nodeSummary(activeNode, intake, result).slice(0, 3).map((item) => (
              <span key={item}>{item}</span>
            ))}
          </div>
        </motion.div>
      </AnimatePresence>
    </motion.section>
  );
}

export default function App() {
  const [intake, setIntake] = useState<Intake>(initialIntake);
  const [result, setResult] = useState<TriageResponse | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);

  const validation = useMemo(() => {
    const issues: string[] = [];
    const age = Number(intake.age);
    if (!intake.age || Number.isNaN(age) || age < 0 || age > 120) issues.push("Age must be between 0 and 120.");
    if (intake.symptoms.trim().length < 3) issues.push("Symptoms are required.");
    if (!intake.duration.trim()) issues.push("Duration is required.");
    if (!intake.severity) issues.push("Severity is required.");
    return issues;
  }, [intake]);

  async function submit(event: FormEvent) {
    event.preventDefault();
    setError(null);
    setResult(null);
    if (validation.length) {
      setError(validation[0]);
      return;
    }
    setLoading(true);
    try {
      const response = await fetch(`${API_BASE}/triage/analyze`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          ...intake,
          age: Number(intake.age),
          medical_history: intake.medical_history || null,
          current_medications: intake.current_medications || null,
          allergies: intake.allergies || null,
        }),
      });
      if (!response.ok) throw new Error(`Request failed with status ${response.status}`);
      setResult(await response.json());
    } catch (err) {
      setError(err instanceof Error ? err.message : "Unable to analyze symptoms.");
    } finally {
      setLoading(false);
    }
  }

  const nextSteps = result?.care_guidance?.next_steps ?? [];

  return (
    <main className="app-shell">
      <motion.section className="topbar" initial="hidden" animate="show" variants={fadeUp}>
        <div>
          <div className="eyebrow">
            <HeartPulse size={18} />
            Multi-agent symptom triage
          </div>
          <h1>Move through symptoms like a conversation.</h1>
          <p>A calmer triage demo with animated agents, concise prompts, and safety-first guidance.</p>
        </div>
        <div className="status-pill">
          <Activity size={18} />
          <span>{graphStatus(result)}</span>
        </div>
      </motion.section>

      <section className="quick-scenarios" aria-label="Demo scenarios">
        {demoCases.map((demo, index) => {
          const Icon = demo.icon;
          return (
            <motion.button
              type="button"
              key={demo.label}
              onClick={() => {
                setResult(null);
                setError(null);
                setIntake({ ...initialIntake, ...demo.intake });
              }}
              initial={{ opacity: 0, y: 12 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{ delay: index * 0.055 }}
              whileHover={{ y: -5, scale: 1.015 }}
              whileTap={{ scale: 0.98 }}
            >
              <Icon size={18} />
              <span>
                <strong>{demo.label}</strong>
                <small>{demo.detail}</small>
              </span>
            </motion.button>
          );
        })}
      </section>

      <section className="workspace">
        <motion.form className="intake-panel" onSubmit={submit} variants={fadeUp} initial="hidden" animate="show">
          <div className="section-title">
            <ClipboardList size={20} />
            <div>
              <h2>Guided Intake</h2>
              <p>Answer the essentials. Keep it simple and specific.</p>
            </div>
          </div>

          <div className="field-grid">
            <label>
              Age <span>*</span>
              <input
                type="number"
                min="0"
                max="120"
                value={intake.age}
                onChange={(event) => setIntake({ ...intake, age: event.target.value })}
              />
            </label>
            <label>
              Duration <span>*</span>
              <input
                value={intake.duration}
                placeholder="30 minutes, 2 days..."
                onChange={(event) => setIntake({ ...intake, duration: event.target.value })}
              />
            </label>
          </div>

          <label>
            Symptoms <span>*</span>
            <textarea
              rows={6}
              placeholder="Describe what you are feeling, when it started, and what changed."
              value={intake.symptoms}
              onChange={(event) => setIntake({ ...intake, symptoms: event.target.value })}
            />
          </label>

          <div className="severity-group">
            <div className="label-row">
              Severity <span>*</span>
            </div>
            <div className="severity-options">
              {severityOptions.map((option) => (
                <motion.button
                  type="button"
                  key={option.value}
                  className={intake.severity === option.value ? "selected" : ""}
                  onClick={() => setIntake({ ...intake, severity: option.value })}
                  whileHover={{ y: -3 }}
                  whileTap={{ scale: 0.97 }}
                >
                  {intake.severity === option.value && <motion.span className="severity-glow" layoutId="severity-glow" />}
                  <strong>{option.label}</strong>
                  <small>{option.helper}</small>
                </motion.button>
              ))}
            </div>
          </div>

          <div className="optional-band">
            <div className="section-title compact">
              <Info size={18} />
              <div>
                <h3>Optional context</h3>
                <p>These help the agents reason more safely.</p>
              </div>
            </div>
            <label>
              Medical history
              <input value={intake.medical_history} onChange={(event) => setIntake({ ...intake, medical_history: event.target.value })} />
            </label>
            <label>
              Current medications
              <input value={intake.current_medications} onChange={(event) => setIntake({ ...intake, current_medications: event.target.value })} />
            </label>
            <label>
              Allergies
              <input value={intake.allergies} onChange={(event) => setIntake({ ...intake, allergies: event.target.value })} />
            </label>
            <label className="checkbox-row">
              <input
                type="checkbox"
                checked={intake.pregnant_or_immunocompromised}
                onChange={(event) => setIntake({ ...intake, pregnant_or_immunocompromised: event.target.checked })}
              />
              Pregnant or immunocompromised
            </label>
          </div>

          {error && <div className="error-box">{error}</div>}

          <motion.button className="submit-button" disabled={loading || validation.length > 0} whileHover={validation.length ? undefined : { y: -2 }} whileTap={{ scale: 0.99 }}>
            <Send size={18} />
            {loading ? "Running LangGraph..." : "Analyze Symptoms"}
          </motion.button>
        </motion.form>

        <section className="experience-panel">
          <LangGraphFlow intake={intake} result={result} loading={loading} />

          <AnimatePresence mode="wait">
            {!result && !loading && (
              <motion.div className="empty-state" key="empty" initial={{ opacity: 0, y: 14 }} animate={{ opacity: 1, y: 0 }} exit={{ opacity: 0, y: -10 }}>
                <AlertTriangle size={28} />
                <h2>Start with one story</h2>
                <p>Pick a demo card or describe symptoms. The workflow will keep the long trace tucked away until you need it.</p>
              </motion.div>
            )}

            {loading && (
              <motion.div className="loading-card" key="loading" initial={{ opacity: 0, scale: 0.97 }} animate={{ opacity: 1, scale: 1 }} exit={{ opacity: 0, scale: 0.98 }}>
                <div className="spinner" />
                <div>
                  <h2>Agents are coordinating</h2>
                  <p>Running the analyzer, care guidance, and supervisor checks.</p>
                </div>
              </motion.div>
            )}

            {result && (
              <motion.div className={`result-card level-${result.triage_level}`} key="result" initial={{ opacity: 0, y: 20 }} animate={{ opacity: 1, y: 0 }} exit={{ opacity: 0 }}>
                <div className="result-header">
                  <span className="level-badge">{titleCaseLevel(result.triage_level)}</span>
                  <span className="case-id">{result.case_id}</span>
                </div>
                <h2>{result.final.recommendation}</h2>
                <p>{result.final.summary}</p>
                <div className="reason-box">
                  <strong>Why this recommendation?</strong>
                  <span>{result.final.reason}</span>
                </div>
                {nextSteps.length > 0 && (
                  <div className="next-steps">
                    <h3>Next steps</h3>
                    <ul>
                      {nextSteps.slice(0, 4).map((step) => (
                        <li key={step}>{step}</li>
                      ))}
                    </ul>
                  </div>
                )}
                <div className="safety-note">
                  <ShieldCheck size={18} />
                  <span>{result.final.safety_note}</span>
                </div>
              </motion.div>
            )}
          </AnimatePresence>

          <DeveloperTrace result={result} />
        </section>
      </section>
    </main>
  );
}
