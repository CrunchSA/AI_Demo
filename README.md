# 🔒 Thales CipherTrust AI Perimeter

A **zero-trust, enterprise-grade conversational AI application** that demonstrates how to secure local Large Language Models (LLMs) using Thales CipherTrust technology. This solution protects sensitive data (PII, SSNs, credentials) at every stage of the AI inference pipeline—at rest, in motion, and during generative processing.

## 🎯 Key Features

- **Data-at-Rest Protection**: CTE (Transparent Encryption) isolates filesystem-level data from rogue admins
- **Data-in-Motion Protection**: CRDP (RESTful Data Protection) encrypts/decrypts PII in real time
- **Zero-Trust LLM Processing**: Ollama engine never sees plaintext sensitive data
- **Identity-Based Access Control**: Per-user masking/redaction of AI outputs based on RBAC policies
- **Format-Preserving Tokenization (FPT)**: Structurally valid fake SSNs maintain semantic meaning for embeddings
- **Audit & Compliance Logging**: Real-time HTTP wire logs show all CRDP transactions
- **Conversational Memory**: Stateful chat history with tokenized context injection

## 📋 Prerequisites

### Local Development
- Docker & Docker Compose
- Python 3.9+
- Streamlit
- Ollama (or Docker image)

### Production Deployment (RKE2 Kubernetes)
- RKE2 cluster with CTE storage provisioning
- Thales CipherTrust Manager (with CRDP policies configured)
- Container runtime (containerd)
- Kubernetes secrets for CRDP API endpoints

## 🚀 Quick Start

### 1. Clone & Setup

```bash
git clone https://github.com/yourusername/ciphertrust-ai-perimeter.git
cd ciphertrust-ai-perimeter

# Copy environment template
cp .env.example .env

# Create data directory for knowledge base
mkdir -p data
```

### 2. Configure Environment

Edit `.env` with your infrastructure values:

```bash
# Point to your Thales CRDP service
CRDP_URL=http://your-crdp-host:8090/v1
CRDP_POLICY=your-policy-name

# Point to your Ollama or compatible LLM
OLLAMA_URL=http://your-ollama-host:11434/api/chat
MODEL_NAME=qwen2.5:1.5b
```

### 3. Add Knowledge Base

Create `data/enterprise_knowledge.txt` with sample corporate data:

```
Jane Doe is our designated internal system compliance auditor.
Her secure identifier number is 000-88-9999.
She has full access to all internal documentation.
```

### 4. Run Locally with Docker Compose

```bash
docker-compose up --build
```

Visit [http://localhost:8501](http://localhost:8501) in your browser.

### 5. Test the Demo

1. **Select Identity**: Use the sidebar dropdown to switch between "Alice", "Bob", or "Malicious_Actor"
2. **Ask a Question**: Type: "Who is our internal compliance auditor and what is their SSN?"
3. **Review Logs**: Expand the "Raw CRDP API Wire Logs" to see:
   - Protect transactions (prompt sanitization)
   - Reveal transactions (identity-based decryption)
   - Access denial messages for unauthorized users

## 🏗️ Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                   Browser / End User                         │
└─────────────┬───────────────────────────────────────────────┘
              │
              ▼
┌─────────────────────────────────────────────────────────────┐
│  Streamlit UI Pod (Secure Middleware Layer)                 │
│  ┌─────────────┐  ┌──────────────┐  ┌─────────────────┐    │
│  │   Phase 1   │  │   Phase 3    │  │  Audit Console  │    │
│  │  Ingestion  │  │   Reveal     │  │   + Wire Logs   │    │
│  │  Interception│  │ Interception │  │                 │    │
│  └──────┬──────┘  └──────┬───────┘  └─────────────────┘    │
│         │                │                                    │
│  ┌──────▼────────────────▼──────────┐                       │
│  │     token_version_vault (Cache)  │                       │
│  └────────────────────────────────────┘                      │
└─────┬──────────────────────┬──────────────────────┬─────────┘
      │                      │                      │
  CRDP /protect          Ollama /api/chat       CRDP /reveal
      │                      │                      │
      ▼                      ▼                      ▼
┌──────────────┐   ┌──────────────┐   ┌──────────────┐
│  Thales CRDP │   │    Ollama    │   │  Thales CRDP │
│  (Protect)   │   │    (Infer)   │   │   (Reveal)   │
└──────────────┘   └──────────────┘   └──────────────┘
      │                      │              │
      ▼                      ▼              ▼
   Token:              Token Input:    Cleartext Output:
   Tkn-7x9P...        Tkn-7x9P...      000-88-9999 (Alice)
                                       XXX-XX-9999 (Bob)
                                       [Access Denied] (Rogue)
```

### Data Flow Phases

**Phase 1 & 2: Context Loading & Prompt/Knowledge Sanitization**
- Middleware reads enterprise knowledge base from CTE volume  
- Middleware intercepts the initial user prompt and calls CRDP `/protect` to sanitize any sensitive data before it moves over the network
- Middleware also calls CRDP `/protect` to sanitize the loaded knowledge base context
- Sanitized RAG context (with fake tokens like "572-39-1148") and the sanitized user prompt are injected into the LLM system prompt

**Phase 3: LLM Inference (Untrusted Zone)**
- Ollama processes only the tokenized knowledge base and prompt
- Ollama generates response containing only token values (e.g., "572-39-1148")

**Phase 4: Output Authorization & Reveal**
- Middleware intercepts Ollama's tokenized response
- Middleware calls CRDP `/reveal` on the detected tokens with the user's identity
- Result: Cleartext (Alice), Masked (Bob), or Denied (Rogue) - based on policy evaluation

## 🔐 Security Model

### Ollama Pod (Untrusted Zone)
- ✅ Only processes tokenized/fake data
- ❌ Never communicates with CRDP
- ❌ No access to encryption keys
- ❌ No plaintext PII in memory

### Streamlit Pod (Trusted Middleware)
- ✅ All CRDP communication happens here
- ✅ Manages token-to-cleartext mappings
- ✅ Enforces identity-based policies
- ✅ Audits all wire transactions

### Thales CipherTrust (Key Management)
- ✅ Holds encryption keys and policies
- ✅ Evaluates access control rules
- ✅ Returns cleartext only to authorized identities
- ✅ Logs all reveal operations

## 📊 Demo Script

See [DEMO_SCRIPT.md](DEMO_SCRIPT.md) for a complete live demonstration walkthrough with:
- Act 1: Data-at-Rest Isolation (Rogue Admin Challenge)
- Act 2: Zero-Trust Context Ingestion (Alice Auditor Pass)
- Act 3: Identity-Based Policy Enforcement (Bob Agent Pass)
- Act 4: Stateful Memory Validation (Extraction Defense)

## 🎬 Deployment

### Local Development
```bash
docker-compose up --build
```

### Kubernetes/RKE2 Production
See [DEPLOYMENT.md](DEPLOYMENT.md) for:
- CTE volume provisioning
- Persistent Volume Claims (PVCs)
- Service mesh configuration
- Network policies for CRDP endpoints
- Secrets management for API credentials

## 🛠️ Configuration

### Environment Variables

| Variable | Default | Purpose |
|----------|---------|---------|
| `CRDP_URL` | `http://crdp-service.default.svc.cluster.local:8090/v1` | Thales CRDP API endpoint |
| `CRDP_POLICY` | `llm-ssn-tokenize-policy` | Policy name in CipherTrust Manager |
| `OLLAMA_URL` | `http://ollama-service.llm-security-demo.svc.cluster.local:11434/api/chat` | Ollama chat API endpoint |
| `MODEL_NAME` | `qwen2.5:1.5b` | LLM model to use |
| `KNOWLEDGE_PATH` | `/data/enterprise_knowledge.txt` | Path to RAG knowledge base |

### Thales CipherTrust Manager Setup

1. **Create a Data Protection Policy**:
   - Policy Name: `llm-ssn-tokenize-policy`
   - Pattern: SSN format (`\d{3}-\d{2}-\d{4}`)
   - Transformation: Tokenize or Mask

2. **Define User Sets**:
   ```
   Alice (Compliance Auditor)
     - Full Access to all data
   
   Bob (Support Agent)
     - Masked/redacted access
   
   Malicious_Actor (Unauthorized)
     - No access / Deny all
   ```

3. **Configure Access Policies**:
   - Bind username field to User Set evaluation
   - Set reveal behavior per user role

## 📝 File Structure

```
ciphertrust-ai-perimeter/
├── app.py                      # Main Streamlit application
├── dockerfile                  # Container image definition
├── docker-compose.yml          # Local orchestration
├── requirements.txt            # Python dependencies
├── .env.example                # Environment template
├── .gitignore                  # Git ignore rules
├── README.md                   # This file
├── ARCHITECTURE.md             # Technical deep dive
├── DEPLOYMENT.md               # RKE2 deployment guide
├── DEMO_SCRIPT.md              # Live demo walkthrough
├── LICENSE                     # Open source license
├── data/
│   └── enterprise_knowledge.txt # Example knowledge base (git-ignored)
└── sample_knowledge.txt        # Template for knowledge base
```

## 🔍 Troubleshooting

### CRDP Connection Errors
```
[CRDP Network Failure: Connection refused]
```
**Solution**: Verify `CRDP_URL` is reachable:
```bash
curl http://your-crdp-host:8090/v1/protect
```

### Ollama Model Not Found
```
error: model 'qwen2.5:1.5b' not found
```
**Solution**: Pull the model first:
```bash
docker exec ollama-llm-service ollama pull qwen2.5:1.5b
```

### All Users See Masked Data
**Solution**: Verify access policies in Thales CipherTrust Manager. Check that "Alice" user set is configured for full reveal access.

### Token Version Mismatch
```
[Access Denied: 400]
```
**Solution**: Ensure `external_version` is properly captured during protect phase. Check CRDP policy configuration supports versioning.

## 📚 Additional Resources

- [Thales CipherTrust Manager Docs](https://supportportal.thalesgroup.com/csm)
- [Ollama Model Library](https://ollama.ai/library)
- [Streamlit Documentation](https://docs.streamlit.io)
- [Kubernetes RKE2 Docs](https://docs.rke2.io)

## 🤝 Contributing

Contributions welcome! Please:
1. Fork the repository
2. Create a feature branch (`git checkout -b feature/amazing-feature`)
3. Commit changes (`git commit -m 'Add amazing feature'`)
4. Push to branch (`git push origin feature/amazing-feature`)
5. Open a Pull Request

## 📄 License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## 🎓 Author

Built as a demonstration of zero-trust AI security architecture using Thales CipherTrust technology.

---

**Last Updated**: 2026-07-23
**Status**: Production-Ready Demo
