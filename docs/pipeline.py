from diagrams import Diagram, Cluster, Edge
from diagrams.onprem.vcs import Github
from diagrams.onprem.ci import GithubActions
from diagrams.onprem.container import Docker
from diagrams.azure.compute import ContainerApps
from diagrams.azure.identity import ActiveDirectory
from diagrams.programming.language import Python
from diagrams.onprem.client import User

graph_attr = {
    "fontsize": "15", "bgcolor": "white", "pad": "0.4",
    "splines": "spline", "nodesep": "0.5", "ranksep": "1.0",
    "fontname": "Helvetica",
}
node_attr = {"fontsize": "12", "fontname": "Helvetica"}
edge_attr = {"fontsize": "11", "fontname": "Helvetica", "color": "#707070"}

with Diagram("", filename="pipeline", show=False, direction="LR",
             graph_attr=graph_attr, node_attr=node_attr, edge_attr=edge_attr):

    dev = User("git push")
    repo = Github("main")

    with Cluster("GitHub Actions"):
        with Cluster("gates"):
            test = GithubActions("test\nruff · 77 tests\n85% coverage floor")
            leaks = GithubActions("secrets\ngitleaks")
        build = GithubActions("build\nlinux/amd64\ntag = commit SHA")
        deploy = GithubActions("deploy")

    ghcr = Docker("GHCR\nghcr.io/akadir695/journal-api")
    entra = ActiveDirectory("Entra ID\nfederated credential")

    with Cluster("Azure"):
        api = ContainerApps("journal-api")
        worker = ContainerApps("journal-worker")

    dev >> repo
    repo >> test
    repo >> leaks
    test >> Edge(label="pass") >> build
    leaks >> Edge(label="clean") >> build
    build >> Edge(label="push image") >> ghcr
    build >> deploy
    deploy >> Edge(label="OIDC token", style="dashed") >> entra
    entra >> Edge(label="short-lived\naccess token", style="dashed") >> deploy
    deploy >> Edge(label="az containerapp update") >> api
    deploy >> worker
    ghcr >> Edge(label="pull", style="dotted") >> api
