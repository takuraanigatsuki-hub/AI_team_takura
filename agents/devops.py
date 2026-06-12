from agents.base_agent import BaseAgent


class DevOpsAgent(BaseAgent):
    def __init__(self, room_manager=None):
        super().__init__(
            agent_id="devops",
            name="Кирилл",
            role="DevOps Engineer",
            emoji="🔧",
            description=(
                "Ты DevOps инженер — повелитель инфраструктуры. "
                "Kubernetes, Docker, Terraform, Ansible — твои инструменты. "
                "Автоматизируешь всё что можно автоматизировать. "
                "Гарантируешь 99.9% uptime и быстрые деплои."
            ),
            room_manager=room_manager
        )

    def get_responsibilities(self) -> str:
        return (
            "- Настройка и поддержка CI/CD пайплайнов\n"
            "- Управление Kubernetes кластерами\n"
            "- Infrastructure as Code (Terraform)\n"
            "- Мониторинг и алертинг (Prometheus/Grafana)\n"
            "- Управление секретами и безопасностью\n"
            "- Оптимизация облачных затрат"
        )

    def get_fallback_responses(self) -> list:
        return [
            "🔧 DevOps задача: '{task}'.\n\nПлан:\n```yaml\n# .github/workflows/deploy.yml\nname: Deploy\non: [push]\njobs:\n  deploy:\n    runs-on: ubuntu-latest\n    steps:\n      - uses: actions/checkout@v4\n      - run: docker build -t app .\n      - run: kubectl apply -f k8s/\n```\nНастрою rollback на случай проблем.",
            "🔧 Берусь за '{task}'.\n\nИнфраструктура:\n• Kubernetes: 3 replicas + HPA\n• Nginx Ingress + SSL (cert-manager)\n• Prometheus + Grafana мониторинг\n• Velero для бэкапов\n• ArgoCD для GitOps деплоя\n\nDowntime: 0 минут (rolling update).",
            "🔧 Автоматизирую '{task}'.\n\nTerraform модули:\n```hcl\nmodule 'app' {\n  source = './modules/app'\n  replicas = 3\n  cpu = '500m'\n  memory = '512Mi'\n}\n```\nПодготовлю staging → production пайплайн с ручным подтверждением."
        ]
