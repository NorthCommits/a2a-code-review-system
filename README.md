# A2A Code Review System

A comprehensive multi-agent code review and quality assurance system that implements the **Agent-to-Agent (A2A) Protocol** as specified by Google Cloud. This Streamlit-based application uses multiple specialized AI agents to analyze code quality, identify issues, and suggest improvements.

## 🏗️ Architecture

The system follows a multi-agent architecture with clear separation of concerns:

```
┌─────────────────────────────────────────────────────────────────────┐
│                        STREAMLIT USER INTERFACE                      │
└──────────────────────────────┬──────────────────────────────────────┘
                               │
                               ▼
┌─────────────────────────────────────────────────────────────────────┐
│                     COORDINATOR AGENT (Client Agent)                 │
│  • Receives code from UI                                             │
│  • Queries Agent Registry for available agents                       │
│  • Distributes tasks via A2A Protocol (JSON-RPC 2.0)               │
│  • Aggregates results from all remote agents                         │
│  • Returns consolidated report to UI                                 │
└──────────────────────────────┬──────────────────────────────────────┘
                               │
                               ▼
┌─────────────────────────────────────────────────────────────────────┐
│                  AGENT REGISTRY & DISCOVERY SERVICE                  │
│  • Maintains list of all available remote agents                     │
│  • Stores agent capabilities and endpoints                           │
│  • Provides discovery API for coordinator                            │
│  • Matches tasks to appropriate agents                               │
└──────────────────────────────┬──────────────────────────────────────┘
                               │
                               ▼
┌─────────────────────────────────────────────────────────────────────┐
│                      A2A PROTOCOL LAYER                              │
│  • JSON-RPC 2.0 Handler (HTTPS)                                     │
│  • Webhook Manager (Async)                                          │
│  • Server-Sent Events (SSE) for Streaming                           │
└──────────────────────────────┬──────────────────────────────────────┘
                               │
                ┌──────────────┼──────────────┐
                │              │              │
                ▼              ▼              ▼
┌──────────────────┐ ┌──────────────────┐ ┌──────────────────┐
│  Syntax Analysis │ │ Security Scanner │ │ Performance      │
│  Remote Agent    │ │ Remote Agent     │ │ Analyzer Agent   │
└──────────────────┘ └──────────────────┘ └──────────────────┘

       ▼                      ▼                      ▼
┌──────────────────┐ ┌──────────────────────────────────────┐
│  Documentation   │ │  Test Coverage Remote Agent          │
│  Quality Agent   │ │                                      │
└──────────────────┘ └──────────────────────────────────────┘
```

## 🚀 Features

### Multi-Agent Analysis
- **Syntax & Style Analysis**: PEP 8 compliance, linting, formatting
- **Security Scanning**: Vulnerability detection, SQL injection, XSS
- **Performance Analysis**: Complexity analysis, optimization suggestions
- **Documentation Quality**: Docstring validation, comment analysis
- **Test Coverage**: Coverage analysis, test quality assessment

### A2A Protocol Implementation
- **JSON-RPC 2.0**: Standardized agent communication
- **Agent Registry**: Centralized agent discovery and management
- **Health Monitoring**: Real-time agent status tracking
- **Load Balancing**: Intelligent task distribution
- **Async Support**: Webhooks and Server-Sent Events

### User Interface
- **Streamlit Web App**: Clean, intuitive interface
- **Real-time Progress**: Live analysis progress tracking
- **Comprehensive Results**: Detailed findings with severity levels
- **Code Correction**: Auto-fixed code suggestions
- **Export Options**: JSON, corrected code, and summary reports

## 📁 Project Structure

```
a2a-code-review-system/
├── app.py                          # Main Streamlit application entry point
├── requirements.txt                # Python dependencies
├── README.md                       # Project documentation
├── .gitignore                      # Git ignore file

├── a2a_protocol/                   # ⭐ A2A Protocol Core Implementation
│   ├── __init__.py
│   ├── protocol_handler.py         # JSON-RPC 2.0 implementation
│   ├── message_schema.py           # A2A message format definitions
│   ├── transport.py                # HTTPS transport layer
│   ├── webhook_handler.py          # Async webhook management
│   └── sse_handler.py              # Server-Sent Events for streaming

├── registry/                       # ⭐ Agent Registry & Discovery Service
│   ├── __init__.py
│   ├── agent_registry.py           # Central agent registry
│   ├── discovery_service.py        # Agent discovery logic
│   ├── registry_config.json        # Available agents configuration
│   └── capability_matcher.py       # Match tasks to agent capabilities

├── agents/                         # ⭐ Agent Implementations
│   ├── __init__.py
│   │
│   ├── base/                       # Base classes for all agents
│   │   ├── __init__.py
│   │   ├── base_agent.py           # Abstract base agent class
│   │   ├── client_agent.py         # Base for client agents
│   │   └── remote_agent.py         # Base for remote agents
│   │
│   ├── coordinator/                # ⭐ Coordinator Agent (Client Agent)
│   │   ├── __init__.py
│   │   ├── coordinator.py          # Main coordinator implementation
│   │   ├── task_distributor.py     # Distributes tasks to remote agents
│   │   ├── result_aggregator.py    # Aggregates results from all agents
│   │   └── orchestration_engine.py # Workflow orchestration logic
│   │
│   ├── remote/                     # ⭐ Remote Specialized Agents
│   │   ├── __init__.py
│   │   ├── syntax_agent.py         # Remote agent for syntax analysis
│   │   ├── security_agent.py       # Remote agent for security scanning
│   │   ├── performance_agent.py    # Remote agent for performance analysis
│   │   ├── documentation_agent.py  # Remote agent for doc quality
│   │   └── test_coverage_agent.py  # Remote agent for test coverage
│   │
│   └── internal/                   # ⭐ Internal Helper Agents (Optional)
│       ├── __init__.py
│       ├── preprocessing_agent.py  # Preprocesses code before analysis
│       ├── validation_agent.py     # Validates input code
│       └── formatting_agent.py     # Formats output results

├── analyzers/                      # Core Analysis Logic (Used by Remote Agents)
│   ├── __init__.py
│   ├── syntax_analyzer.py          # Syntax analysis algorithms
│   ├── security_analyzer.py        # Security scanning algorithms
│   ├── performance_analyzer.py     # Performance analysis algorithms
│   ├── documentation_analyzer.py   # Documentation check algorithms
│   └── test_analyzer.py            # Test coverage algorithms

├── utils/                          # Utility Functions
│   ├── __init__.py
│   ├── code_parser.py              # Parse and validate code
│   ├── report_generator.py         # Generate analysis reports
│   ├── code_fixer.py               # Auto-fix common issues
│   └── logger.py                   # Logging utility

├── ui/                             # Streamlit UI Components
│   ├── __init__.py
│   ├── main_interface.py           # Main UI layout
│   ├── components.py               # Reusable UI components
│   └── styles.py                   # Custom CSS styling

├── storage/                        # Session & State Management
│   ├── __init__.py
│   ├── session_manager.py          # Streamlit session state manager
│   └── file_handler.py             # File upload/download handling

├── config/                         # Configuration Files
│   ├── __init__.py
│   ├── settings.py                 # Application settings
│   └── agent_endpoints.py          # Agent endpoint configurations

├── tests/                          # Testing Suite
│   ├── __init__.py
│   ├── test_protocol/
│   │   ├── test_a2a_handler.py
│   │   └── test_message_schema.py
│   ├── test_registry/
│   │   └── test_discovery.py
│   ├── test_agents/
│   │   ├── test_coordinator.py
│   │   ├── test_remote_agents.py
│   │   └── test_internal_agents.py
│   └── sample_code/
│       ├── good_code.py
│       ├── bad_code.py
│       └── vulnerable_code.py

└── docs/                           # Documentation
    ├── A2A_PROTOCOL.md             # A2A protocol explanation
    ├── ARCHITECTURE.md             # System architecture
    ├── AGENT_GUIDE.md              # How to create new agents
    ├── REGISTRY_GUIDE.md           # Registry usage guide
    └── DEPLOYMENT.md               # Deployment instructions
```

## 🛠️ Installation

### Prerequisites
- Python 3.8+
- OpenAI API key

### Setup

1. **Clone the repository**
   ```bash
   git clone <repository-url>
   cd a2a-code-review-system
   ```

2. **Create virtual environment**
   ```bash
   python -m venv venv
   source venv/bin/activate  # On Windows: venv\Scripts\activate
   ```

3. **Install dependencies**
   ```bash
   pip install -r requirements.txt
   ```

4. **Set up environment variables**
   ```bash
   # Create .env file
   echo "OPENAI_API_KEY=your_openai_api_key_here" > .env
   ```

5. **Run the application**
   ```bash
   streamlit run app.py
   ```

## 🎯 Usage

### Basic Usage

1. **Open the application** in your browser (typically `http://localhost:8501`)

2. **Enter your code** in the Code Analysis tab:
   - Paste your code in the text area
   - Or load sample code for demonstration

3. **Configure analysis options** in the sidebar:
   - Select programming language
   - Choose analysis types (syntax, security, performance, documentation, test coverage)

4. **Run analysis** by clicking "Analyze Code"

5. **View results** in the Results tab:
   - Summary with quality score
   - Detailed observations, errors, and suggestions
   - Corrected code (if available)
   - Download options for results

### Advanced Features

- **System monitoring** in the System tab
- **Agent status** and health monitoring
- **Analysis history** tracking
- **Export capabilities** (JSON, corrected code, summary reports)

## 🔧 Configuration

### Agent Registry Configuration

Edit `registry/registry_config.json` to configure available agents:

```json
{
  "agents": [
    {
      "agent_id": "syntax-analyzer-001",
      "name": "Syntax Analysis Agent",
      "capabilities": ["syntax_check", "linting", "style_validation"],
      "endpoint": "http://localhost:5001/analyze",
      "status": "active"
    }
  ]
}
```

### Analysis Configuration

Modify analysis types and priorities in the coordinator agent configuration.

## 🧪 Testing

Run the test suite:

```bash
# Run all tests
pytest

# Run specific test categories
pytest tests/test_protocol/
pytest tests/test_registry/
pytest tests/test_agents/
```

## 📊 A2A Protocol Compliance

This system implements the A2A protocol with:

- **JSON-RPC 2.0** for standardized communication
- **Agent Registry** for service discovery
- **Health Monitoring** for agent status tracking
- **Capability Matching** for intelligent task distribution
- **Async Support** via webhooks and Server-Sent Events

## 🤝 Contributing

1. Fork the repository
2. Create a feature branch (`git checkout -b feature/amazing-feature`)
3. Commit your changes (`git commit -m 'Add amazing feature'`)
4. Push to the branch (`git push origin feature/amazing-feature`)
5. Open a Pull Request

## 📝 License

This project is licensed under the MIT License - see the LICENSE file for details.

## 🙏 Acknowledgments

- Google Cloud A2A Protocol specification
- OpenAI for LLM capabilities
- Streamlit for the web interface
- FastAPI for agent communication

## 📞 Support

For support and questions:
- Create an issue in the repository
- Check the documentation in the `docs/` folder
- Review the architecture diagrams and protocol specifications

---

**Built with ❤️ using the A2A Protocol for multi-agent coordination**
