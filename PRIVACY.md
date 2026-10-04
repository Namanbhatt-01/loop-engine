# Privacy Policy

**Effective Date:** October 4, 2026

Loop Engine Core is an open-source autonomous development harness and Model Context Protocol (MCP) server. This privacy policy outlines data handling practices for users and automated integrations (including Claude Desktop, Cursor, and OpenAI tools).

## 1. Local-First Architecture
Loop Engine Core runs entirely on your local machine or self-hosted environment. It does not collect, transmit, or store personal telemetry or usage metrics to external servers operated by the maintainers.

## 2. Code and File Data
* All source code analysis, file reading, and test execution occur locally within your specified workspace directory.
* File access is strictly bounded by path confinement rules defined in `Loopfile.yaml`, preventing access to external or protected directories.

## 3. Third-Party Model Providers
* If you configure remote model providers (such as Google Gemini API), prompt contents and error diagnostics are transmitted directly between your machine and that provider under their respective terms and privacy policies.
* When running local models via Ollama, all inference remains 100% offline and no external network calls are made.

## 4. Environment Variables and Credentials
* Environment variables (such as `LOOP_PORT` or `GEMINI_API_KEY`) stay on your local machine and are never logged, exported, or exfiltrated.

## 5. Contact
For questions regarding security or privacy, refer to [SECURITY.md](SECURITY.md) or open an issue on GitHub.
