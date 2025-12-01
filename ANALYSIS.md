# Glass Box PII Guardrail
## How to Use AI Without Exposing Sensitive Data

**Live Demo**: https://pii-guardrails.vercel.app

---

## The Question

> *Can we leverage AI's capabilities while keeping sensitive information private?*

Organizations want to use AI for productivity—drafting emails, querying internal databases, summarizing documents. But these tasks often involve sensitive data:

```
"Draft an email to john.doe@company.com about his salary of $85,000"
```

Without protection, this query—email address, salary, and all—goes directly to an external AI provider. **The AI sees everything.**

This creates a dilemma: **use AI and risk exposure**, or **protect privacy and miss out on AI's benefits**.

This project explores a third option.

---

## The Challenge

### What Makes This Hard?

Protecting PII in AI applications isn't straightforward:

| Challenge | Why It's Difficult |
|-----------|-------------------|
| **Detection accuracy** | PII appears in many formats (emails, phone numbers, salaries, SSNs) |
| **Real-time performance** | Users expect instant responses, not processing delays |
| **Reversibility** | The AI's response must reference the original values, not placeholders |
| **Trust** | Users need confidence the protection actually works |

Most solutions address detection but ignore the trust problem. Users can't verify what's happening—it's a **black box**.

---

## The Approach

### Reversible Anonymization

The core idea: **replace sensitive data with placeholders before the AI sees it, then restore the original values in the response.**

```
Step 1: User Input
"Draft an email to john.doe@company.com about his salary of $85,000"

Step 2: Detect & Anonymize
"Draft an email to <EMAIL_1> about his salary of <SALARY_1>"
       ↓
       Mapping stored: {<EMAIL_1>: "john.doe@company.com", <SALARY_1>: "$85,000"}

Step 3: AI Processes (sees only placeholders)
"Dear <EMAIL_1>, I wanted to discuss the compensation of <SALARY_1>..."

Step 4: Deanonymize Response
"Dear john.doe@company.com, I wanted to discuss the compensation of $85,000..."

Step 5: User Sees Original Values Restored
```

The AI never sees the actual email or salary—only generic placeholders.

### The "Glass Box" Difference

We add transparency by showing this process in real-time through a split-screen interface:

| Left Panel | Right Panel |
|------------|-------------|
| Normal chat experience | Inspector showing: |
| User sees restored values | • What PII was detected |
| | • The anonymized prompt sent to AI |
| | • The mapping table |
| | • Processing metrics |

This transforms "trust us" into **"verify yourself"**—users can see exactly what protection is applied.

---

## The Experiment

### Research Question

*Which PII detection method provides the best balance of accuracy, speed, and reliability?*

### Methods Tested

We evaluated three fundamentally different approaches:

| Detector | Type | How It Works |
|----------|------|--------------|
| **Presidio** | Hybrid | Combines regex patterns with NER (Named Entity Recognition) |
| **GLiNER** | Neural | Transformer model that identifies entities without task-specific training |
| **Llama Guard** | LLM | Large language model prompted to extract PII (experimental) |

### Datasets

| Dataset | Size | Purpose |
|---------|------|---------|
| `golden_set` | 100 | Core benchmark—curated real-world PII patterns |
| `synthetic_dataset` | 300 | Bulk evaluation—Faker-generated diverse examples |
| `adversarial_dataset` | 100 | Robustness testing—intentionally tricky cases |
| `test_scenarios` | 20 | Quick validation—hand-crafted edge cases |

**Total: 520 test cases** covering 10 PII types.

### Metrics

- **F1 Score**: Balance of precision (accuracy) and recall (completeness)
- **Leakage Rate**: Percentage of PII that slips through undetected (critical for security)
- **Latency**: Processing time added to each query

### Interactive Benchmark

Explore the benchmark results interactively at **[/comparison](https://pii-guardrails.vercel.app/comparison)**—filter by dataset, compare detectors head-to-head, and view detailed metrics including F1 scores, latency distributions, and leakage rates.

---

## The Results

### Which Detector Won?

**Presidio** emerged as the clear choice for production use:

| Metric | Presidio | GLiNER | Llama Guard |
|--------|----------|--------|-------------|
| **F1 Score** | **89%** | 78% | 0% |
| **Leakage Rate** | **6%** | 27% | N/A |
| **Latency** | **2-3ms** | 30-200ms | 1000+ms |
| **External API** | No | No | Yes |

### But GLiNER Has Strengths

The neural approach excels where regex fails:

| Entity Type | Presidio | GLiNER | Insight |
|-------------|----------|--------|---------|
| EMAIL | **100%** | 85% | Regex patterns work perfectly |
| SSN | 67% | **100%** | Neural understands context better |
| Adversarial | 58% | **85%** | Obfuscated PII needs semantic understanding |

### Llama Guard Failed

Llama Guard scored **0% across all datasets**. Why?

It was designed for **safety classification** ("is this content safe?"), not **entity extraction** ("where is the PII?"). Prompting it to return structured positions doesn't work.

**Lesson**: LLMs aren't always the answer. Specialized tools often outperform for specific tasks.

---

## The Trade-offs

### Speed vs. Accuracy

| Approach | Latency | F1 Score | Best For |
|----------|---------|----------|----------|
| Presidio only | 2-3ms | 89% | Real-time applications |
| GLiNER only | 30-200ms | 78% | Batch processing |
| Both (ensemble) | ~200ms | Higher | Offline analysis |

For interactive applications, **Presidio's 2-3ms overhead is imperceptible**.

### What 6% Leakage Means

Presidio misses ~6% of PII. Is that acceptable?

| Context | 6% Leakage | Assessment |
|---------|------------|------------|
| Internal productivity tools | ~6 items per 100 slip through | Often acceptable |
| Healthcare (HIPAA) | 6 patient records exposed per 100 | Too high |
| Financial compliance | 6 account numbers leaked per 100 | Too high |

**For high-compliance environments**: Add a human review step or use ensemble detection.

### The Transparency Trade-off

Showing the mapping table in the browser means it's technically visible to users. This is intentional—transparency is the point. But for deployments where even the mapping must be hidden, server-side deanonymization is needed.

---

## Key Insights

### 1. No Perfect Detector Exists

Different tools excel at different PII types. The ideal system would combine:
- **Presidio** for emails, phone numbers, credit cards (pattern-based)
- **GLiNER** for SSNs and adversarial robustness (semantic understanding)

### 2. Leakage Rate > F1 Score

For security, what matters is: **how much PII gets through undetected?**

A detector with 89% F1 but 6% leakage is better than one with 85% F1 but 27% leakage.

### 3. Latency Must Be Invisible

Users expect instant responses. Adding 2-3ms (Presidio) is invisible. Adding 200ms (GLiNER) is noticeable. Adding 1000ms+ (Llama Guard) breaks the experience.

### 4. Transparency Builds Trust

The "Glass Box" approach converts skeptics. When users can **see** their data being protected, they trust the system more than when told "we protect your data."

### 5. Right Tool for the Job

Llama Guard (billions of parameters) scored 0%. Presidio (regex + small NER model) scored 89%. More powerful ≠ more effective.

---

## The Answer

> *Can we use AI without exposing sensitive data?*

**Yes—with reversible anonymization.**

The approach works: Presidio achieves 89% F1 with only 2-3ms overhead. The remaining 6% leakage can be addressed through:
- Ensemble detection for high-security contexts
- Human review for compliance-critical applications
- Domain-specific regex patterns for known PII formats

The "Glass Box" UI adds unique value: users can verify protection themselves, building trust that no amount of documentation can match.

### Recommendations

| Use Case | Recommendation |
|----------|----------------|
| **Real-time applications** | Presidio (89% F1, 2ms latency) |
| **High-security batch** | Presidio + GLiNER validation |
| **Compliance audit** | Glass Box UI for transparency |
| **SSN-heavy data** | GLiNER for SSN-specific detection |

---

## Future Research & Improvements

This POC demonstrates the core concept, but several areas warrant further exploration:

### Detection Improvements

| Gap | Current State | Future Direction |
|-----|---------------|------------------|
| **Ensemble detection** | Single detector at a time | Combine Presidio (speed) + GLiNER (robustness) with voting |
| **Confidence thresholding** | All detections treated equally | Filter by confidence score, flag low-confidence for review |
| **Adversarial robustness** | 58% F1 on obfuscated PII | Train on adversarial examples, add normalization layer |
| **Context awareness** | Position-based detection only | Consider surrounding context ("call me at 555-1234" vs "order #555-1234") |

### Architecture Improvements

| Gap | Current State | Future Direction |
|-----|---------------|------------------|
| **Streaming deanonymization** | Waits for full response | Real-time placeholder replacement during stream |
| **Session persistence** | Mapping lost on refresh | Store mappings in Redis/database for continuity |
| **Server-side deanonymization** | Client-side only (visible in browser) | Option for server-side restoration for higher security |
| **Scale testing** | Single-user demo | Load testing, concurrent session handling |

### Usability Improvements

| Gap | Current State | Future Direction |
|-----|---------------|------------------|
| **False positive handling** | No way to correct mistakes | Allow users to "unmark" incorrectly detected PII |
| **Custom entity types** | Fixed 10 types | User-defined patterns (e.g., internal employee IDs) |
| **Multi-language** | English only | Extend to other languages with localized NER models |
| **Audit logging** | Visual UI only | Persistent audit trail for compliance |

### Open Research Questions

1. **What's the optimal ensemble strategy?** - Weighted voting, confidence-based selection, or entity-type routing?

2. **How to handle partial matches?** - When detector finds "John" but ground truth is "John Doe"

3. **Can we achieve <1% leakage?** - What combination of techniques would be needed for high-compliance environments?

4. **How does performance degrade with input length?** - Current testing uses short prompts; behavior at 10K+ tokens unknown

5. **What's the user trust threshold?** - At what leakage rate do users lose confidence in the system?

---

## Learn More

### Key Concepts

1. **[Named Entity Recognition (NER)](https://huggingface.co/learn/nlp-course/chapter7/7)**
   How AI identifies "entities" like names and organizations in text.

2. **[Retrieval-Augmented Generation (RAG)](https://www.pinecone.io/learn/retrieval-augmented-generation/)**
   Architecture that combines document retrieval with LLM generation.

3. **[Precision vs Recall](https://developers.google.com/machine-learning/crash-course/classification/precision-and-recall)**
   The trade-off between finding all PII (recall) and avoiding false alarms (precision).

4. **[PII Detection Patterns](https://cloud.google.com/dlp/docs/infotypes-reference)**
   Google's reference for PII types and detection approaches.

### Tools Used

5. **[Microsoft Presidio](https://microsoft.github.io/presidio/)**
   The core anonymization engine powering this POC.

6. **[GLiNER](https://arxiv.org/abs/2311.08526)**
   Zero-shot NER model for semantic entity detection.

7. **[Vercel AI SDK](https://sdk.vercel.ai/docs)**
   Framework for streaming AI responses.

---

## Summary

| Question | Answer |
|----------|--------|
| Can we protect PII in AI applications? | Yes, via reversible anonymization |
| Which detector works best? | Presidio (89% F1, 2ms latency) |
| What's the security trade-off? | 6% leakage—acceptable for most use cases |
| How do we build user trust? | Glass Box transparency—show, don't tell |

The project demonstrates that **privacy and AI capability are not mutually exclusive**. With the right approach, organizations can adopt AI tools while maintaining control over sensitive data.

---

| Aspect | Traditional Approach | Glass Box Approach |
|--------|---------------------|-------------------|
| **Visibility** | Hidden processing | Real-time inspection |
| **Trust Model** | "Trust us" | "Verify yourself" |
| **Debugging** | Log files | Visual UI |
| **User Education** | None | Built-in |
