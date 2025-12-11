# CardioXNet Documentation 📚

[![Back to README](../README.md)](../README.md)

Welcome to the CardioXNet documentation! This comprehensive guide covers everything you need to understand, install, configure, and use the CardioXNet platform for cardiac repair pathway discovery.

---

## 🚀 Quick Start

Get up and running quickly:

- **[Quick Start Guide](../QUICK_START_GUIDE.md)** - Step-by-step installation and setup
- **[README](../README.md)** - Overview, features, and basic usage
- **[Docker Setup](../README.md#docker-recommended)** - One-command deployment

---

## 📖 User Guides

### For Researchers & Analysts

| Guide | Description | Level |
|-------|-------------|-------|
| **[Workflow Description](../WORKFLOW_DESCRIPTION.md)** | Complete NETS pipeline explanation | Intermediate |
| **[Configuration Guide](CONFIGURATION.md)** | Detailed configuration options | Advanced |
| **[API Documentation](http://localhost:8000/docs)** | Interactive REST API reference | All Levels |

### For Developers

| Guide | Description | Level |
|-------|-------------|-------|
| **[Contributing](../README.md#contributing)** | Development setup and contribution guidelines | Advanced |
| **[Code Quality](../README.md#code-quality)** | Testing and linting procedures | Advanced |
| **[Architecture](../README.md#architecture)** | System design and data flow | Advanced |

---

## 🛠️ Configuration & Setup

### Core Configuration
- **[Configuration Guide](CONFIGURATION.md)** - Complete configuration reference
- **[Environment Variables](CONFIGURATION.md#environment-variable-overrides)** - Runtime configuration
- **[Docker Configuration](../docker-compose.yml)** - Container setup

### Data Sources
- **[STRING Database Setup](../README.md#data-setup)** - Protein interaction data
- **[GeneMANIA Integration](../README.md#genemania-local-data-optional)** - Functional association data
- **[API Endpoints](CONFIGURATION.md#api-configuration)** - External service configuration

---

## 🔬 Scientific Background

### NETS Algorithm
- **[Algorithm Overview](../WORKFLOW_DESCRIPTION.md#complete-stage-by-stage-description)** - Pipeline stages explained
- **[NES Scoring](../WORKFLOW_DESCRIPTION.md#stage-3-final-nes-scoring)** - Novelty & Evidence Scoring
- **[Statistical Methods](../WORKFLOW_DESCRIPTION.md#statistical-rigor)** - FDR correction and validation

### Data Integration
- **[Multi-Database Strategy](../README.md#data-sources)** - Pathway database integration
- **[Literature Mining](../WORKFLOW_DESCRIPTION.md#stage-2b-secondary-pathway-discovery)** - PubMed integration
- **[Network Analysis](../WORKFLOW_DESCRIPTION.md#stage-4-topology-analysis-validation)** - Graph-based validation

---

## 🐛 Troubleshooting & Support

### Common Issues
- **[Troubleshooting Guide](../README.md#troubleshooting)** - Solutions to common problems
- **[Configuration Issues](CONFIGURATION.md#troubleshooting-configuration)** - Config-specific problems
- **[Performance Tuning](CONFIGURATION.md#performance-tuning)** - Optimization strategies

### Getting Help
- **[GitHub Issues](https://github.com/yourusername/cardioxnet/issues)** - Bug reports and feature requests
- **[Discussions](https://github.com/yourusername/cardioxnet/discussions)** - Community support
- **[Email Support](../README.md#support)** - Direct contact

---

## 📊 API Reference

### REST API
- **[Interactive Docs](http://localhost:8000/docs)** - Swagger UI documentation
- **[Alternative Docs](http://localhost:8000/redoc)** - ReDoc format
- **[API Examples](../README.md#api-usage)** - Code samples

### WebSocket API
- **Real-time Updates** - Live progress monitoring
- **Event Streaming** - Pipeline status notifications

---

## 🔧 Development Resources

### Codebase
- **[Project Structure](../README.md#architecture)** - Code organization
- **[Dependencies](../requirements.txt)** - Python packages
- **[Frontend Stack](../frontend/package.json)** - React/TypeScript setup

### Testing
- **[Unit Tests](../README.md#running-tests)** - Test execution
- **[Code Coverage](../README.md#code-quality)** - Quality metrics
- **[Integration Tests](../tests/)** - End-to-end validation

---

## 📈 Advanced Topics

### Performance Optimization
- **[Scaling Configuration](CONFIGURATION.md#high-throughput-analysis)** - Large-scale analysis
- **[Memory Management](CONFIGURATION.md#memory-constrained-environments)** - Resource optimization
- **[Caching Strategies](../README.md#data-setup)** - Data persistence

### Customization
- **[Custom Databases](../README.md#genemania-local-data-optional)** - Adding new data sources
- **[Pipeline Extensions](../WORKFLOW_DESCRIPTION.md#algorithmic-improvements)** - Modifying the pipeline
- **[Output Formats](../README.md#comprehensive-reports)** - Custom report generation

---

## 📚 Research & Citation

### Scientific Background
- **[NETS Methodology](../WORKFLOW_DESCRIPTION.md#nets-methodology)** - Algorithm foundation
- **[Validation Studies](../WORKFLOW_DESCRIPTION.md#validation-approach)** - Performance evaluation
- **[Cardiac Context](../WORKFLOW_DESCRIPTION.md#cardiac-specific-filtering)** - Disease-specific adaptations

### Citation Information
- **[Citation Format](../README.md#citation)** - How to cite CardioXNet
- **[Research Applications](../README.md#features)** - Use cases and applications
- **[Algorithmic Improvements](ALGORITHMIC_IMPROVEMENTS.md)** - Recent enhancements

---

## 🗺️ Site Map

```
CardioXNet Documentation/
├── 📄 README.md (Main project page)
├── 🚀 QUICK_START_GUIDE.md (Installation guide)
├── 📋 docs/
│   ├── 📖 index.md (This file)
│   └── 🔧 CONFIGURATION.md (Configuration reference)
├── 🔬 WORKFLOW_DESCRIPTION.md (Pipeline details)
├── 📈 ALGORITHMIC_IMPROVEMENTS.md (Enhancements)
├── 🧪 tests/ (Test suite)
├── 🐳 docker-compose.yml (Container setup)
└── 📊 outputs/ (Example results)
```

---

## 🎯 Quick Navigation

<div align="center">

| I want to... | Go to... |
|-------------|----------|
| **Get started quickly** | [Quick Start Guide](../QUICK_START_GUIDE.md) |
| **Understand the pipeline** | [Workflow Description](../WORKFLOW_DESCRIPTION.md) |
| **Configure the system** | [Configuration Guide](CONFIGURATION.md) |
| **Use the API** | [API Documentation](http://localhost:8000/docs) |
| **Report a bug** | [GitHub Issues](https://github.com/yourusername/cardioxnet/issues) |
| **Contribute code** | [Contributing Guide](../README.md#contributing) |

</div>

---

## 📞 Contact & Support

- **📧 Email**: support@cardioxnet.org
- **🐛 Issues**: [GitHub Issues](https://github.com/yourusername/cardioxnet/issues)
- **💬 Discussions**: [GitHub Discussions](https://github.com/yourusername/cardioxnet/discussions)
- **📖 Documentation**: [This site](.)

---

<div align="center">

**CardioXNet** - *Discovering Cardiac Repair Pathways Through Network Intelligence*

[![GitHub](https://img.shields.io/badge/GitHub-Repository-blue?logo=github)](https://github.com/yourusername/cardioxnet)
[![Docker](https://img.shields.io/badge/Docker-Ready-blue?logo=docker)](https://docker.com)
[![License](https://img.shields.io/badge/License-MIT-green)](../LICENSE)

</div>