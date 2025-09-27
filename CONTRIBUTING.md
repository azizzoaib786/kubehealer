# Contributing to KubeHealer

Thank you for your interest in contributing to KubeHealer! We welcome contributions from the community and appreciate your help in making this project better.

## 🚀 Quick Start

1. **Fork the repository**: [https://github.com/azizzoaib786/kubehealer](https://github.com/azizzoaib786/kubehealer)
2. **Clone your fork**:
   ```bash
   git clone https://github.com/yourusername/kubehealer.git
   cd kubehealer
   ```
3. **Set up the development environment**:
   ```bash
   kind create cluster --config=cluster/kind-kubehealer-cluster.yaml
   kubectl create namespace kubehealer
   kubectl apply -f k8s/ -R
   ```

## 🛠️ Development Workflow

### Creating a Feature Branch
```bash
git checkout -b feature/your-feature-name
```

### Making Changes
1. **Code Quality**: Follow existing code patterns and include tests
2. **Documentation**: Update relevant README files for your changes
3. **Testing**: Ensure all applications build and deploy successfully
4. **Commit Messages**: Use clear, descriptive commit messages

### Testing Your Changes
```bash
# Build applications
cd apps/etl-sim && docker build -t kubehealer/etl-sim . && cd ../..
cd apps/ml-scorer && docker build -t kubehealer/ml-scorer . && cd ../..
cd apps/rl-agent && docker build -t kubehealer/rl-agent . && cd ../..

# Test deployment
kubectl -n kubehealer rollout restart deployment/etl-sim
kubectl -n kubehealer rollout restart deployment/ml-scorer
kubectl -n kubehealer rollout restart deployment/rl-agent

# Verify pods are running
kubectl -n kubehealer get pods
```

### Submitting Changes
```bash
git add .
git commit -m "Add: your descriptive commit message"
git push origin feature/your-feature-name
```

Then create a pull request at: [https://github.com/azizzoaib786/kubehealer/pulls](https://github.com/azizzoaib786/kubehealer/pulls)

## 🎯 Areas for Contribution

### 🐛 Bug Fixes
- Fix application crashes or unexpected behavior
- Improve error handling and logging
- Address performance issues

### 📚 Documentation
- Improve README files and inline comments
- Add code examples and tutorials
- Create troubleshooting guides

### 🚀 New Features
- Additional failure scenarios for testing
- New monitoring metrics and dashboards
- Enhanced ML models and algorithms
- Additional deployment targets (EKS, GKE, etc.)

### 🤖 Machine Learning
- Improve anomaly detection algorithms
- Add new scoring models
- Enhance the reinforcement learning agent
- Add model performance tracking

### 📊 Monitoring & Observability
- New Grafana dashboards
- Additional Prometheus metrics
- Alert rules and notifications
- Distributed tracing integration

### 🔧 Infrastructure
- Helm charts for easier deployment
- CI/CD pipeline improvements
- Multi-cluster support
- Performance optimizations

## 📋 Coding Guidelines

### Python Code Style
- Follow PEP 8 guidelines
- Use meaningful variable and function names
- Add docstrings for functions and classes
- Include type hints where appropriate

### Docker Best Practices
- Use multi-stage builds for smaller images
- Follow security best practices
- Optimize layer caching
- Document exposed ports and volumes

### Kubernetes Manifests
- Use consistent labeling and annotations
- Follow resource naming conventions
- Include resource limits and requests
- Add health checks (readiness/liveness probes)

### Documentation
- Update README files when adding features
- Include usage examples
- Document configuration options
- Add troubleshooting information

## 🧪 Testing

### Manual Testing
1. Deploy your changes to a Kind cluster
2. Test failure injection scenarios
3. Verify monitoring and alerting
4. Check self-healing behavior

### Integration Testing
- Test interaction between components
- Verify metrics collection and visualization
- Test different configuration scenarios
- Validate RBAC permissions

## 🐛 Reporting Bugs

Before creating a bug report, please check if the issue already exists: [https://github.com/azizzoaib786/kubehealer/issues](https://github.com/azizzoaib786/kubehealer/issues)

When reporting bugs, please include:
- **Environment**: OS, Docker version, Kubernetes version
- **Steps to reproduce**: Detailed steps to reproduce the issue
- **Expected behavior**: What you expected to happen
- **Actual behavior**: What actually happened
- **Logs**: Relevant log output from applications or Kubernetes
- **Screenshots**: If applicable

## 💡 Feature Requests

We welcome feature requests! Please [open an issue](https://github.com/azizzoaib786/kubehealer/issues/new) with:
- **Description**: Clear description of the proposed feature
- **Use case**: Why this feature would be useful
- **Implementation ideas**: Any thoughts on how it could be implemented
- **Examples**: Mock-ups, code examples, or similar features

## 🤝 Code of Conduct

### Our Standards
- Be respectful and constructive in all interactions
- Welcome newcomers and help them get started
- Focus on what is best for the community
- Show empathy towards other community members

### Unacceptable Behavior
- Harassment or discriminatory language
- Personal attacks or trolling
- Publishing private information without permission
- Spam or excessive self-promotion

## 📝 Pull Request Process

1. **Fork the repository** and create your branch from `main`
2. **Make your changes** following the coding guidelines
3. **Test your changes** thoroughly
4. **Update documentation** as needed
5. **Create a pull request** with a clear description of changes
6. **Respond to feedback** during the review process

### Pull Request Template
```markdown
## Description
Brief description of changes

## Type of Change
- [ ] Bug fix
- [ ] New feature
- [ ] Documentation update
- [ ] Performance improvement
- [ ] Other (please describe)

## Testing
- [ ] Local testing completed
- [ ] All applications build successfully
- [ ] Kubernetes deployments work
- [ ] Documentation updated

## Screenshots (if applicable)
Add screenshots to help explain your changes
```

## 🔄 Review Process

1. **Automated checks**: All PRs go through automated testing
2. **Maintainer review**: Core maintainers will review your changes
3. **Community feedback**: Other contributors may provide feedback
4. **Merge**: Once approved, your changes will be merged

## 🆘 Getting Help

- **Documentation**: Start with the README files
- **Issues**: Search existing issues or create a new one
- **Discussions**: Use GitHub Discussions for questions
- **Community**: Join our community discussions

## 📚 Resources

- **Main Repository**: [https://github.com/azizzoaib786/kubehealer](https://github.com/azizzoaib786/kubehealer)
- **Kubernetes Documentation**: [https://kubernetes.io/docs/](https://kubernetes.io/docs/)
- **Docker Documentation**: [https://docs.docker.com/](https://docs.docker.com/)
- **Prometheus Documentation**: [https://prometheus.io/docs/](https://prometheus.io/docs/)
- **Grafana Documentation**: [https://grafana.com/docs/](https://grafana.com/docs/)

## 🎉 Recognition

Contributors will be recognized in the project README and release notes. We appreciate every contribution, no matter how small!

---

**Thank you for contributing to KubeHealer!**
