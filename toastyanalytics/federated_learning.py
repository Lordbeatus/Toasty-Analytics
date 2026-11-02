"""
Federated Learning Framework for ToastyAnalytics
Enables distributed learning across AI agents without sharing raw data
Using Flower (https://flower.dev/) framework
"""

from typing import Any, Dict, List, Optional, Tuple

try:
    import flwr as fl
    from flwr.common import Metrics, NDArrays, Scalar
    from flwr.server import ServerConfig
    from flwr.server.strategy import FedAvg

    FLOWER_AVAILABLE = True
except ImportError:
    FLOWER_AVAILABLE = False
    print("Flower not installed - federated learning unavailable")

# PyTorch for model definitions
try:
    import torch
    import torch.nn as nn
    from torch.utils.data import DataLoader, TensorDataset

    TORCH_AVAILABLE = True
except ImportError:
    TORCH_AVAILABLE = False


class CodeQualityModel(nn.Module):
    """
    Simple neural network for code quality prediction
    Used in federated learning
    """

    def __init__(self, input_dim: int = 768, hidden_dim: int = 128):
        super().__init__()
        self.network = nn.Sequential(
            nn.Linear(input_dim, hidden_dim),
            nn.ReLU(),
            nn.Dropout(0.2),
            nn.Linear(hidden_dim, 64),
            nn.ReLU(),
            nn.Linear(64, 1),
            nn.Sigmoid(),
        )

    def forward(self, x):
        return self.network(x)


if FLOWER_AVAILABLE and TORCH_AVAILABLE:

    class ToastyAnalyticsClient(fl.client.NumPyClient):
        """
        Federated learning client for individual AI agents
        Trains locally on agent's data, shares only model updates
        """

        def __init__(self, agent_id: str, model: nn.Module, train_loader: DataLoader):
            self.agent_id = agent_id
            self.model = model
            self.train_loader = train_loader
            self.device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
            self.model.to(self.device)

        def get_parameters(self, config: Dict[str, Scalar]) -> NDArrays:
            """Return current model parameters"""
            return [val.cpu().numpy() for _, val in self.model.state_dict().items()]

        def set_parameters(self, parameters: NDArrays) -> None:
            """Update model with aggregated parameters from server"""
            params_dict = zip(self.model.state_dict().keys(), parameters)
            state_dict = {k: torch.tensor(v) for k, v in params_dict}
            self.model.load_state_dict(state_dict, strict=True)

        def fit(
            self, parameters: NDArrays, config: Dict[str, Scalar]
        ) -> Tuple[NDArrays, int, Dict]:
            """Train model on local data"""
            self.set_parameters(parameters)

            # Training configuration
            epochs = int(config.get("local_epochs", 1))
            learning_rate = float(config.get("learning_rate", 0.001))

            optimizer = torch.optim.Adam(self.model.parameters(), lr=learning_rate)
            criterion = nn.BCELoss()

            self.model.train()
            total_loss = 0
            num_batches = 0

            for epoch in range(epochs):
                for batch_data, batch_labels in self.train_loader:
                    batch_data = batch_data.to(self.device)
                    batch_labels = batch_labels.to(self.device)

                    optimizer.zero_grad()
                    outputs = self.model(batch_data)
                    loss = criterion(outputs, batch_labels)
                    loss.backward()
                    optimizer.step()

                    total_loss += loss.item()
                    num_batches += 1

            avg_loss = total_loss / num_batches if num_batches > 0 else 0

            print(
                f" Agent {self.agent_id} trained for {epochs} epochs, avg loss: {avg_loss:.4f}"
            )

            return (
                self.get_parameters({}),
                len(self.train_loader.dataset),
                {"loss": avg_loss},
            )

        def evaluate(
            self, parameters: NDArrays, config: Dict[str, Scalar]
        ) -> Tuple[float, int, Dict]:
            """Evaluate model on local data"""
            self.set_parameters(parameters)

            self.model.eval()
            criterion = nn.BCELoss()
            total_loss = 0
            correct = 0
            total = 0

            with torch.no_grad():
                for batch_data, batch_labels in self.train_loader:
                    batch_data = batch_data.to(self.device)
                    batch_labels = batch_labels.to(self.device)

                    outputs = self.model(batch_data)
                    loss = criterion(outputs, batch_labels)
                    total_loss += loss.item()

                    predicted = (outputs > 0.5).float()
                    correct += (predicted == batch_labels).sum().item()
                    total += batch_labels.size(0)

            accuracy = correct / total if total > 0 else 0
            avg_loss = (
                total_loss / len(self.train_loader) if len(self.train_loader) > 0 else 0
            )

            return avg_loss, len(self.train_loader.dataset), {"accuracy": accuracy}


class FederatedLearningServer:
    """
    Federated learning server that coordinates training across agents
    """

    def __init__(self, model: nn.Module, num_rounds: int = 10, min_clients: int = 2):
        self.model = model
        self.num_rounds = num_rounds
        self.min_clients = min_clients

        if not FLOWER_AVAILABLE:
            raise ImportError("Flower framework not installed")

    def start_server(self, server_address: str = "0.0.0.0:8080"):
        """
        Start federated learning server

        Agents connect to this server and participate in federated training
        """

        # Define strategy for aggregating client updates
        strategy = FedAvg(
            fraction_fit=1.0,  # Sample 100% of available clients for training
            fraction_evaluate=1.0,  # Sample 100% of available clients for evaluation
            min_fit_clients=self.min_clients,
            min_evaluate_clients=self.min_clients,
            min_available_clients=self.min_clients,
            evaluate_metrics_aggregation_fn=self._weighted_average,
            fit_metrics_aggregation_fn=self._weighted_average,
        )

        # Start server
        print(f"Starting Federated Learning Server on {server_address}")
        print(f"Rounds: {self.num_rounds}, Min clients: {self.min_clients}")

        fl.server.start_server(
            server_address=server_address,
            config=ServerConfig(num_rounds=self.num_rounds),
            strategy=strategy,
        )

        print("Federated learning completed")

    def _weighted_average(self, metrics: List[Tuple[int, Metrics]]) -> Metrics:
        """Aggregate metrics from clients using weighted average"""

        # Calculate weighted averages
        accuracies = [
            num_examples * m["accuracy"]
            for num_examples, m in metrics
            if "accuracy" in m
        ]
        losses = [
            num_examples * m["loss"] for num_examples, m in metrics if "loss" in m
        ]
        examples = [num_examples for num_examples, _ in metrics]

        total_examples = sum(examples)

        return {
            "accuracy": sum(accuracies) / total_examples if accuracies else 0,
            "loss": sum(losses) / total_examples if losses else 0,
        }


class FederatedLearningManager:
    """
    High-level manager for federated learning in ToastyAnalytics
    """

    def __init__(self):
        self.server = None
        self.clients: Dict[str, ToastyAnalyticsClient] = {}
        self.model = None

    def initialize_server(self, model: Optional[nn.Module] = None, **config):
        """Initialize federated learning server"""

        if not TORCH_AVAILABLE or not FLOWER_AVAILABLE:
            print("PyTorch and Flower required for federated learning")
            return False

        if model is None:
            # Use default code quality model
            model = CodeQualityModel()

        self.model = model
        self.server = FederatedLearningServer(
            model=model,
            num_rounds=config.get("num_rounds", 10),
            min_clients=config.get("min_clients", 2),
        )

        print("Federated learning server initialized")
        return True

    def register_agent(self, agent_id: str, training_data: List[Dict[str, Any]]):
        """
        Register an AI agent for federated learning

        Args:
            agent_id: Unique identifier for the agent
            training_data: List of {"features": array, "label": float} dictionaries
        """

        if not TORCH_AVAILABLE:
            print("PyTorch required for federated learning")
            return False

        # Convert training data to PyTorch tensors
        features = torch.tensor(
            [item["features"] for item in training_data], dtype=torch.float32
        )
        labels = torch.tensor(
            [[item["label"]] for item in training_data], dtype=torch.float32
        )

        # Create DataLoader
        dataset = TensorDataset(features, labels)
        train_loader = DataLoader(dataset, batch_size=32, shuffle=True)

        # Create client
        client = ToastyAnalyticsClient(
            agent_id=agent_id,
            model=CodeQualityModel() if self.model is None else self.model,
            train_loader=train_loader,
        )

        self.clients[agent_id] = client

        print(
            f" Registered agent {agent_id} with {len(training_data)} training samples"
        )
        return True

    def start_training(self, server_address: str = "0.0.0.0:8080"):
        """Start federated learning training"""

        if self.server is None:
            print("Server not initialized - call initialize_server() first")
            return False

        if len(self.clients) < self.server.min_clients:
            print(
                f" Need at least {self.server.min_clients} clients, have {len(self.clients)}"
            )
            return False

        print(f"Starting federated learning with {len(self.clients)} agents")
        self.server.start_server(server_address)

        return True

    def get_global_model(self) -> Optional[nn.Module]:
        """Get the trained global model"""
        return self.model


# Global singleton
_fl_manager = None

if FLOWER_AVAILABLE and TORCH_AVAILABLE:

    def get_federated_learning_manager() -> FederatedLearningManager:
        """Get global federated learning manager"""
        global _fl_manager
        if _fl_manager is None:
            _fl_manager = FederatedLearningManager()
        return _fl_manager

else:
    # Stubs when dependencies unavailable
    def get_federated_learning_manager():
        print("Federated learning requires PyTorch and Flower")
        return None
