def slaveNodes() {
    try {
        // Get all slave nodes
        def axis = []
        for (slave in jenkins.model.Jenkins.instance.getNodes()) {
            println("name: " + slave.getDisplayName())
            println("labels: " + slave.labelString)
            axis+=slave.getDisplayName()
        }
        // Print all slave nodes
        for (i in axis) {
            node (i){
                //agent {label i}
                try {
                    println( "########################### "+ i +" ###########################")
                }  catch (Exception e) {
                    println(e)
                }
            }
        }
    } catch (Exception e) {
        println(e)
    }
}
pipeline {
    agent {label 'admin'}
    stages {
        stage('slave stage') {
            steps {
                script {
                    slaveNodes()
                }
            }
        }
    }
}
