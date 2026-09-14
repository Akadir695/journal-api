from diagrams import Diagram, Cluster, Edge
from diagrams.azure.compute import ContainerApps
from diagrams.azure.database import CacheForRedis
from diagrams.azure.storage import BlobStorage
from diagrams.onprem.client import Users

graph_attr = {
    "fontsize": "15", "bgcolor": "white", "pad": "0.4",
    "splines": "spline", "nodesep": "0.6", "ranksep": "1.3",
    "fontname": "Helvetica",
}
node_attr = {"fontsize": "12", "fontname": "Helvetica"}
edge_attr = {"fontsize": "11", "fontname": "Helvetica", "color": "#707070"}

with Diagram("", filename="export-flow", show=False, direction="LR",
             graph_attr=graph_attr, node_attr=node_attr, edge_attr=edge_attr):

    client = Users("Client")

    with Cluster("Azure"):
        api = ContainerApps("journal-api")
        redis = CacheForRedis("redis\nqueue")
        worker = ContainerApps("journal-worker")
        blob = BlobStorage("Blob Storage")

    client >> Edge(label="1 · POST /exports") >> api
    api >> Edge(label="2 · 202 Accepted\nnot ready yet", style="dashed",
                color="#B07C2E", fontcolor="#B07C2E") >> client

    api >> Edge(label="3 · queue the job") >> redis
    redis >> Edge(label="4 · picked up") >> worker
    worker >> Edge(label="5 · build zip, upload") >> blob

    client >> Edge(label="6 · GET /download") >> api
    api >> Edge(label="7 · signed URL\nvalid 5 minutes", style="dashed",
                color="#B07C2E", fontcolor="#B07C2E") >> client
    client >> Edge(label="8 · download direct\nnever through the API",
                   color="#2E7D32", fontcolor="#2E7D32") >> blob
