from diagrams import Diagram, Cluster, Edge
from diagrams.azure.compute import ContainerApps
from diagrams.azure.database import DatabaseForPostgresqlServers, CacheForRedis
from diagrams.azure.storage import BlobStorage
from diagrams.azure.security import KeyVaults
from diagrams.azure.analytics import LogAnalyticsWorkspaces
from diagrams.azure.devops import ApplicationInsights
from diagrams.azure.identity import ManagedIdentities
from diagrams.onprem.client import Users
from diagrams.onprem.vcs import Github

graph_attr = {
    "fontsize": "15",
    "bgcolor": "white",
    "pad": "0.4",
    "splines": "ortho",
    "nodesep": "0.45",
    "ranksep": "0.9",
    "fontname": "Helvetica",
}
node_attr = {"fontsize": "12", "fontname": "Helvetica"}
edge_attr = {"fontsize": "11", "fontname": "Helvetica", "color": "#707070"}

with Diagram(
    "",
    filename="architecture",
    show=False,
    direction="LR",
    graph_attr=graph_attr,
    node_attr=node_attr,
    edge_attr=edge_attr,
):
    users = Users("Client")
    gh = Github("GitHub Actions")

    with Cluster("Azure  ·  rg-journal-dev"):

        with Cluster("Identity"):
            mi = ManagedIdentities("Managed identity")
            kv = KeyVaults("Key Vault")

        with Cluster("Container Apps Environment"):
            api = ContainerApps("journal-api\nscales to zero")
            redis = CacheForRedis("redis\ninternal ingress")
            worker = ContainerApps("journal-worker\nARQ · email")

        with Cluster("Data"):
            pg = DatabaseForPostgresqlServers("PostgreSQL\nFlexible Server")
            blob = BlobStorage("Blob Storage")

        with Cluster("Observability"):
            appi = ApplicationInsights("Application Insights")
            law = LogAnalyticsWorkspaces("Log Analytics")

    users >> Edge(label="HTTPS") >> api
    gh >> Edge(label="OIDC deploy", style="dashed") >> api

    api >> Edge(label="enqueue") >> redis
    redis >> Edge(label="jobs") >> worker

    api >> pg
    worker >> pg
    api >> Edge(label="signed URLs") >> blob
    worker >> blob

    api >> Edge(style="dotted") >> appi
    worker >> Edge(style="dotted", label="traces + logs") >> appi
    appi >> law

    api >> Edge(style="dotted") >> mi
    mi >> Edge(style="dotted", label="secrets") >> kv
