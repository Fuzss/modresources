plugins {
    alias(libs.plugins.architecturyloom)
}

architectury {
    common(rootProject.subprojects.map { it.name.lowercase() }.filter { !it.contains("common") })
}

loom {
    accessWidenerPath.set(file("src/main/resources/${project.property("modId")}.accesswidener"))
}

dependencies {
    // Fabric Loader
    modCompileOnly(libs.fabricloader.fabric)
}

tasks.withType<net.fabricmc.loom.task.AbstractRemapJarTask>().configureEach {
    targetNamespace.set("named")
}
