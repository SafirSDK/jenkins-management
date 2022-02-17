def call(Closure callback) {
    def agents = jenkins.model.Jenkins.get().computers.toList()
    for (agent in agents) {
        if (agent.node.selfLabel.name == "built-in")
        {
            echo "removing ${agent.node.selfLabel.name}"
            agents.remove(agent)
        }
    }
    parallel agents.collectEntries { agent ->
        def nodeLabel = agent.node.selfLabel.name
        ["${nodeLabel}": {
            node("${nodeLabel}") {
                stage("${nodeLabel}") {
                    callback(nodeLabel)
                }
            }
        }]
    }
}
