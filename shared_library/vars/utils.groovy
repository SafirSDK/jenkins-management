/* Calling isUnix() in multiple places in the scripts make the output very ugly, so we make our own
   version of the function. */
def betterIsUnix() {
    return env.SystemRoot == null
}

def runCommand(Map map) {
    def command = map.command
    if (betterIsUnix()) {
        if (map.linux_arguments != null)
            command = command + " " + map.linux_arguments
        sh (script: command, label: "Running (through sh) " + command)
    }
    else {
        //command = command.replaceAll("/","\\\\")
        if (map.windows_arguments != null)
            command = command + " " + map.windows_arguments
        bat (script: command, label: "Running (through bat) " + command)
    }
}

def runPython(Map map) {
    def command = "python ${map.script}"
    if (map.command != null)
        command = map.command
    if (map.requirements != null) {
        if (betterIsUnix()) {
            if (map.linux_arguments != null)
                command = command + " " + map.linux_arguments
            sh label: "Running (through sh) " + command,
               script: """
                       python -m venv --system-site-packages .venv
                       . .venv/bin/activate
                       python -m pip install --upgrade pip
                       python -m pip install -r ${map.requirements}
                       $command"""
        }
        else {
            command = command.replaceAll("/","\\\\")
            if (map.windows_arguments != null)
                command = command + " " + map.windows_arguments
            bat label: "Running (through bat) " + command,
                script: """
                        python -m venv --system-site-packages .venv
                        call .venv\\Scripts\\activate
                        python -m pip install --upgrade pip
                        python -m pip install -r ${map.requirements}
                        $command"""
        }
    }
    else {
        map.command = command
        runCommand(map)
    }
}




@NonCPS
def markNodeOffline(nodeName, message) {
    def theNode;
    for (node in Jenkins.instance.nodes) {
        if (node.getNodeName() == nodeName) {
            echo "Found node for $nodeName"
            theNode = node
            break
        }
    }
    if (theNode == null) {
        echo "Failed to find node for $nodeName, cannot mark offline."
        return
    }
    computer = theNode.toComputer()
    computer.setTemporarilyOffline(true)
    computer.doChangeOfflineCause(message)
}

@NonCPS
def markAllNodesOnline() {
    for (node in Jenkins.instance.nodes) {
        node.toComputer().setTemporarilyOffline(false)
    }
}

